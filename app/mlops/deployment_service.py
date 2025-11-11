"""
Enhanced MLOps Service with Automated Model Deployment.

Extends the base MLOps service to:
1. Train model via /mlops/training/upload
2. Automatically build Docker image with trained model
3. Push to ECR (637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model)
4. Deploy to OVH EKS (asgard namespace)
"""

import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import mlflow
from mlflow.tracking import MlflowClient


class ModelDeploymentService:
    """Service to automate model containerization and deployment."""

    def __init__(self):
        """Initialize deployment service."""
        self.ecr_registry = "637423187518.dkr.ecr.eu-north-1.amazonaws.com"
        self.ecr_repository = "asgard-model"
        self.aws_region = "eu-north-1"
        self.k8s_namespace = "asgard"
        self.mlflow_uri = os.getenv(
            "MLFLOW_TRACKING_URI", "http://mlflow-service.asgard.svc.cluster.local:5000"
        )

        self.mlflow_client = MlflowClient()

        print(f"✅ ModelDeploymentService initialized")
        print(f"   ECR: {self.ecr_registry}/{self.ecr_repository}")
        print(f"   Namespace: {self.k8s_namespace}")

    def deploy_model_after_training(
        self, model_name: str, model_version: str, run_id: str, tags: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Deploy a trained model to EKS.

        This method is called automatically after training completes.

        Args:
            model_name: Name of the registered model
            model_version: Version number of the model
            run_id: MLflow run ID
            tags: Additional tags for deployment

        Returns:
            Deployment status and details
        """
        try:
            deployment_id = (
                f"{model_name}-{model_version}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            )
            image_tag = f"{model_name}-v{model_version}"

            print(f"\n{'='*80}")
            print(f"🚀 Starting automated deployment for {model_name} v{model_version}")
            print(f"{'='*80}\n")

            # Step 1: Build Docker image
            print("📦 Step 1: Building Docker image...")
            image_uri = self._build_model_image(
                model_name=model_name,
                model_version=model_version,
                run_id=run_id,
                image_tag=image_tag,
            )
            print(f"   ✅ Image built: {image_uri}")

            # Step 2: Push to ECR
            print("\n📤 Step 2: Pushing to ECR...")
            self._push_to_ecr(image_uri)
            print(f"   ✅ Image pushed to ECR")

            # Step 3: Deploy to EKS
            print("\n🚀 Step 3: Deploying to OVH EKS...")
            deployment_info = self._deploy_to_eks(
                model_name=model_name,
                model_version=model_version,
                image_uri=image_uri,
                deployment_id=deployment_id,
                tags=tags,
            )
            print(f"   ✅ Deployed to namespace: {self.k8s_namespace}")

            print(f"\n{'='*80}")
            print(f"✅ Deployment completed successfully!")
            print(f"{'='*80}\n")

            return {
                "deployment_id": deployment_id,
                "model_name": model_name,
                "model_version": model_version,
                "image_uri": image_uri,
                "namespace": self.k8s_namespace,
                "status": "deployed",
                "deployment_info": deployment_info,
                "deployed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            return {
                "deployment_id": deployment_id,
                "model_name": model_name,
                "model_version": model_version,
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat(),
            }

    def _build_model_image(
        self, model_name: str, model_version: str, run_id: str, image_tag: str
    ) -> str:
        """Build Docker image with the trained model."""

        image_uri = f"{self.ecr_registry}/{self.ecr_repository}:{image_tag}"

        # Create temporary directory for build context
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create Dockerfile
            dockerfile_content = f"""# Production inference image for {model_name}
FROM python:3.11-slim

# Install dependencies
RUN pip install --no-cache-dir \\
    mlflow==2.16.2 \\
    fastapi==0.104.1 \\
    uvicorn[standard]==0.24.0 \\
    scikit-learn==1.3.2 \\
    pandas==2.1.3 \\
    numpy==1.26.2 \\
    boto3==1.34.0 \\
    requests==2.31.0

# Set environment variables
ENV MLFLOW_TRACKING_URI="{self.mlflow_uri}" \\
    MODEL_NAME="{model_name}" \\
    MODEL_VERSION="{model_version}" \\
    PORT=8080 \\
    PYTHONUNBUFFERED=1

# Create app directory
WORKDIR /app

# Copy inference service
COPY inference_service.py .

# Create non-root user
RUN groupadd -r mluser && useradd -r -g mluser mluser && \\
    chown -R mluser:mluser /app

USER mluser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8080/health').raise_for_status()" || exit 1

# Expose port
EXPOSE 8080

# Run inference service
CMD ["python", "inference_service.py"]
"""

            dockerfile_path = tmpdir_path / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            # Copy inference service to build context
            inference_service_path = Path(
                "/home/hac/downloads/code/asgard-dev/ml_deployment/inference_service.py"
            )
            if inference_service_path.exists():
                import shutil

                shutil.copy(inference_service_path, tmpdir_path / "inference_service.py")
            else:
                # Create a minimal inference service if the file doesn't exist
                self._create_minimal_inference_service(tmpdir_path / "inference_service.py")

            # Build Docker image
            print(f"   Building image: {image_uri}")
            build_cmd = [
                "docker",
                "build",
                "-t",
                image_uri,
                "-f",
                str(dockerfile_path),
                str(tmpdir_path),
            ]

            result = subprocess.run(build_cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                raise Exception(f"Docker build failed: {result.stderr}")

            print(f"   Build output: {result.stdout[-200:]}")  # Last 200 chars

        return image_uri

    def _create_minimal_inference_service(self, output_path: Path):
        """Create a minimal inference service file."""
        content = """import os
import mlflow
import mlflow.sklearn
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Model Inference Service")

MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_VERSION = os.getenv("MODEL_VERSION", "latest")
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI")

mlflow.set_tracking_uri(MLFLOW_URI)
model = None

@app.on_event("startup")
async def load_model():
    global model
    model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
    model = mlflow.sklearn.load_model(model_uri)

@app.get("/health")
async def health():
    return {"status": "healthy", "model": MODEL_NAME, "version": MODEL_VERSION}

@app.post("/predict")
async def predict(data: dict):
    import pandas as pd
    df = pd.DataFrame(data["inputs"])
    predictions = model.predict(df)
    return {"predictions": predictions.tolist()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
"""
        output_path.write_text(content)

    def _push_to_ecr(self, image_uri: str):
        """Push Docker image to ECR."""

        # Login to ECR
        print("   Authenticating with ECR...")
        login_cmd = ["aws", "ecr", "get-login-password", "--region", self.aws_region]

        login_result = subprocess.run(login_cmd, capture_output=True, text=True, timeout=30)

        if login_result.returncode != 0:
            raise Exception(f"ECR login failed: {login_result.stderr}")

        # Docker login
        docker_login_cmd = [
            "docker",
            "login",
            "--username",
            "AWS",
            "--password-stdin",
            self.ecr_registry,
        ]

        docker_login_result = subprocess.run(
            docker_login_cmd, input=login_result.stdout, capture_output=True, text=True, timeout=30
        )

        if docker_login_result.returncode != 0:
            raise Exception(f"Docker login failed: {docker_login_result.stderr}")

        # Push image
        print(f"   Pushing {image_uri}...")
        push_cmd = ["docker", "push", image_uri]

        push_result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=600)

        if push_result.returncode != 0:
            raise Exception(f"Docker push failed: {push_result.stderr}")

        print(f"   Push completed")

    def _deploy_to_eks(
        self,
        model_name: str,
        model_version: str,
        image_uri: str,
        deployment_id: str,
        tags: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Deploy model to OVH EKS cluster."""

        # Create Kubernetes manifests
        deployment_manifest = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {model_name}-inference
  namespace: {self.k8s_namespace}
  labels:
    app: {model_name}-inference
    model: {model_name}
    version: v{model_version}
    deployment-id: {deployment_id}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {model_name}-inference
  template:
    metadata:
      labels:
        app: {model_name}-inference
        model: {model_name}
        version: v{model_version}
    spec:
      containers:
      - name: inference
        image: {image_uri}
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: MLFLOW_TRACKING_URI
          value: "http://mlflow-service.asgard.svc.cluster.local:5000"
        - name: MODEL_NAME
          value: "{model_name}"
        - name: MODEL_VERSION
          value: "{model_version}"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {model_name}-inference
  namespace: {self.k8s_namespace}
  labels:
    app: {model_name}-inference
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
  selector:
    app: {model_name}-inference
"""

        # Apply manifests
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(deployment_manifest)
            manifest_path = f.name

        try:
            print(f"   Applying Kubernetes manifests...")
            kubectl_cmd = ["kubectl", "apply", "-f", manifest_path]

            result = subprocess.run(kubectl_cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                raise Exception(f"kubectl apply failed: {result.stderr}")

            print(f"   {result.stdout}")

            # Wait for rollout
            print(f"   Waiting for deployment rollout...")
            rollout_cmd = [
                "kubectl",
                "rollout",
                "status",
                f"deployment/{model_name}-inference",
                "-n",
                self.k8s_namespace,
                "--timeout=5m",
            ]

            rollout_result = subprocess.run(
                rollout_cmd, capture_output=True, text=True, timeout=320
            )

            if rollout_result.returncode == 0:
                print(f"   ✅ Deployment rolled out successfully")
            else:
                print(f"   ⚠️  Rollout status: {rollout_result.stderr}")

            # Get service endpoint
            svc_cmd = [
                "kubectl",
                "get",
                "svc",
                f"{model_name}-inference",
                "-n",
                self.k8s_namespace,
                "-o",
                "jsonpath={.spec.clusterIP}",
            ]

            svc_result = subprocess.run(svc_cmd, capture_output=True, text=True, timeout=10)

            cluster_ip = svc_result.stdout.strip() if svc_result.returncode == 0 else "N/A"

            return {
                "deployment_name": f"{model_name}-inference",
                "service_name": f"{model_name}-inference",
                "namespace": self.k8s_namespace,
                "cluster_ip": cluster_ip,
                "endpoint": f"http://{model_name}-inference.{self.k8s_namespace}.svc.cluster.local",
                "replicas": 2,
            }

        finally:
            # Clean up temp file
            Path(manifest_path).unlink(missing_ok=True)


# Integration hook for MLOps service
def post_training_hook(
    model_name: str, model_version: str, run_id: str, tags: Dict[str, str] = None
):
    """
    Hook to be called after training completes.

    This should be integrated into the MLOps service _execute_training_script method.
    """
    deployment_service = ModelDeploymentService()
    result = deployment_service.deploy_model_after_training(
        model_name=model_name, model_version=model_version, run_id=run_id, tags=tags
    )
    return result
