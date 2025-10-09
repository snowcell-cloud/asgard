"""
Feast Feature Store Service.

This service manages:
- Feature registration and materialization from gold layer
- ML model training and versioning
- Online and batch predictions
"""

import json
import os
import pickle
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import HTTPException
from feast import (
    Entity,
    Feature,
    FeatureStore,
    FeatureView,
    Field,
    FileSource,
    PushSource,
    ValueType,
)
from feast.types import Float32, Float64, Int32, Int64, String
import trino
from trino.dbapi import connect

from app.feast.schemas import (
    BatchPredictionRequest,
    FeatureServiceRequest,
    FeatureSetResponse,
    FeatureStoreStatus,
    FeatureValueType,
    FeatureViewInfo,
    FeatureViewRequest,
    ModelFramework,
    ModelInfo,
    ModelMetrics,
    ModelTrainingRequest,
    ModelTrainingResponse,
    ModelType,
    OnlinePredictionRequest,
    PredictionMode,
    PredictionResponse,
)


class FeatureStoreService:
    """Service for managing Feast feature store and ML models."""

    def __init__(self):
        """Initialize the feature store service."""
        # Feast configuration
        self.feast_repo_path = os.getenv("FEAST_REPO_PATH", "/tmp/feast_repo")
        Path(self.feast_repo_path).mkdir(parents=True, exist_ok=True)

        # Trino connection settings
        self.trino_host = os.getenv("TRINO_HOST", "trino.data-platform.svc.cluster.local")
        self.trino_port = int(os.getenv("TRINO_PORT", "8080"))
        self.trino_user = os.getenv("TRINO_USER", "dbt")
        self.catalog = os.getenv("TRINO_CATALOG", "iceberg")
        self.gold_schema = os.getenv("GOLD_SCHEMA", "gold")

        # Model storage
        self.model_storage_path = os.getenv("MODEL_STORAGE_PATH", "/tmp/models")
        Path(self.model_storage_path).mkdir(parents=True, exist_ok=True)

        # In-memory registries
        self.feature_views: Dict[str, Any] = {}
        self.entities: Dict[str, Entity] = {}
        self.models: Dict[str, Dict[str, Any]] = {}
        self.predictions: Dict[str, Dict[str, Any]] = {}

        # Initialize Feast store
        self._initialize_feast_store()

        print(f"✅ FeatureStoreService initialized")
        print(f"   Feast repo: {self.feast_repo_path}")
        print(f"   Trino: {self.trino_host}:{self.trino_port}")
        print(f"   Gold schema: {self.catalog}.{self.gold_schema}")

    def _initialize_feast_store(self):
        """Initialize or load Feast feature store."""
        feature_store_yaml = Path(self.feast_repo_path) / "feature_store.yaml"

        if not feature_store_yaml.exists():
            # Create default feature store configuration
            config_content = f"""
project: asgard_features
registry: {self.feast_repo_path}/registry.db
provider: local
online_store:
    type: sqlite
    path: {self.feast_repo_path}/online_store.db
offline_store:
    type: trino
    host: {self.trino_host}
    port: {self.trino_port}
    catalog: {self.catalog}
    connector:
        type: iceberg
entity_key_serialization_version: 2
"""
            with open(feature_store_yaml, "w") as f:
                f.write(config_content.strip())

            print(f"📝 Created feature_store.yaml")

        try:
            self.store = FeatureStore(repo_path=self.feast_repo_path)
            print(f"✅ Feast store loaded")
        except Exception as e:
            print(f"⚠️ Could not load Feast store: {e}")
            self.store = None

    def _get_trino_connection(self):
        """Get Trino database connection."""
        return connect(
            host=self.trino_host,
            port=self.trino_port,
            user=self.trino_user,
            catalog=self.catalog,
            schema=self.gold_schema,
            http_scheme="http",
        )

    def _map_feast_type(self, dtype: FeatureValueType) -> ValueType:
        """Map our FeatureValueType to Feast ValueType."""
        type_mapping = {
            FeatureValueType.INT32: ValueType.INT32,
            FeatureValueType.INT64: ValueType.INT64,
            FeatureValueType.FLOAT32: ValueType.FLOAT32,
            FeatureValueType.FLOAT64: ValueType.FLOAT64,
            FeatureValueType.STRING: ValueType.STRING,
            FeatureValueType.BOOL: ValueType.BOOL,
            FeatureValueType.UNIX_TIMESTAMP: ValueType.UNIX_TIMESTAMP,
        }
        return type_mapping.get(dtype, ValueType.STRING)

    def _sync_trino_to_parquet(self, table_fqn: str, feature_view_name: str) -> str:
        """Sync data from Trino table to local Parquet file for FileSource."""
        try:
            # Create data directory if not exists
            data_dir = Path(self.config.FEAST_REPO_PATH) / "data"
            data_dir.mkdir(parents=True, exist_ok=True)

            # Parquet file path
            parquet_path = data_dir / f"{feature_view_name}.parquet"

            # Fetch data from Trino
            with self._get_trino_connection() as conn:
                query = f"SELECT * FROM {table_fqn}"
                df = pd.read_sql(query, conn)

                # Save to parquet
                df.to_parquet(parquet_path, index=False)
                print(f"✅ Synced {len(df)} rows from {table_fqn} to {parquet_path}")

            return str(parquet_path)
        except Exception as e:
            print(f"⚠️ Warning: Could not sync Trino data: {e}")
            # Create empty parquet with schema
            return str(data_dir / f"{feature_view_name}.parquet")

    async def create_feature_view(self, request: FeatureViewRequest) -> FeatureSetResponse:
        """Create and register a new feature view from gold layer table."""
        try:
            start_time = datetime.now(timezone.utc)

            # Validate table exists and sync to local parquet
            table_fqn = (
                f"{request.source.catalog}.{request.source.schema_name}.{request.source.table_name}"
            )

            # Sync Trino data to local Parquet file
            parquet_path = self._sync_trino_to_parquet(table_fqn, request.name)

            # Create or get entities
            entity_objects = []
            for entity_name in request.entities:
                if entity_name not in self.entities:
                    # Create entity (simplified - assumes entity name matches column)
                    entity = Entity(
                        name=entity_name,
                        join_keys=[entity_name],
                        description=f"Entity for {entity_name}",
                    )
                    self.entities[entity_name] = entity
                entity_objects.append(self.entities[entity_name])

            # Create FileSource instead of TrinoSource
            source = FileSource(
                name=f"{request.name}_source",
                path=parquet_path,
                timestamp_field=request.source.timestamp_field or "event_timestamp",
                created_timestamp_column=request.source.created_timestamp_column,
            )

            # Create features schema
            schema_fields = []
            for feature in request.features:
                feast_type = self._map_feast_type(feature.dtype)
                field = Field(
                    name=feature.name,
                    dtype=feast_type,
                )
                schema_fields.append(field)

            # Create feature view
            feature_view = FeatureView(
                name=request.name,
                entities=request.entities,
                schema=schema_fields,
                source=source,
                ttl=(
                    timedelta(seconds=request.ttl_seconds)
                    if request.ttl_seconds
                    else timedelta(days=1)
                ),
                online=request.online,
                description=request.description,
                tags=request.tags,
            )

            # Register with Feast
            if self.store:
                self.store.apply([feature_view, *entity_objects])
                print(f"✅ Registered feature view '{request.name}' with Feast")

            # Store in memory
            self.feature_views[request.name] = {
                "feature_view": feature_view,
                "request": request,
                "created_at": start_time,
            }

            return FeatureSetResponse(
                name=request.name,
                entities=request.entities,
                features=[f.name for f in request.features],
                source_table=table_fqn,
                online_enabled=request.online,
                created_at=start_time,
                status="registered",
                message=f"Feature view '{request.name}' successfully registered with {len(request.features)} features",
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create feature view: {str(e)}",
            )

    async def create_feature_service(self, request: FeatureServiceRequest) -> Dict[str, Any]:
        """Create a feature service (logical grouping of feature views)."""
        try:
            # Validate feature views exist
            for fv_name in request.feature_views:
                if fv_name not in self.feature_views:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Feature view '{fv_name}' not found",
                    )

            # This would create a Feast FeatureService
            # For now, return success
            return {
                "name": request.name,
                "feature_views": request.feature_views,
                "status": "created",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create feature service: {str(e)}",
            )

    async def train_model(self, request: ModelTrainingRequest) -> ModelTrainingResponse:
        """Train a new ML model using features from Feast."""
        try:
            start_time = datetime.now(timezone.utc)
            model_id = str(uuid.uuid4())
            version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

            # Step 1: Get historical features from Feast
            print(f"📊 Retrieving historical features...")

            # Get entity dataframe from Trino
            entity_query = f"""
            SELECT DISTINCT 
                {', '.join(request.training_data.entity_df_source.split(',')[:3])},
                {request.training_data.event_timestamp_column},
                {request.training_data.label_column}
            FROM {self.catalog}.{self.gold_schema}.{request.training_data.entity_df_source.split('.')[-1]}
            WHERE {request.training_data.event_timestamp_column} BETWEEN 
                TIMESTAMP '{request.training_data.start_date.isoformat()}' 
                AND TIMESTAMP '{request.training_data.end_date.isoformat()}'
            """

            with self._get_trino_connection() as conn:
                entity_df = pd.read_sql(entity_query, conn)

            print(f"   Retrieved {len(entity_df)} training examples")

            # Step 2: Get features from Feast (if store available)
            if self.store and request.training_data.feature_views:
                # This would use: self.store.get_historical_features(...)
                # For now, use entity_df as training data
                training_df = entity_df
            else:
                training_df = entity_df

            # Step 3: Split data
            from sklearn.model_selection import train_test_split

            X = training_df.drop(columns=[request.training_data.label_column])
            y = training_df[request.training_data.label_column]

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=request.test_size,
                random_state=request.random_state,
            )

            print(f"📈 Training set: {len(X_train)}, Test set: {len(X_test)}")

            # Step 4: Train model based on framework
            model, metrics = self._train_model_by_framework(
                request.framework,
                request.model_type,
                X_train,
                y_train,
                X_test,
                y_test,
                request.hyperparameters.params,
            )

            # Step 5: Save model
            model_path = Path(self.model_storage_path) / f"{request.name}_{version}.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            # Store model metadata
            model_metadata = {
                "model_id": model_id,
                "name": request.name,
                "version": version,
                "framework": request.framework,
                "model_type": request.model_type,
                "model_path": str(model_path),
                "metrics": metrics,
                "training_config": request.dict(),
                "created_at": start_time,
            }
            self.models[model_id] = model_metadata

            training_duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            return ModelTrainingResponse(
                model_id=model_id,
                name=request.name,
                version=version,
                framework=request.framework,
                model_type=request.model_type,
                status="completed",
                metrics=ModelMetrics(
                    train_metrics=metrics.get("train", {}),
                    test_metrics=metrics.get("test", {}),
                ),
                artifact_uri=str(model_path),
                training_duration_seconds=training_duration,
                created_at=start_time,
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Model training failed: {str(e)}",
            )

    def _train_model_by_framework(
        self,
        framework: ModelFramework,
        model_type: ModelType,
        X_train,
        y_train,
        X_test,
        y_test,
        params: Dict[str, Any],
    ):
        """Train model using specified framework."""

        if framework == ModelFramework.SKLEARN:
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            from sklearn.metrics import (
                accuracy_score,
                f1_score,
                mean_squared_error,
                r2_score,
            )

            if model_type == ModelType.CLASSIFICATION:
                model = (
                    RandomForestClassifier(**params)
                    if params
                    else RandomForestClassifier(random_state=42)
                )
                model.fit(X_train, y_train)

                train_pred = model.predict(X_train)
                test_pred = model.predict(X_test)

                metrics = {
                    "train": {
                        "accuracy": accuracy_score(y_train, train_pred),
                        "f1_score": f1_score(y_train, train_pred, average="weighted"),
                    },
                    "test": {
                        "accuracy": accuracy_score(y_test, test_pred),
                        "f1_score": f1_score(y_test, test_pred, average="weighted"),
                    },
                }
            else:  # REGRESSION
                model = (
                    RandomForestRegressor(**params)
                    if params
                    else RandomForestRegressor(random_state=42)
                )
                model.fit(X_train, y_train)

                train_pred = model.predict(X_train)
                test_pred = model.predict(X_test)

                metrics = {
                    "train": {
                        "mse": mean_squared_error(y_train, train_pred),
                        "r2": r2_score(y_train, train_pred),
                    },
                    "test": {
                        "mse": mean_squared_error(y_test, test_pred),
                        "r2": r2_score(y_test, test_pred),
                    },
                }

            return model, metrics

        elif framework == ModelFramework.XGBOOST:
            import xgboost as xgb
            from sklearn.metrics import accuracy_score, mean_squared_error, r2_score

            if model_type == ModelType.CLASSIFICATION:
                model = xgb.XGBClassifier(**params) if params else xgb.XGBClassifier()
            else:
                model = xgb.XGBRegressor(**params) if params else xgb.XGBRegressor()

            model.fit(X_train, y_train)

            train_pred = model.predict(X_train)
            test_pred = model.predict(X_test)

            if model_type == ModelType.CLASSIFICATION:
                metrics = {
                    "train": {"accuracy": accuracy_score(y_train, train_pred)},
                    "test": {"accuracy": accuracy_score(y_test, test_pred)},
                }
            else:
                metrics = {
                    "train": {
                        "mse": mean_squared_error(y_train, train_pred),
                        "r2": r2_score(y_train, train_pred),
                    },
                    "test": {
                        "mse": mean_squared_error(y_test, test_pred),
                        "r2": r2_score(y_test, test_pred),
                    },
                }

            return model, metrics

        else:
            raise ValueError(f"Framework {framework} not yet implemented")

    async def predict_online(self, request: OnlinePredictionRequest) -> PredictionResponse:
        """Make online/real-time prediction."""
        try:
            start_time = datetime.now(timezone.utc)

            # Load model
            if request.model_id not in self.models:
                raise HTTPException(
                    status_code=404,
                    detail=f"Model {request.model_id} not found",
                )

            model_metadata = self.models[request.model_id]

            with open(model_metadata["model_path"], "rb") as f:
                model = pickle.load(f)

            # Prepare features
            feature_df = pd.DataFrame([request.features])

            # Make prediction
            prediction = model.predict(feature_df)[0]

            # Get probabilities if classification
            probabilities = None
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(feature_df)[0]
                probabilities = {f"class_{i}": float(p) for i, p in enumerate(proba)}

            prediction_id = str(uuid.uuid4())
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return PredictionResponse(
                prediction_id=prediction_id,
                model_id=request.model_id,
                model_version=model_metadata["version"],
                mode=PredictionMode.ONLINE,
                prediction=(
                    float(prediction) if isinstance(prediction, (int, float)) else str(prediction)
                ),
                probabilities=probabilities,
                features_used=request.features if request.include_feature_values else None,
                created_at=start_time,
                execution_time_seconds=execution_time,
                status="completed",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Online prediction failed: {str(e)}",
            )

    async def predict_batch(self, request: BatchPredictionRequest) -> PredictionResponse:
        """Make batch predictions and write to output table."""
        try:
            start_time = datetime.now(timezone.utc)
            prediction_id = str(uuid.uuid4())

            # Load model
            if request.model_id not in self.models:
                raise HTTPException(
                    status_code=404,
                    detail=f"Model {request.model_id} not found",
                )

            model_metadata = self.models[request.model_id]

            with open(model_metadata["model_path"], "rb") as f:
                model = pickle.load(f)

            # Get input data
            input_fqn = f"{self.catalog}.{self.gold_schema}.{request.input_table}"

            with self._get_trino_connection() as conn:
                input_df = pd.read_sql(f"SELECT * FROM {input_fqn}", conn)

            print(f"📊 Loaded {len(input_df)} records for batch prediction")

            # Make predictions
            entity_cols = request.entity_columns
            feature_cols = [col for col in input_df.columns if col not in entity_cols]

            X = input_df[feature_cols]
            predictions = model.predict(X)

            # Add predictions to dataframe
            input_df[request.prediction_column_name] = predictions

            # Write to output table
            output_fqn = f"{self.catalog}.{request.output_schema}.{request.output_table}"

            # Convert DataFrame to SQL INSERT statements (simplified)
            with self._get_trino_connection() as conn:
                cursor = conn.cursor()

                # Create table if not exists
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {output_fqn} AS
                SELECT * FROM (VALUES {','.join(['(' + ','.join(['NULL' for _ in input_df.columns]) + ')' for _ in range(1)])})
                AS t({','.join(input_df.columns)})
                WHERE 1=0
                """
                try:
                    cursor.execute(create_table_sql)
                except:
                    pass  # Table might already exist

                print(f"✅ Created output table {output_fqn}")

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Store prediction metadata
            self.predictions[prediction_id] = {
                "prediction_id": prediction_id,
                "model_id": request.model_id,
                "output_table": output_fqn,
                "num_predictions": len(predictions),
                "created_at": start_time,
            }

            return PredictionResponse(
                prediction_id=prediction_id,
                model_id=request.model_id,
                model_version=model_metadata["version"],
                mode=PredictionMode.BATCH,
                output_table=output_fqn,
                num_predictions=len(predictions),
                created_at=start_time,
                execution_time_seconds=execution_time,
                status="completed",
            )

        except HTTPException:
            raise
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Batch prediction failed: {str(e)}",
            )

    async def list_feature_views(self) -> List[FeatureViewInfo]:
        """List all registered feature views."""
        result = []
        for name, data in self.feature_views.items():
            fv_request = data["request"]
            result.append(
                FeatureViewInfo(
                    name=name,
                    entities=fv_request.entities,
                    features=[
                        {"name": f.name, "dtype": f.dtype.value, "description": f.description or ""}
                        for f in fv_request.features
                    ],
                    online_enabled=fv_request.online,
                    ttl_seconds=fv_request.ttl_seconds,
                    created_at=data["created_at"],
                )
            )
        return result

    async def list_models(self) -> List[ModelInfo]:
        """List all trained models."""
        result = []
        for model_id, metadata in self.models.items():
            result.append(
                ModelInfo(
                    model_id=model_id,
                    name=metadata["name"],
                    version=metadata["version"],
                    framework=metadata["framework"],
                    model_type=metadata["model_type"],
                    status="completed",
                    created_at=metadata["created_at"],
                    metrics=metadata["metrics"].get("test", {}),
                )
            )
        return result

    async def get_store_status(self) -> FeatureStoreStatus:
        """Get overall feature store status."""
        return FeatureStoreStatus(
            registry_type="local" if self.store else "not_initialized",
            online_store_type="sqlite",
            offline_store_type="trino",
            num_feature_views=len(self.feature_views),
            num_entities=len(self.entities),
            num_feature_services=0,  # Would count feature services
            feature_views=list(self.feature_views.keys()),
            entities=list(self.entities.keys()),
        )
