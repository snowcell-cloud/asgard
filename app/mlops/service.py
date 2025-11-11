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
from app.mlops.deployment_service import ModelDeploymentService


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

        # Initialize deployment service for automated model deployment
        self.deployment_service = ModelDeploymentService()

        # Model cache for serving
        self.model_cache: Dict[str, Any] = {}

        # Training jobs storage (in-memory for now)
        self.training_jobs: Dict[str, Dict[str, Any]] = {}
        self.training_jobs_lock = threading.Lock()

        # Deployment jobs storage (in-memory for now)
        self.deployment_jobs: Dict[str, Dict[str, Any]] = {}
        self.deployment_jobs_lock = threading.Lock()

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

                                # Check if model is already registered in this run
                                # (training script might have registered it)
                                model_version = None
                                try:
                                    client = mlflow.tracking.MlflowClient()
                                    registered_model = client.get_registered_model(model_name)

                                    # Find version with matching run_id
                                    for mv in client.search_model_versions(f"name='{model_name}'"):
                                        if mv.run_id == run_id:
                                            model_version = mv.version
                                            logs += f"\n✅ Model already registered: {model_name} version {model_version}\n"
                                            break

                                    # If not found, register it
                                    if not model_version:
                                        model_uri = f"runs:/{run_id}/model"
                                        result = mlflow.register_model(model_uri, model_name)
                                        model_version = result.version
                                        logs += f"\n✅ Model registered: {model_name} version {model_version}\n"

                                except Exception as check_error:
                                    # Model doesn't exist yet, try to register it
                                    try:
                                        model_uri = f"runs:/{run_id}/model"
                                        result = mlflow.register_model(model_uri, model_name)
                                        model_version = result.version
                                        logs += f"\n✅ Model registered: {model_name} version {model_version}\n"
                                    except Exception as reg_error:
                                        logs += (
                                            f"\n⚠️  Model registration failed: {str(reg_error)}\n"
                                        )

                                if model_version:
                                    # Update job status
                                    model_version = int(model_version)

                                    with self.training_jobs_lock:
                                        self.training_jobs[job_id]["run_id"] = run_id
                                        self.training_jobs[job_id]["model_version"] = model_version
                                        self.training_jobs[job_id]["status"] = "completed"
                                        self.training_jobs[job_id]["logs"] = logs
                                        self.training_jobs[job_id][
                                            "completed_at"
                                        ] = datetime.utcnow()

                                    # 🚀 AUTOMATED DEPLOYMENT: Build image and deploy to EKS
                                    logs += "\n" + "=" * 80 + "\n"
                                    logs += "🚀 Starting automated deployment to OVH EKS...\n"
                                    logs += "=" * 80 + "\n"

                                    try:
                                        deployment_result = (
                                            self.deployment_service.deploy_model_after_training(
                                                model_name=model_name,
                                                model_version=str(model_version),
                                                run_id=run_id,
                                                tags=tags,
                                            )
                                        )

                                        if deployment_result.get("status") == "deployed":
                                            logs += f"\n✅ Deployment successful!\n"
                                            logs += f"   Deployment ID: {deployment_result['deployment_id']}\n"
                                            logs += f"   Image: {deployment_result['image_uri']}\n"
                                            logs += (
                                                f"   Namespace: {deployment_result['namespace']}\n"
                                            )
                                            logs += f"   Endpoint: {deployment_result['deployment_info']['endpoint']}\n"

                                            with self.training_jobs_lock:
                                                self.training_jobs[job_id][
                                                    "deployment_info"
                                                ] = deployment_result
                                                self.training_jobs[job_id]["logs"] = logs
                                        else:
                                            logs += f"\n⚠️  Deployment failed: {deployment_result.get('error', 'Unknown error')}\n"
                                            with self.training_jobs_lock:
                                                self.training_jobs[job_id]["deployment_error"] = (
                                                    deployment_result.get("error")
                                                )
                                                self.training_jobs[job_id]["logs"] = logs

                                    except Exception as deploy_error:
                                        logs += f"\n❌ Deployment exception: {str(deploy_error)}\n"
                                        with self.training_jobs_lock:
                                            self.training_jobs[job_id]["deployment_error"] = str(
                                                deploy_error
                                            )
                                            self.training_jobs[job_id]["logs"] = logs
                                else:
                                    # Model version not found, mark as completed without deployment
                                    logs += "\n⚠️  Model version not found, skipping deployment\n"
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

    # ========================================================================
    # End-to-End Deployment (/deploy)
    # ========================================================================

    async def deploy_model_end_to_end(self, request) -> dict:
        """
        Complete model deployment pipeline:
        1. Train model via uploaded script
        2. Build Docker image
        3. Push to ECR
        4. Deploy to K8s with LoadBalancer

        Returns deployment URL and status.
        """
        import subprocess
        import tempfile
        from pathlib import Path

        job_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Store deployment job info
        deployment_info = {
            "job_id": job_id,
            "model_name": request.model_name,
            "experiment_name": request.experiment_name,
            "status": "training",
            "deployment_url": None,
            "external_ip": None,
            "model_version": None,
            "run_id": None,
            "ecr_image": None,
            "error": None,
            "created_at": datetime.utcnow(),
            "completed_at": None,
        }

        # Store in deployment jobs dict
        with self.deployment_jobs_lock:
            self.deployment_jobs[job_id] = deployment_info

        # Start deployment in background thread
        thread = threading.Thread(
            target=self._execute_full_deployment,
            args=(job_id, request),
        )
        thread.daemon = True
        thread.start()

        # Return immediately with job ID
        return {
            "job_id": job_id,
            "model_name": request.model_name,
            "experiment_name": request.experiment_name,
            "status": "training",
            "message": f"Deployment started. Use /mlops/deployments/{job_id} to check status",
        }

    def _execute_full_deployment(self, job_id: str, request):
        """Execute complete deployment workflow in background."""
        try:
            # Get deployment info from storage
            with self.deployment_jobs_lock:
                if job_id not in self.deployment_jobs:
                    return
                deployment_info = self.deployment_jobs[job_id]

            # STEP 1: Train model
            with self.deployment_jobs_lock:
                deployment_info["status"] = "training"
            print(f"🚀 [{job_id}] Starting training...")

            training_request = {
                "script_name": request.script_name,
                "script_content": request.script_content,
                "experiment_name": request.experiment_name,
                "model_name": request.model_name,
                "requirements": request.requirements or [],
                "environment_vars": request.environment_vars or {},
                "timeout": request.timeout,
                "tags": request.tags or {},
            }

            # Execute training synchronously within this thread
            from app.mlops.schemas import TrainingScriptUploadRequest

            train_req = TrainingScriptUploadRequest(**training_request)

            # Decode and execute script
            try:
                script_bytes = base64.b64decode(request.script_content)
                script_text = script_bytes.decode("utf-8")
            except:
                script_text = request.script_content

            # Execute training
            training_result = self._run_training_sync(
                script_text,
                request.experiment_name,
                request.model_name,
                request.requirements or [],
                request.environment_vars or {},
                request.timeout,
                request.tags or {},
            )

            if not training_result or not training_result.get("run_id"):
                with self.deployment_jobs_lock:
                    deployment_info["status"] = "failed"
                    deployment_info["error"] = "Training failed"
                    deployment_info["completed_at"] = datetime.utcnow()
                return

            with self.deployment_jobs_lock:
                deployment_info["run_id"] = training_result["run_id"]
                deployment_info["model_version"] = training_result.get("version", "1")

            print(f"✅ [{job_id}] Training completed: v{deployment_info['model_version']}")

            # STEP 2: Build Docker image
            with self.deployment_jobs_lock:
                deployment_info["status"] = "building"
            print(f"🐳 [{job_id}] Building Docker image...")

            ecr_registry = os.getenv(
                "ECR_REGISTRY", "637423187518.dkr.ecr.eu-north-1.amazonaws.com"
            )
            ecr_repo = os.getenv("ECR_REPO", "asgard-model")
            aws_region = os.getenv("AWS_DEFAULT_REGION", "eu-north-1")

            image_tag = (
                f"{request.model_name.replace('_', '-')}-v{deployment_info['model_version']}"
            )
            image_uri = f"{ecr_registry}/{ecr_repo}:{image_tag}"

            # Build image
            if not self._build_docker_image(
                request.model_name,
                deployment_info["model_version"],
                deployment_info["run_id"],
                image_uri,
                aws_region,
            ):
                with self.deployment_jobs_lock:
                    deployment_info["status"] = "failed"
                    deployment_info["error"] = "Docker build failed"
                    deployment_info["completed_at"] = datetime.utcnow()
                return

            with self.deployment_jobs_lock:
                deployment_info["ecr_image"] = image_uri
            print(f"✅ [{job_id}] Image built: {image_uri}")

            # STEP 3: Push to ECR
            with self.deployment_jobs_lock:
                deployment_info["status"] = "pushing"
            print(f"📤 [{job_id}] Pushing to ECR...")

            if not self._push_to_ecr(image_uri, ecr_registry, aws_region):
                with self.deployment_jobs_lock:
                    deployment_info["status"] = "failed"
                    deployment_info["error"] = "ECR push failed"
                    deployment_info["completed_at"] = datetime.utcnow()
                return

            print(f"✅ [{job_id}] Pushed to ECR")

            # STEP 4: Deploy to K8s
            with self.deployment_jobs_lock:
                deployment_info["status"] = "deploying"
            print(f"☸️  [{job_id}] Deploying to Kubernetes...")

            external_ip = self._deploy_to_k8s(
                request.model_name,
                deployment_info["model_version"],
                deployment_info["run_id"],
                image_uri,
                request.namespace,
                request.replicas,
                aws_region,
            )

            if not external_ip:
                with self.deployment_jobs_lock:
                    deployment_info["status"] = "failed"
                    deployment_info["error"] = "K8s deployment failed or IP not assigned"
                    deployment_info["completed_at"] = datetime.utcnow()
                return

            with self.deployment_jobs_lock:
                deployment_info["external_ip"] = external_ip
                deployment_info["deployment_url"] = f"http://{external_ip}"
                deployment_info["status"] = "deployed"
                deployment_info["completed_at"] = datetime.utcnow()

            print(f"🎉 [{job_id}] Deployment complete!")
            print(f"   URL: {deployment_info['deployment_url']}")

        except Exception as e:
            with self.deployment_jobs_lock:
                deployment_info["status"] = "failed"
                deployment_info["error"] = str(e)
                deployment_info["completed_at"] = datetime.utcnow()
            print(f"❌ [{job_id}] Deployment failed: {e}")

    def _run_training_sync(
        self, script_text, experiment_name, model_name, requirements, env_vars, timeout, tags
    ):
        """Run training synchronously and return result."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = Path(tmpdir) / "train.py"

                # Inject MLflow configuration
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
                for key, value in env_vars.items():
                    injected_script += f"os.environ['{key}'] = '{value}'\n"

                injected_script += "\n# User script\n" + script_text
                script_path.write_text(injected_script)

                # Install requirements
                if requirements:
                    subprocess.run(
                        ["pip", "install", "--quiet", "--no-cache-dir"] + requirements,
                        timeout=120,
                        cwd=tmpdir,
                    )

                # Execute script
                env = os.environ.copy()
                env["MLFLOW_TRACKING_URI"] = self.mlflow_tracking_uri
                env.update(env_vars)

                result = subprocess.run(
                    ["python", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                    env=env,
                )

                if result.returncode == 0:
                    # Get latest run
                    experiment = mlflow.get_experiment_by_name(experiment_name)
                    if experiment:
                        runs = mlflow.search_runs(
                            experiment_ids=[experiment.experiment_id],
                            order_by=["start_time DESC"],
                            max_results=1,
                        )

                        if not runs.empty:
                            run_id = runs.iloc[0]["run_id"]

                            # Try to get model version
                            try:
                                client = mlflow.tracking.MlflowClient()
                                for mv in client.search_model_versions(f"name='{model_name}'"):
                                    if mv.run_id == run_id:
                                        return {"run_id": run_id, "version": mv.version}
                            except:
                                pass

                            return {"run_id": run_id, "version": "1"}

                return None

        except Exception as e:
            print(f"Training error: {e}")
            return None

    def _build_docker_image(self, model_name, model_version, run_id, image_uri, aws_region):
        """Build Docker image for model inference."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Create Dockerfile
                dockerfile = tmpdir_path / "Dockerfile"
                dockerfile.write_text(
                    f"""FROM python:3.11-slim as builder
RUN pip install --no-cache-dir --user mlflow==2.16.2 fastapi==0.104.1 uvicorn[standard]==0.24.0 scikit-learn==1.3.2 pandas==2.1.3 numpy==1.26.2 boto3==1.34.0 python-multipart==0.0.6

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
WORKDIR /app
ENV MLFLOW_TRACKING_URI=http://mlflow-service.asgard.svc.cluster.local:5000
ENV MODEL_NAME={model_name}
ENV MODEL_VERSION={model_version}
ENV RUN_ID={run_id}
ENV AWS_DEFAULT_REGION={aws_region}
COPY inference_service.py /app/
EXPOSE 80
CMD ["uvicorn", "inference_service:app", "--host", "0.0.0.0", "--port", "80"]
"""
                )

                # Create inference service
                inference_service = tmpdir_path / "inference_service.py"
                inference_service.write_text(
                    """import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow.pyfunc
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Model Inference API", version="1.0.0")

model_name = os.getenv("MODEL_NAME")
model_version = os.getenv("MODEL_VERSION")
run_id = os.getenv("RUN_ID")
mlflow_uri = os.getenv("MLFLOW_TRACKING_URI")
model = None

@app.on_event("startup")
async def load_model():
    global model
    try:
        import mlflow
        mlflow.set_tracking_uri(mlflow_uri)
        model_uri = f"runs:/{run_id}/model"
        model = mlflow.pyfunc.load_model(model_uri)
        logger.info(f"Model loaded: {model_name} v{model_version}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")

class PredictRequest(BaseModel):
    inputs: Dict[str, List[Any]]

class PredictResponse(BaseModel):
    predictions: List[Any]

@app.get("/health")
async def health():
    return {"status": "healthy" if model else "model_not_loaded", "model": {"name": model_name, "version": model_version, "run_id": run_id}}

@app.get("/metadata")
async def metadata():
    return {"model_name": model_name, "model_version": model_version, "run_id": run_id, "mlflow_uri": mlflow_uri, "model_loaded": model is not None}

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        import pandas as pd
        df = pd.DataFrame(request.inputs)
        predictions = model.predict(df)
        return {"predictions": predictions.tolist() if hasattr(predictions, "tolist") else list(predictions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.get("/")
async def root():
    return {"service": "Model Inference API", "model": model_name, "version": model_version}
"""
                )

                # Build image
                result = subprocess.run(
                    ["docker", "build", "-t", image_uri, "."],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                return result.returncode == 0

        except Exception as e:
            print(f"Build error: {e}")
            return False

    def _push_to_ecr(self, image_uri, ecr_registry, aws_region):
        """Push Docker image to ECR."""
        try:
            # ECR login
            result = subprocess.run(
                ["aws", "ecr", "get-login-password", "--region", aws_region],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return False

            password = result.stdout.strip()

            subprocess.run(
                ["docker", "login", "--username", "AWS", "--password-stdin", ecr_registry],
                input=password,
                text=True,
                timeout=30,
            )

            # Push image
            result = subprocess.run(
                ["docker", "push", image_uri],
                capture_output=True,
                text=True,
                timeout=600,
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Push error: {e}")
            return False

    def _deploy_to_k8s(
        self, model_name, model_version, run_id, image_uri, namespace, replicas, aws_region
    ):
        """Deploy to Kubernetes and return external IP."""
        try:
            deployment_name = f"{model_name.replace('_', '-')}-inference"
            service_name = f"{model_name.replace('_', '-')}-service"

            # Create AWS credentials secret
            aws_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")

            if aws_key and aws_secret:
                subprocess.run(
                    [
                        "kubectl",
                        "create",
                        "secret",
                        "generic",
                        "aws-credentials",
                        f"--from-literal=AWS_ACCESS_KEY_ID={aws_key}",
                        f"--from-literal=AWS_SECRET_ACCESS_KEY={aws_secret}",
                        f"--namespace={namespace}",
                        "--dry-run=client",
                        "-o",
                        "yaml",
                    ],
                    capture_output=True,
                )

                subprocess.run(
                    ["kubectl", "apply", "-f", "-"],
                    input=f"""apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: {namespace}
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: {aws_key}
  AWS_SECRET_ACCESS_KEY: {aws_secret}
""",
                    text=True,
                    capture_output=True,
                )

            # Create deployment
            deployment_yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {deployment_name}
  namespace: {namespace}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {deployment_name}
  template:
    metadata:
      labels:
        app: {deployment_name}
    spec:
      imagePullSecrets:
      - name: ecr-credentials
      containers:
      - name: inference
        image: {image_uri}
        ports:
        - containerPort: 80
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: AWS_ACCESS_KEY_ID
              optional: true
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: AWS_SECRET_ACCESS_KEY
              optional: true
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 60
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  namespace: {namespace}
spec:
  type: LoadBalancer
  selector:
    app: {deployment_name}
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
"""

            # Apply deployment
            subprocess.run(
                ["kubectl", "apply", "-f", "-"],
                input=deployment_yaml,
                text=True,
                capture_output=True,
                timeout=30,
            )

            # Wait for external IP (max 3 minutes)
            for _ in range(36):
                time.sleep(5)
                result = subprocess.run(
                    [
                        "kubectl",
                        "get",
                        "svc",
                        service_name,
                        "-n",
                        namespace,
                        "-o",
                        "jsonpath={.status.loadBalancer.ingress[0].ip}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                external_ip = result.stdout.strip()
                if external_ip and external_ip != "<pending>":
                    return external_ip

            return None

        except Exception as e:
            print(f"Deploy error: {e}")
            return None

    async def get_deployment_status(self, job_id: str) -> dict:
        """Get status of a deployment job."""
        with self.deployment_jobs_lock:
            if job_id not in self.deployment_jobs:
                raise HTTPException(status_code=404, detail=f"Deployment job {job_id} not found")

            job = self.deployment_jobs[job_id]

            # Calculate duration if completed
            duration_seconds = None
            if job["completed_at"] and job["created_at"]:
                duration_seconds = (job["completed_at"] - job["created_at"]).total_seconds()

            return {
                "job_id": job["job_id"],
                "model_name": job["model_name"],
                "experiment_name": job["experiment_name"],
                "status": job["status"],
                "deployment_url": job["deployment_url"],
                "external_ip": job["external_ip"],
                "model_version": job["model_version"],
                "run_id": job["run_id"],
                "ecr_image": job["ecr_image"],
                "error": job["error"],
                "created_at": job["created_at"],
                "completed_at": job["completed_at"],
                "duration_seconds": duration_seconds,
            }
