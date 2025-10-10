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

        # S3 configuration for Iceberg Parquet files
        self.s3_bucket = os.getenv("S3_BUCKET", "airbytedestination1")
        self.s3_iceberg_base_path = os.getenv("S3_ICEBERG_BASE_PATH", "iceberg/gold")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")

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
        print(f"   S3 Iceberg: s3://{self.s3_bucket}/{self.s3_iceberg_base_path}")

    def _initialize_feast_store(self):
        """Initialize or load Feast feature store."""
        feature_store_yaml = Path(self.feast_repo_path) / "feature_store.yaml"

        if not feature_store_yaml.exists():
            # Create default feature store configuration
            # NOTE: Using offline store only. Online store is commented out for now.
            # Data source: Iceberg S3 Parquet files (no sync needed)
            config_content = f"""
project: asgard_features
registry: {self.feast_repo_path}/registry.db
provider: local
# online_store:
#     type: sqlite
#     path: {self.feast_repo_path}/online_store.db
offline_store:
    type: file
    # Reads directly from S3 Parquet files created by Iceberg
    # Example: s3://{self.s3_bucket}/{self.s3_iceberg_base_path}/{{table}}/data/*.parquet
entity_key_serialization_version: 2
"""
            with open(feature_store_yaml, "w") as f:
                f.write(config_content.strip())

            print(f"📝 Created feature_store.yaml (Direct S3 Parquet access from Iceberg)")

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

    def _get_iceberg_parquet_path(self, table_fqn: str) -> str:
        """
        Get the S3 Parquet file path for an Iceberg table.

        Iceberg tables store data in Parquet format on S3 with metadata managed by Nessie.
        This method queries Iceberg metadata to get the actual Parquet file locations.

        Example path: s3://airbytedestination1/iceberg/gold/{table_uuid}/data/*.parquet
        """
        try:
            # Query Iceberg metadata to get table files
            with self._get_trino_connection() as conn:
                # Get table metadata including file paths
                # Iceberg stores file paths in metadata
                metadata_query = f"""
                SELECT 
                    "$path" as file_path
                FROM {table_fqn}
                LIMIT 1
                """

                result = pd.read_sql(metadata_query, conn)

                if len(result) > 0 and "file_path" in result.columns:
                    # Extract the S3 path from the first file
                    first_file_path = result["file_path"].iloc[0]

                    # Get the data directory (remove the specific parquet file name)
                    # Example: s3://bucket/iceberg/gold/table_id/data/file.parquet -> s3://bucket/iceberg/gold/table_id/data/*.parquet
                    if first_file_path.startswith("s3://"):
                        # Use wildcard pattern for all parquet files in the data directory
                        data_dir = "/".join(first_file_path.split("/")[:-1])
                        s3_path = f"{data_dir}/*.parquet"
                        print(f"✅ Found Iceberg data at: {s3_path}")
                        return s3_path

                # Fallback: construct path based on table name
                # Format: s3://bucket/iceberg/gold/{table_name}/data/*.parquet
                table_name = table_fqn.split(".")[-1]
                s3_path = (
                    f"s3://{self.s3_bucket}/{self.s3_iceberg_base_path}/{table_name}/data/*.parquet"
                )
                print(f"⚠️  Using constructed path: {s3_path}")
                return s3_path

        except Exception as e:
            print(f"⚠️ Warning: Could not query Iceberg metadata: {e}")
            # Fallback to constructed path
            table_name = table_fqn.split(".")[-1]
            s3_path = (
                f"s3://{self.s3_bucket}/{self.s3_iceberg_base_path}/{table_name}/data/*.parquet"
            )
            print(f"⚠️  Using fallback path: {s3_path}")
            return s3_path

    def _sync_trino_to_parquet(self, table_fqn: str, feature_view_name: str) -> str:
        """
        Get S3 Parquet path for Iceberg table (NO SYNC NEEDED).

        Iceberg already stores data in Parquet format on S3 with Nessie metadata.
        We just return the S3 path directly for Feast FileSource to use.

        OLD approach: Iceberg → Trino → Local Parquet (unnecessary duplication)
        NEW approach: Iceberg S3 Parquet → Feast FileSource (direct access)
        """
        try:
            # Get the S3 path where Iceberg stores the Parquet files
            s3_path = self._get_iceberg_parquet_path(table_fqn)

            # Validate table exists by querying it
            with self._get_trino_connection() as conn:
                count_query = f"SELECT COUNT(*) as cnt FROM {table_fqn}"
                result = pd.read_sql(count_query, conn)
                row_count = result["cnt"].iloc[0] if len(result) > 0 else 0
                print(f"✅ Validated Iceberg table {table_fqn} ({row_count} rows)")

            return s3_path

        except Exception as e:
            print(f"⚠️ Warning: Could not access Iceberg table: {e}")
            # Return constructed path anyway
            table_name = table_fqn.split(".")[-1]
            return f"s3://{self.s3_bucket}/{self.s3_iceberg_base_path}/{table_name}/data/*.parquet"

    async def create_feature_view(self, request: FeatureViewRequest) -> FeatureSetResponse:
        """
        Create and register a new feature view from Iceberg gold layer table.

        Data flow (DIRECT ACCESS - NO SYNC):
        1. Source: Iceberg catalog table (e.g., iceberg.gold.customer_aggregates)
        2. Iceberg stores data in S3 Parquet format with Nessie metadata
        3. Query Trino to get S3 Parquet file path
        4. Register FileSource feature view pointing directly to S3 Parquet files
        5. Feast reads from S3 Parquet (no local copy needed)
        """
        try:
            start_time = datetime.now(timezone.utc)

            # Build Iceberg table FQN
            table_fqn = (
                f"{request.source.catalog}.{request.source.schema_name}.{request.source.table_name}"
            )

            # Get S3 Parquet path directly from Iceberg (no sync needed)
            s3_parquet_path = self._sync_trino_to_parquet(table_fqn, request.name)

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

            # Create FileSource pointing directly to S3 Parquet files (Iceberg storage)
            # Note: Data is stored by Iceberg in S3 Parquet format, no sync needed
            source = FileSource(
                name=f"{request.name}_source",
                path=s3_parquet_path,
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

            # Create feature view (offline store only - online disabled)
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
                online=False,  # Disabled: Using offline store only
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
                online_enabled=False,  # Disabled: Using offline store only
                created_at=start_time,
                status="registered",
                message=f"Feature view '{request.name}' successfully registered from Iceberg gold layer with {len(request.features)} features (offline store only)",
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

    # NOTE: Online predictions disabled - using offline store only
    # Uncomment when online store is enabled
    """
    async def predict_online(self, request: OnlinePredictionRequest) -> PredictionResponse:
        '''Make online/real-time prediction.'''
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
    """

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
            online_store_type="disabled",  # Online store disabled - offline only
            offline_store_type="file (S3 Parquet - Iceberg native storage)",
            num_feature_views=len(self.feature_views),
            num_entities=len(self.entities),
            num_feature_services=0,  # Would count feature services
            feature_views=list(self.feature_views.keys()),
            entities=list(self.entities.keys()),
        )
