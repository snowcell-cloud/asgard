"""
MLOps Service for ML lifecycle management.

Integrates Feast feature store with MLflow for:
- Model training with feature engineering
- Model registry and versioning
- Model serving and predictions
"""

import os
import pickle
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import mlflow.lightgbm
import pandas as pd
from fastapi import HTTPException
from mlflow.tracking import MlflowClient

from app.feast.service import FeatureStoreService
from app.mlops.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelFramework,
    ModelInfo,
    ModelMetrics,
    ModelType,
    ModelVersionInfo,
    PredictionInput,
    PredictionOutput,
    RegisterModelRequest,
    RegisterModelResponse,
    TrainModelRequest,
    TrainModelResponse,
    MLOpsStatus,
)


class MLOpsService:
    """Service for managing ML lifecycle with Feast + MLflow."""

    def __init__(self):
        """Initialize MLOps service."""
        # MLflow configuration
        self.mlflow_tracking_uri = os.getenv(
            "MLFLOW_TRACKING_URI", "http://mlflow-service.asgard.svc.cluster.local:5000"
        )
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)

        # Initialize MLflow client
        self.mlflow_client = MlflowClient()

        # Initialize Feast service for feature management
        self.feast_service = FeatureStoreService()

        # Model cache for serving
        self.model_cache: Dict[str, Any] = {}

        # Monitoring storage (in-memory for now, can be moved to DB)
        self.monitoring_data: Dict[str, List[Dict[str, Any]]] = {}

        print(f"✅ MLOpsService initialized")
        print(f"   MLflow: {self.mlflow_tracking_uri}")
        print(f"   Feast repo: {self.feast_service.feast_repo_path}")

    # ========================================================================
    # Model Training (/models)
    # ========================================================================

    async def train_model(self, request: TrainModelRequest) -> TrainModelResponse:
        """
        Train a model using Feast features.

        Steps:
        1. Retrieve features from Feast
        2. Train model with specified framework
        3. Log to MLflow with metrics and artifacts
        4. Return training results
        """
        try:
            # Set or create experiment
            experiment = mlflow.get_experiment_by_name(request.experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(request.experiment_name)
            else:
                experiment_id = experiment.experiment_id

            # Start MLflow run
            with mlflow.start_run(experiment_id=experiment_id) as run:
                # Log parameters
                mlflow.log_params(request.hyperparameters.params)
                mlflow.set_tags(request.tags)
                mlflow.set_tag("framework", request.framework.value)
                mlflow.set_tag("model_type", request.model_type.value)

                # Get training data from Feast
                X_train, y_train = await self._get_training_data(request.data_source)

                # Train model based on framework
                model, metrics = await self._train_model_by_framework(
                    request.framework,
                    request.model_type,
                    X_train,
                    y_train,
                    request.hyperparameters.params,
                )

                # Log metrics
                mlflow.log_metrics(metrics.metrics)

                # Log model
                model_uri = await self._log_model(model, request.framework)

                return TrainModelResponse(
                    run_id=run.info.run_id,
                    experiment_id=experiment_id,
                    model_name=request.model_name,
                    model_uri=model_uri,
                    metrics=metrics,
                    artifact_uri=run.info.artifact_uri,
                    status="completed",
                    created_at=datetime.utcnow(),
                )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")

    async def _get_training_data(self, data_source) -> Tuple[pd.DataFrame, pd.Series]:
        """Retrieve training data from Feast."""
        try:
            # Convert entities dict to DataFrame
            entities_df = pd.DataFrame(data_source.entities)

            # Get features from Feast
            if data_source.feature_service:
                # Use feature service
                feature_vector = self.feast_service.store.get_historical_features(
                    entity_df=entities_df, features=[data_source.feature_service]
                ).to_df()
            elif data_source.feature_views:
                # Use feature views
                features = [
                    f"{fv}:*" for fv in data_source.feature_views
                ]  # Get all features from views
                feature_vector = self.feast_service.store.get_historical_features(
                    entity_df=entities_df, features=features
                ).to_df()
            else:
                raise ValueError("Either feature_service or feature_views must be provided")

            # Separate features and target
            y_train = feature_vector[data_source.target_column]
            X_train = feature_vector.drop(columns=[data_source.target_column])

            return X_train, y_train

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve training data: {str(e)}"
            )

    async def _train_model_by_framework(
        self,
        framework: ModelFramework,
        model_type: ModelType,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        params: Dict[str, Any],
    ) -> Tuple[Any, ModelMetrics]:
        """Train model based on specified framework."""
        metrics = {}

        if framework == ModelFramework.SKLEARN:
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            from sklearn.metrics import accuracy_score, mean_squared_error, r2_score

            if model_type == ModelType.CLASSIFICATION:
                model = RandomForestClassifier(**params)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_train)
                metrics["train_accuracy"] = accuracy_score(y_train, y_pred)
            else:  # REGRESSION
                model = RandomForestRegressor(**params)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_train)
                metrics["train_rmse"] = mean_squared_error(y_train, y_pred, squared=False)
                metrics["train_r2"] = r2_score(y_train, y_pred)

        elif framework == ModelFramework.XGBOOST:
            import xgboost as xgb
            from sklearn.metrics import accuracy_score, mean_squared_error, r2_score

            if model_type == ModelType.CLASSIFICATION:
                model = xgb.XGBClassifier(**params)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_train)
                metrics["train_accuracy"] = accuracy_score(y_train, y_pred)
            else:
                model = xgb.XGBRegressor(**params)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_train)
                metrics["train_rmse"] = mean_squared_error(y_train, y_pred, squared=False)
                metrics["train_r2"] = r2_score(y_train, y_pred)

        elif framework == ModelFramework.LIGHTGBM:
            import lightgbm as lgb
            from sklearn.metrics import accuracy_score, mean_squared_error, r2_score

            if model_type == ModelType.CLASSIFICATION:
                model = lgb.LGBMClassifier(**params)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_train)
                metrics["train_accuracy"] = accuracy_score(y_train, y_pred)
            else:
                model = lgb.LGBMRegressor(**params)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_train)
                metrics["train_rmse"] = mean_squared_error(y_train, y_pred, squared=False)
                metrics["train_r2"] = r2_score(y_train, y_pred)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Framework {framework} not implemented. Use sklearn, xgboost, or lightgbm.",
            )

        return model, ModelMetrics(metrics=metrics)

    async def _log_model(self, model: Any, framework: ModelFramework) -> str:
        """Log model to MLflow."""
        if framework == ModelFramework.SKLEARN:
            mlflow.sklearn.log_model(model, "model")
        elif framework == ModelFramework.XGBOOST:
            mlflow.xgboost.log_model(model, "model")
        elif framework == ModelFramework.LIGHTGBM:
            mlflow.lightgbm.log_model(model, "model")
        else:
            # Fallback to pickle
            mlflow.log_artifact(pickle.dumps(model), "model.pkl")

        return f"runs:/{mlflow.active_run().info.run_id}/model"

    # ========================================================================
    # Model Registry (/registry)
    # ========================================================================

    async def register_model(self, request: RegisterModelRequest) -> RegisterModelResponse:
        """Register a model to MLflow Model Registry."""
        try:
            model_uri = f"runs:/{request.run_id}/model"

            # Register model
            model_version = mlflow.register_model(
                model_uri=model_uri,
                name=request.model_name,
                tags=request.tags,
            )

            # Update version description
            if request.description:
                self.mlflow_client.update_model_version(
                    name=request.model_name,
                    version=model_version.version,
                    description=request.description,
                )

            return RegisterModelResponse(
                model_name=request.model_name,
                version=str(model_version.version),
                run_id=request.run_id,
                status="registered",
                created_at=datetime.utcnow(),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Model registration failed: {str(e)}")

    async def get_model_info(self, model_name: str) -> ModelInfo:
        """Get information about a registered model."""
        try:
            model = self.mlflow_client.get_registered_model(model_name)

            # Get all versions
            versions = self.mlflow_client.search_model_versions(f"name='{model_name}'")

            latest_versions = []
            for version in versions[:5]:  # Top 5 versions
                latest_versions.append(
                    ModelVersionInfo(
                        name=version.name,
                        version=version.version,
                        stage=version.current_stage,
                        run_id=version.run_id,
                        description=version.description,
                        tags=version.tags,
                        created_at=datetime.fromtimestamp(version.creation_timestamp / 1000),
                        updated_at=datetime.fromtimestamp(version.last_updated_timestamp / 1000),
                    )
                )

            return ModelInfo(
                name=model.name,
                description=model.description,
                tags=model.tags,
                latest_versions=latest_versions,
                created_at=datetime.fromtimestamp(model.creation_timestamp / 1000),
                updated_at=datetime.fromtimestamp(model.last_updated_timestamp / 1000),
            )

        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Model not found: {str(e)}")

    async def list_models(self) -> List[ModelInfo]:
        """List all registered models."""
        try:
            models = self.mlflow_client.search_registered_models()
            return [await self.get_model_info(model.name) for model in models]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")

    # ========================================================================
    # Model Serving (/serve)
    # ========================================================================

    async def predict(self, request: PredictionInput) -> PredictionOutput:
        """Make predictions using a registered model."""
        try:
            # Load model
            model, model_version, run_id = await self._load_model(
                request.model_name, request.model_version
            )

            # Get features
            if request.features:
                # Direct features provided
                X = pd.DataFrame([request.features])
            else:
                # Retrieve from Feast
                entities_df = pd.DataFrame(request.entities)
                feature_vector = self.feast_service.store.get_online_features(
                    entity_rows=entities_df.to_dict("records"),
                    features=["*"],  # Get all features
                ).to_df()
                X = feature_vector

            # Make predictions
            predictions = model.predict(X)

            response = PredictionOutput(
                predictions=predictions.tolist(),
                model_name=request.model_name,
                model_version=model_version,
                run_id=run_id,
                prediction_time=datetime.utcnow(),
            )

            if request.return_features:
                response.features = X.to_dict("list")

            return response

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    async def batch_predict(self, request: BatchPredictionRequest) -> BatchPredictionResponse:
        """Make batch predictions."""
        try:
            job_id = str(uuid.uuid4())

            # Load model
            model, model_version, run_id = await self._load_model(
                request.model_name, request.model_version
            )

            # Get features from Feast
            entities_df = pd.DataFrame(request.entities_df)

            if request.feature_service:
                feature_vector = self.feast_service.store.get_historical_features(
                    entity_df=entities_df, features=[request.feature_service]
                ).to_df()
            elif request.feature_views:
                features = [f"{fv}:*" for fv in request.feature_views]
                feature_vector = self.feast_service.store.get_historical_features(
                    entity_df=entities_df, features=features
                ).to_df()
            else:
                raise ValueError("Either feature_service or feature_views required")

            # Make predictions
            predictions = model.predict(feature_vector)

            # Add predictions to DataFrame
            result_df = feature_vector.copy()
            result_df["prediction"] = predictions

            # Save to S3 if output path provided
            output_path = request.output_path
            if output_path:
                result_df.to_parquet(output_path, index=False)
            else:
                output_path = f"s3://{self.feast_service.s3_bucket}/predictions/{job_id}.parquet"
                result_df.to_parquet(output_path, index=False)

            return BatchPredictionResponse(
                job_id=job_id,
                model_name=request.model_name,
                model_version=model_version,
                status="completed",
                output_path=output_path,
                created_at=datetime.utcnow(),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

    async def _load_model(
        self,
        model_name: str,
        version: Optional[str] = None,
    ) -> Tuple[Any, str, str]:
        """Load model from MLflow by name and version."""
        # Generate cache key
        cache_key = f"{model_name}:{version or 'latest'}"

        # Check cache
        if cache_key in self.model_cache:
            return self.model_cache[cache_key]

        # Determine model URI
        if version:
            model_uri = f"models:/{model_name}/{version}"
        else:
            model_uri = f"models:/{model_name}/latest"

        # Load model
        model = mlflow.pyfunc.load_model(model_uri)

        # Get model version info
        if version:
            version_info = self.mlflow_client.get_model_version(model_name, version)
        else:
            # Get latest version
            versions = self.mlflow_client.search_model_versions(f"name='{model_name}'")
            version_info = versions[0] if versions else None

        if not version_info:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

        model_version = version_info.version
        run_id = version_info.run_id

        # Cache model
        self.model_cache[cache_key] = (model, model_version, run_id)

        return model, model_version, run_id

    # ========================================================================
    # Status and Health
    # ========================================================================

    async def get_status(self) -> MLOpsStatus:
        """Get MLOps platform status."""
        try:
            # Check MLflow connection
            mlflow_available = True
            try:
                self.mlflow_client.search_experiments()
            except:
                mlflow_available = False

            # Check Feast
            feast_available = True
            try:
                feature_views = len(self.feast_service.feature_views)
            except:
                feast_available = False
                feature_views = 0

            # Count models and experiments
            registered_models = len(self.mlflow_client.search_registered_models())
            active_experiments = len(
                [
                    e
                    for e in self.mlflow_client.search_experiments()
                    if e.lifecycle_stage == "active"
                ]
            )

            return MLOpsStatus(
                mlflow_tracking_uri=self.mlflow_tracking_uri,
                mlflow_available=mlflow_available,
                feast_store_available=feast_available,
                registered_models=registered_models,
                active_experiments=active_experiments,
                feature_views=feature_views,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

    # ========================================================================
    # Model Monitoring
    # ========================================================================

    async def log_monitoring_metrics(self, request):
        """Log monitoring metrics for a model."""
        try:
            from app.mlops.schemas import MonitoringResponse

            monitoring_id = str(uuid.uuid4())

            # Calculate alerts based on thresholds
            alerts = []
            alert_triggered = False

            # Check for drift alerts (simple threshold-based)
            if request.metric_type.value in ["prediction_drift", "feature_drift"]:
                for metric_name, value in request.metrics.items():
                    if value > 0.1:  # 10% drift threshold
                        alerts.append(f"{metric_name} drift detected: {value:.3f}")
                        alert_triggered = True

            # Check for data quality alerts
            if request.metric_type.value == "data_quality":
                for metric_name, value in request.metrics.items():
                    if "missing" in metric_name and value > 0.05:  # 5% missing threshold
                        alerts.append(f"High missing rate in {metric_name}: {value:.3f}")
                        alert_triggered = True

            # Check for performance degradation
            if request.metric_type.value == "model_performance":
                for metric_name, value in request.metrics.items():
                    if "accuracy" in metric_name and value < 0.7:  # 70% threshold
                        alerts.append(f"Low {metric_name}: {value:.3f}")
                        alert_triggered = True

            # Store monitoring data
            model_key = f"{request.model_name}:{request.model_version}"
            if model_key not in self.monitoring_data:
                self.monitoring_data[model_key] = []

            monitoring_entry = {
                "monitoring_id": monitoring_id,
                "model_name": request.model_name,
                "model_version": request.model_version,
                "metric_type": request.metric_type.value,
                "metrics": request.metrics,
                "reference_data": request.reference_data,
                "current_data": request.current_data,
                "tags": request.tags,
                "alert_triggered": alert_triggered,
                "alerts": alerts,
                "timestamp": datetime.utcnow(),
            }

            self.monitoring_data[model_key].append(monitoring_entry)

            # Also log to MLflow if available
            try:
                with mlflow.start_run(run_name=f"monitoring_{monitoring_id}"):
                    mlflow.set_tag("model_name", request.model_name)
                    mlflow.set_tag("model_version", request.model_version)
                    mlflow.set_tag("metric_type", request.metric_type.value)
                    mlflow.log_metrics(request.metrics)
                    if alert_triggered:
                        mlflow.set_tag("alert_triggered", "true")
                        mlflow.set_tag("alerts", "; ".join(alerts))
            except Exception as e:
                print(f"Warning: Could not log to MLflow: {str(e)}")

            return MonitoringResponse(
                monitoring_id=monitoring_id,
                model_name=request.model_name,
                model_version=request.model_version,
                metric_type=request.metric_type.value,
                metrics=request.metrics,
                alert_triggered=alert_triggered,
                alerts=alerts,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Monitoring logging failed: {str(e)}")

    async def get_monitoring_history(self, request):
        """Get monitoring history for a model."""
        try:
            from app.mlops.schemas import MonitoringHistoryResponse, MonitoringResponse

            model_key = f"{request.model_name}:{request.model_version or '*'}"

            # Get all monitoring data for this model
            all_records = []
            for key, records in self.monitoring_data.items():
                if key.startswith(request.model_name):
                    if (
                        request.model_version is None
                        or key == f"{request.model_name}:{request.model_version}"
                    ):
                        all_records.extend(records)

            # Filter by metric type if specified
            if request.metric_type:
                all_records = [
                    r for r in all_records if r["metric_type"] == request.metric_type.value
                ]

            # Filter by date range if specified
            if request.start_date:
                all_records = [r for r in all_records if r["timestamp"] >= request.start_date]
            if request.end_date:
                all_records = [r for r in all_records if r["timestamp"] <= request.end_date]

            # Sort by timestamp descending
            all_records.sort(key=lambda x: x["timestamp"], reverse=True)

            # Apply limit
            limited_records = all_records[: request.limit]

            # Convert to response objects
            response_records = [MonitoringResponse(**record) for record in limited_records]

            # Calculate summary statistics
            summary = {
                "total_alerts": sum(1 for r in all_records if r["alert_triggered"]),
                "metric_types": list(set(r["metric_type"] for r in all_records)),
                "date_range": {
                    "start": min(r["timestamp"] for r in all_records) if all_records else None,
                    "end": max(r["timestamp"] for r in all_records) if all_records else None,
                },
            }

            return MonitoringHistoryResponse(
                model_name=request.model_name,
                model_version=request.model_version,
                total_records=len(all_records),
                records=response_records,
                summary=summary,
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get monitoring history: {str(e)}"
            )
