"""
MLOps Service for ML lifecycle management.

Simplified single-click deployment:
- One-click deployment: train + build + push + deploy
- Query models and versions from MLflow
- Platform health status

Note: Model inference is handled by deployed inference services, not here.
"""

import os
import uuid
import base64
import subprocess
import tempfile
import time
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
    ModelInfo,
    ModelVersionInfo,
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

        print(f"✅ MLOpsService initialized")
        print(f"   MLflow: {self.mlflow_tracking_uri}")
        print(f"   Feast repo: {self.feast_service.feast_repo_path}")

    # ========================================================================
    # Model Registry - Read Only (/models)
    # ========================================================================

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
    # End-to-End Deployment (/deploy)
    # ========================================================================

    async def deploy_model_end_to_end(self, request) -> dict:
        """
        Complete model deployment pipeline - SYNCHRONOUS:
        1. Train model via uploaded script
        2. Build Docker image
        3. Push to ECR
        4. Deploy to K8s with LoadBalancer
        5. Wait for external IP
        6. Return inference URL

        This is a blocking operation that waits for complete deployment.
        """
        import subprocess
        import tempfile
        from pathlib import Path

        start_time = time.time()

        print(f"🚀 Starting deployment for {request.model_name}...")

        # STEP 1: Train model
        print(f"📚 [1/4] Training model...")

        # Decode script content (handle both base64 and plain text)
        try:
            print(f"🔍 Attempting to decode script_content (length: {len(request.script_content)})")
            # Try base64 decode first
            script_bytes = base64.b64decode(request.script_content)
            script_text = script_bytes.decode("utf-8")
            print(f"✅ Script decoded from base64 (decoded length: {len(script_text)})")
        except Exception as decode_error:
            # If decode fails, assume it's already plain text
            print(f"⚠️  Base64 decode failed, using as plain text: {decode_error}")
            script_text = request.script_content
        
        print(f"📝 Script preview (first 200 chars):\n{script_text[:200]}...")

        try:
            training_result = self._run_training_sync(
                script_text,
                request.experiment_name,
                request.model_name,
                request.requirements or [],
                request.environment_vars or {},
                request.timeout,
                request.tags or {},
            )
        except Exception as training_error:
            import traceback

            error_detail = traceback.format_exc()
            error_msg = f"Training failed: {str(training_error)}"
            print(f"❌ {error_msg}")
            print(f"❌ Full traceback:\n{error_detail}")
            
            # Create detailed error message
            full_error_msg = (
                f"Training Failed\n\n"
                f"Error: {str(training_error)}\n\n"
                f"Make sure your training script:\n"
                f"1. Calls mlflow.start_run() to create a run\n"
                f"2. Trains your model\n"
                f"3. Logs the model with mlflow.<framework>.log_model(model, 'model')\n"
                f"4. Example frameworks: sklearn, xgboost, tensorflow, pytorch\n\n"
                f"Traceback:\n{error_detail}"
            )
            
            raise HTTPException(status_code=500, detail=full_error_msg)

        if not training_result or not training_result.get("run_id"):
            error_msg = (
                "Training completed but no MLflow run was created.\n\n"
                "Your script MUST:\n"
                "1. Call mlflow.start_run() to start tracking\n"
                "2. Train your model\n"
                "3. Log the model with mlflow.<framework>.log_model(model, 'model')\n"
                "   Examples: mlflow.sklearn.log_model(), mlflow.xgboost.log_model()\n"
                "4. End the run with mlflow.end_run() or use context manager\n\n"
                "Example script:\n"
                "  import mlflow\n"
                "  import mlflow.sklearn\n"
                "  from sklearn.ensemble import RandomForestClassifier\n\n"
                "  with mlflow.start_run():\n"
                "      model = RandomForestClassifier(n_estimators=100)\n"
                "      model.fit(X_train, y_train)\n"
                "      mlflow.sklearn.log_model(model, 'model')\n"
                "      mlflow.log_params({'n_estimators': 100})\n"
                "      accuracy = model.score(X_test, y_test)\n"
                "      mlflow.log_metric('accuracy', accuracy)\n"
            )
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        run_id = training_result["run_id"]
        model_version = training_result.get("version", "1")
        model_path = training_result.get("model_path")

        print(f"✅ Training completed: v{model_version}, run_id={run_id}")
        print(f"✅ Model path: {model_path}")

        # STEP 2: Build Docker image
        print(f"🐳 [2/4] Building Docker image...")

        ecr_registry = os.getenv("ECR_REGISTRY", "637423187518.dkr.ecr.eu-north-1.amazonaws.com")
        ecr_repo = os.getenv("ECR_REPO", "asgard-model")
        aws_region = os.getenv("AWS_DEFAULT_REGION", "eu-north-1")

        image_tag = f"{request.model_name.replace('_', '-')}-v{model_version}"
        image_uri = f"{ecr_registry}/{ecr_repo}:{image_tag}"

        if not self._build_docker_image(
            request.model_name, model_version, run_id, image_uri, aws_region, model_path
        ):
            raise HTTPException(status_code=500, detail="Docker build failed")

        print(f"✅ Image built: {image_uri}")

        # STEP 3: Push to ECR
        print(f"📤 [3/4] Pushing to ECR...")

        if not self._push_to_ecr(image_uri, ecr_registry, aws_region):
            raise HTTPException(status_code=500, detail="ECR push failed")

        print(f"✅ Pushed to ECR")

        # STEP 4: Deploy to K8s and wait for IP
        print(f"☸️  [4/4] Deploying to Kubernetes...")

        external_ip = self._deploy_to_k8s(
            request.model_name,
            model_version,
            run_id,
            image_uri,
            request.namespace,
            request.replicas,
            aws_region,
        )

        if not external_ip:
            raise HTTPException(
                status_code=500, detail="K8s deployment failed or external IP not assigned"
            )

        deployment_time = time.time() - start_time

        inference_url = f"http://{external_ip}"

        print(f"🎉 Deployment complete in {deployment_time:.1f}s!")
        print(f"   Inference URL: {inference_url}")

        # Return complete response
        return {
            "model_name": request.model_name,
            "experiment_name": request.experiment_name,
            "status": "deployed",
            "inference_url": inference_url,
            "external_ip": external_ip,
            "model_version": model_version,
            "run_id": run_id,
            "ecr_image": image_uri,
            "endpoints": {
                "health": f"{inference_url}/health",
                "metadata": f"{inference_url}/metadata",
                "predict": f"{inference_url}/predict",
                "root": inference_url,
            },
            "deployment_time_seconds": round(deployment_time, 2),
            "message": f"Model deployed successfully! Use {inference_url}/predict for inference",
        }

    def _run_training_sync(
        self, script_text, experiment_name, model_name, requirements, env_vars, timeout, tags
    ):
        """Run training synchronously and return result."""
        print(f"🔍 _run_training_sync called:")
        print(f"   Experiment: {experiment_name}")
        print(f"   Model: {model_name}")
        print(f"   Requirements: {requirements}")
        print(f"   Timeout: {timeout}")
        print(f"   Tags: {tags}")

        try:
            print(f"🔍 Creating temp directory...")
            with tempfile.TemporaryDirectory() as tmpdir:
                print(f"🔍 Temp dir created: {tmpdir}")
                script_path = Path(tmpdir) / "train.py"
                print(f"🔍 Script path: {script_path}")

                # Inject simple configuration without MLflow model logging
                injected_script = """# Auto-injected configuration (no MLflow model logging)
import os
import sys
import pickle
from pathlib import Path

# Setup environment
os.environ['GIT_PYTHON_REFRESH'] = 'quiet'

# Create model directory for saving in current working directory
MODEL_DIR = Path.cwd() / 'model_artifacts'
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / 'model.pkl'

print("✅ Configuration (No MLflow logging):")
print(f"   Working directory: {Path.cwd()}")
print(f"   Model save path: {MODEL_PATH}")
print(f"   To save your model: pickle.dump(model, open(MODEL_PATH, 'wb'))")

"""
                # Add user-provided environment variables
                if env_vars:
                    injected_script += "# User-provided environment variables\n"
                    for key, value in env_vars.items():
                        injected_script += f"os.environ['{key}'] = '{value}'\n"
                    injected_script += "\n"

                # Add the user's script
                injected_script += "# ========== User Training Script ==========\n"
                injected_script += script_text
                
                # Write the complete script
                script_path.write_text(injected_script)

                print(f"📝 Training script written to: {script_path}")
                print(f"� Full script content:\n{'='*60}")
                print(injected_script)
                print(f"{'='*60}\n")

                # Install requirements if provided
                if requirements:
                    print(f"📦 Installing {len(requirements)} requirements: {requirements}")
                    pip_result = subprocess.run(
                        ["pip", "install", "--quiet", "--no-cache-dir"] + requirements,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=tmpdir,
                    )
                    if pip_result.returncode != 0:
                        error_msg = f"Failed to install requirements: {pip_result.stderr}"
                        print(f"❌ {error_msg}")
                        raise Exception(error_msg)
                    print(f"✅ Requirements installed successfully")

                # Prepare environment for script execution with minimal MLflow features
                env = os.environ.copy()
                env["MLFLOW_TRACKING_URI"] = self.mlflow_tracking_uri
                env["MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING"] = "false"
                env["GIT_PYTHON_REFRESH"] = "quiet"
                env["EXPERIMENT_NAME"] = experiment_name
                env["MODEL_NAME"] = model_name
                env.update(env_vars)

                print(f"🏃 Executing training script with timeout={timeout}s...")
                print(
                    f"   Python: {subprocess.run(['which', 'python'], capture_output=True, text=True).stdout.strip()}"
                )
                print(f"   Working dir: {tmpdir}")
                print(f"   Environment vars: MLFLOW_TRACKING_URI, EXPERIMENT_NAME, MODEL_NAME + {len(env_vars)} custom vars")

                # Execute the training script
                result = subprocess.run(
                    ["python", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                    env=env,
                )

                print(f"\n{'='*60}")
                print(f"Script execution completed: returncode={result.returncode}")
                print(f"{'='*60}")
                
                if result.stdout:
                    print(f"STDOUT:\n{result.stdout}")
                
                if result.stderr:
                    print(f"STDERR:\n{result.stderr}")
                    
                print(f"{'='*60}\n")

                # Check if script executed successfully
                if result.returncode != 0:
                    error_msg = f"Training script failed with exit code {result.returncode}"
                    if result.stderr:
                        error_msg += f"\n\nError output:\n{result.stderr}"
                    if result.stdout:
                        error_msg += f"\n\nStandard output:\n{result.stdout}"
                    print(f"❌ {error_msg}")
                    raise Exception(error_msg)

                print(f"✅ Script executed successfully")

                # Check if model was saved in the temp directory
                model_dir = Path(tmpdir) / "model_artifacts"
                model_file = model_dir / "model.pkl"
                
                if not model_file.exists():
                    error_msg = (
                        f"No model file found at {model_file}.\n\n"
                        f"Your script MUST save the trained model using:\n"
                        f"  pickle.dump(model, open(MODEL_PATH, 'wb'))\n\n"
                        f"The MODEL_PATH variable is automatically set in your script."
                    )
                    print(f"❌ {error_msg}")
                    raise Exception(error_msg)

                print(f"✅ Model file found: {model_file}")

                # Copy model to a location outside temp directory for Docker build
                persistent_dir = Path("/tmp/asgard_models")
                persistent_dir.mkdir(exist_ok=True)
                
                # Generate a simple run_id
                import uuid
                run_id = str(uuid.uuid4())[:8]
                
                persistent_model_path = persistent_dir / f"model_{run_id}.pkl"
                import shutil
                shutil.copy(model_file, persistent_model_path)
                
                print(f"✅ Model saved to persistent location: {persistent_model_path}")
                print(f"✅ Model ID: {run_id}")

                return {
                    "run_id": run_id,
                    "version": "latest",
                    "model_path": str(persistent_model_path)
                }

        except subprocess.TimeoutExpired:
            error_msg = f"Training script timed out after {timeout} seconds. Consider increasing the timeout parameter."
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            print(f"❌ Training error: {e}")
            import traceback
            traceback.print_exc()
            # Re-raise the exception so the caller can handle it
            raise

    def _build_docker_image(self, model_name, model_version, run_id, image_uri, aws_region, model_path=None):
        """Build Docker image for model inference."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Copy model file to build context
                if model_path and Path(model_path).exists():
                    import shutil
                    shutil.copy(model_path, tmpdir_path / "model.pkl")
                    print(f"✅ Copied model from {model_path} to build context")

                # Create Dockerfile (minimal, no MLflow)
                dockerfile = tmpdir_path / "Dockerfile"
                dockerfile.write_text(
                    f"""FROM python:3.11-slim as builder
RUN pip install --no-cache-dir --user fastapi==0.104.1 uvicorn[standard]==0.24.0 scikit-learn==1.3.2 pandas==2.1.3 numpy==1.26.2 python-multipart==0.0.6

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
WORKDIR /app
ENV MODEL_NAME={model_name}
ENV MODEL_VERSION={model_version}
ENV RUN_ID={run_id}
COPY inference_service.py /app/
COPY model.pkl /app/
EXPOSE 80
CMD ["uvicorn", "inference_service:app", "--host", "0.0.0.0", "--port", "80"]
"""
                )

                # Create inference service (pickle-based, no MLflow)
                inference_service = tmpdir_path / "inference_service.py"
                inference_service.write_text(
                    """import os
import logging
import pickle
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Model Inference API", version="1.0.0")

model_name = os.getenv("MODEL_NAME")
model_version = os.getenv("MODEL_VERSION")
run_id = os.getenv("RUN_ID")
model = None

@app.on_event("startup")
async def load_model():
    global model
    try:
        model_path = "/app/model.pkl"
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        logger.info(f"Model loaded from {model_path}: {model_name} v{model_version}")
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
    return {"model_name": model_name, "model_version": model_version, "run_id": run_id, "model_loaded": model is not None}

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        import pandas as pd
        import numpy as np
        df = pd.DataFrame(request.inputs)
        predictions = model.predict(df)
        return {"predictions": predictions.tolist() if hasattr(predictions, "tolist") else list(predictions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.get("/")
async def root():
    return {"service": "Model Inference API (Pickle)", "model": model_name, "version": model_version}
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
