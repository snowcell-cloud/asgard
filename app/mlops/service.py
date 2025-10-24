"""
MLOps Service for ML lifecycle management.

Simplified service for script-based training and model serving:
- Upload and execute Python training scripts
- Register models to MLflow
- Serve models for inference
- Track training job status
"""

import os
import uuid
import base64
import subprocess
import tempfile
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import mlflow
import pandas as pd
import numpy as np
from fastapi import HTTPException
from mlflow.tracking import MlflowClient

from app.feast.service import FeatureStoreService
from app.mlops.schemas import (
    InferenceRequest,
    InferenceResponse,
    ModelInfo,
    ModelVersionInfo,
    RegisterModelRequest,
    RegisterModelResponse,
    TrainingJobStatus,
    TrainingScriptUploadRequest,
    TrainingScriptUploadResponse,
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

        # Training jobs storage (in-memory for now)
        self.training_jobs: Dict[str, Dict[str, Any]] = {}
        self.training_jobs_lock = threading.Lock()

        print(f"✅ MLOpsService initialized")
        print(f"   MLflow: {self.mlflow_tracking_uri}")
        print(f"   Feast repo: {self.feast_service.feast_repo_path}")

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
    # Script-based Training (/training/upload)
    # ========================================================================

    async def upload_and_execute_script(
        self, request: TrainingScriptUploadRequest
    ) -> TrainingScriptUploadResponse:
        """
        Upload and execute a Python training script.

        The script must:
        1. Use mlflow.start_run() to log experiments
        2. Call mlflow.log_model() to register the trained model
        3. Optionally use provided environment variables
        """
        try:
            # Generate job ID
            job_id = str(uuid.uuid4())[:8]

            # Decode script content (assuming base64 encoded)
            try:
                script_bytes = base64.b64decode(request.script_content)
                script_text = script_bytes.decode("utf-8")
            except Exception:
                # If not base64, treat as plain text
                script_text = request.script_content

            # Store job info
            job_info = {
                "job_id": job_id,
                "script_name": request.script_name,
                "experiment_name": request.experiment_name,
                "model_name": request.model_name,
                "status": "queued",
                "run_id": None,
                "model_version": None,
                "error": None,
                "created_at": datetime.utcnow(),
                "started_at": None,
                "completed_at": None,
                "logs": "",
            }

            with self.training_jobs_lock:
                self.training_jobs[job_id] = job_info

            # Execute script in background thread
            thread = threading.Thread(
                target=self._execute_training_script,
                args=(
                    job_id,
                    script_text,
                    request.experiment_name,
                    request.model_name,
                    request.requirements,
                    request.environment_vars,
                    request.timeout,
                    request.tags,
                ),
            )
            thread.daemon = True
            thread.start()

            return TrainingScriptUploadResponse(
                job_id=job_id,
                script_name=request.script_name,
                experiment_name=request.experiment_name,
                model_name=request.model_name,
                status="queued",
                created_at=datetime.utcnow(),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload script: {str(e)}")

    def _execute_training_script(
        self,
        job_id: str,
        script_text: str,
        experiment_name: str,
        model_name: str,
        requirements: List[str],
        environment_vars: Dict[str, str],
        timeout: int,
        tags: Dict[str, str],
    ):
        """Execute training script in isolated environment."""
        try:
            # Update status to running
            with self.training_jobs_lock:
                self.training_jobs[job_id]["status"] = "running"
                self.training_jobs[job_id]["started_at"] = datetime.utcnow()

            # Create temporary directory for script execution
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = Path(tmpdir) / "train.py"

                # Inject MLflow configuration into script
                injected_script = f"""
import os
import sys
import mlflow

# MLflow configuration
os.environ['MLFLOW_TRACKING_URI'] = '{self.mlflow_tracking_uri}'
mlflow.set_tracking_uri('{self.mlflow_tracking_uri}')
mlflow.set_experiment('{experiment_name}')

# User-provided environment variables
"""
                for key, value in environment_vars.items():
                    injected_script += f"os.environ['{key}'] = '{value}'\n"

                injected_script += "\n# User script\n" + script_text

                # Write script to file
                script_path.write_text(injected_script)

                # Install requirements if specified
                logs = ""
                if requirements:
                    logs += "Installing requirements...\n"
                    try:
                        result = subprocess.run(
                            [
                                "pip",
                                "install",
                                "--quiet",
                                "--no-cache-dir",
                            ]
                            + requirements,
                            capture_output=True,
                            text=True,
                            timeout=120,
                            cwd=tmpdir,
                        )
                        logs += result.stdout + result.stderr
                    except subprocess.TimeoutExpired:
                        logs += "Requirements installation timed out\n"

                # Execute the script
                logs += "\nExecuting training script...\n"
                try:
                    env = os.environ.copy()
                    env["MLFLOW_TRACKING_URI"] = self.mlflow_tracking_uri
                    env.update(environment_vars)

                    result = subprocess.run(
                        ["python", str(script_path)],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=tmpdir,
                        env=env,
                    )

                    logs += result.stdout
                    if result.stderr:
                        logs += "\nStderr:\n" + result.stderr

                    # Check if execution was successful
                    if result.returncode == 0:
                        # Try to get the latest run from the experiment
                        experiment = mlflow.get_experiment_by_name(experiment_name)
                        if experiment:
                            runs = mlflow.search_runs(
                                experiment_ids=[experiment.experiment_id],
                                order_by=["start_time DESC"],
                                max_results=1,
                            )

                            if not runs.empty:
                                run_id = runs.iloc[0]["run_id"]

                                # Try to register the model
                                try:
                                    model_uri = f"runs:/{run_id}/model"
                                    result = mlflow.register_model(model_uri, model_name)
                                    model_version = result.version

                                    with self.training_jobs_lock:
                                        self.training_jobs[job_id]["run_id"] = run_id
                                        self.training_jobs[job_id]["model_version"] = model_version
                                        self.training_jobs[job_id]["status"] = "completed"
                                        self.training_jobs[job_id]["logs"] = logs
                                        self.training_jobs[job_id][
                                            "completed_at"
                                        ] = datetime.utcnow()
                                except Exception as reg_error:
                                    logs += f"\nModel registration failed: {str(reg_error)}\n"
                                    with self.training_jobs_lock:
                                        self.training_jobs[job_id]["run_id"] = run_id
                                        self.training_jobs[job_id]["status"] = "completed"
                                        self.training_jobs[job_id]["logs"] = logs
                                        self.training_jobs[job_id][
                                            "completed_at"
                                        ] = datetime.utcnow()
                            else:
                                logs += "\nNo runs found in experiment\n"
                                with self.training_jobs_lock:
                                    self.training_jobs[job_id]["status"] = "failed"
                                    self.training_jobs[job_id]["error"] = "No MLflow run created"
                                    self.training_jobs[job_id]["logs"] = logs
                                    self.training_jobs[job_id]["completed_at"] = datetime.utcnow()
                    else:
                        with self.training_jobs_lock:
                            self.training_jobs[job_id]["status"] = "failed"
                            self.training_jobs[job_id][
                                "error"
                            ] = f"Script exited with code {result.returncode}"
                            self.training_jobs[job_id]["logs"] = logs
                            self.training_jobs[job_id]["completed_at"] = datetime.utcnow()

                except subprocess.TimeoutExpired:
                    logs += f"\nScript execution timed out after {timeout} seconds\n"
                    with self.training_jobs_lock:
                        self.training_jobs[job_id]["status"] = "failed"
                        self.training_jobs[job_id]["error"] = "Execution timeout"
                        self.training_jobs[job_id]["logs"] = logs
                        self.training_jobs[job_id]["completed_at"] = datetime.utcnow()

        except Exception as e:
            with self.training_jobs_lock:
                self.training_jobs[job_id]["status"] = "failed"
                self.training_jobs[job_id]["error"] = str(e)
                self.training_jobs[job_id]["completed_at"] = datetime.utcnow()

    async def get_training_job_status(self, job_id: str) -> TrainingJobStatus:
        """Get status of a training job."""
        with self.training_jobs_lock:
            if job_id not in self.training_jobs:
                raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")

            job = self.training_jobs[job_id]

            # Calculate duration if completed
            duration_seconds = None
            if job["completed_at"] and job["started_at"]:
                duration_seconds = (job["completed_at"] - job["started_at"]).total_seconds()

            return TrainingJobStatus(
                job_id=job["job_id"],
                script_name=job["script_name"],
                experiment_name=job["experiment_name"],
                model_name=job["model_name"],
                status=job["status"],
                run_id=job["run_id"],
                model_version=job["model_version"],
                logs=job.get("logs"),
                error=job["error"],
                created_at=job["created_at"],
                started_at=job["started_at"],
                completed_at=job["completed_at"],
                duration_seconds=duration_seconds,
            )

    # ========================================================================
    # Model Inference (/inference)
    # ========================================================================

    async def inference(self, request: InferenceRequest) -> InferenceResponse:
        """
        Run inference on a deployed model.

        This is a simplified inference endpoint that loads the model
        and makes predictions on the provided input data.
        """
        try:
            start_time = time.time()

            # Load model
            model, model_version, run_id = await self._load_model(
                request.model_name, request.model_version
            )

            # Prepare input data
            X = pd.DataFrame(request.inputs)

            # Make predictions
            predictions = model.predict(X)

            # Get probabilities if requested and model supports it
            probabilities = None
            if request.return_probabilities:
                try:
                    if hasattr(model, "predict_proba"):
                        probabilities = model.predict_proba(X).tolist()
                except Exception:
                    pass  # Model doesn't support probabilities

            # Calculate inference time
            inference_time_ms = (time.time() - start_time) * 1000

            return InferenceResponse(
                model_name=request.model_name,
                model_version=model_version,
                predictions=(
                    predictions.tolist() if hasattr(predictions, "tolist") else list(predictions)
                ),
                probabilities=probabilities,
                inference_time_ms=round(inference_time_ms, 2),
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
