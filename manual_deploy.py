#!/usr/bin/env python3
"""
Manually deploy a trained model that is already registered in MLflow.
"""

import subprocess
import tempfile
import os
import json
import time


def build_and_deploy_model(model_name: str, model_version: str, run_id: str):
    """Build Docker image and deploy to EKS."""

    print(f"=" * 80)
    print(f"MANUAL MODEL DEPLOYMENT")
    print(f"=" * 80)
    print(f"Model: {model_name}")
    print(f"Version: {model_version}")
    print(f"Run ID: {run_id}")
    print(f"=" * 80)

    # Configuration
    ECR_REGISTRY = "637423187518.dkr.ecr.eu-north-1.amazonaws.com"
    ECR_REPO = "asgard-model"
    AWS_REGION = "eu-north-1"
    NAMESPACE = "asgard"

    image_tag = f"{model_name}-v{model_version}"
    image_uri = f"{ECR_REGISTRY}/{ECR_REPO}:{image_tag}"

    # Step 1: Create Dockerfile
    print(f"\n📝 Step 1: Creating Dockerfile...")

    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_path = os.path.join(tmpdir, "Dockerfile")

        dockerfile_content = f"""
# Multi-stage build for model inference service
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \\
    mlflow==2.16.2 \\
    fastapi==0.104.1 \\
    uvicorn[standard]==0.24.0 \\
    scikit-learn==1.3.2 \\
    pandas==2.1.3 \\
    numpy==1.26.2 \\
    python-multipart==0.0.6

# Set MLflow environment
ENV MLFLOW_TRACKING_URI=http://mlflow-service.asgard.svc.cluster.local:5000
ENV MODEL_NAME={model_name}
ENV MODEL_VERSION={model_version}
ENV RUN_ID={run_id}

# Copy inference service (will be created inline)
COPY inference_service.py /app/

# Expose port
EXPOSE 80

# Run the service
CMD ["uvicorn", "inference_service:app", "--host", "0.0.0.0", "--port", "80"]
"""

        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        print(f"✅ Dockerfile created")

        # Step 2: Create inference service
        print(f"\n📝 Step 2: Creating inference service...")

        inference_service_path = os.path.join(tmpdir, "inference_service.py")

        # Read the inference service template
        template_path = "ml_deployment/inference_service.py"
        if os.path.exists(template_path):
            with open(template_path, "r") as f:
                inference_code = f.read()

            with open(inference_service_path, "w") as f:
                f.write(inference_code)

            print(f"✅ Inference service created")
        else:
            print(f"⚠️  Template not found, creating minimal service...")
            # Minimal inference service
            minimal_service = """
import os
from fastapi import FastAPI
import mlflow

app = FastAPI(title="Model Inference API")

MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_VERSION = os.getenv("MODEL_VERSION")

@app.get("/health")
def health():
    return {"status": "healthy", "model": MODEL_NAME, "version": MODEL_VERSION}

@app.get("/metadata")
def metadata():
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "mlflow_uri": os.getenv("MLFLOW_TRACKING_URI")
    }
"""
            with open(inference_service_path, "w") as f:
                f.write(minimal_service)
            print(f"✅ Minimal inference service created")

        # Step 3: Build Docker image
        print(f"\n🐳 Step 3: Building Docker image...")
        print(f"   Image: {image_uri}")

        try:
            result = subprocess.run(
                ["docker", "build", "-t", image_uri, "-f", dockerfile_path, tmpdir],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print(f"✅ Image built successfully")
            else:
                print(f"❌ Build failed:")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ Build error: {e}")
            return False

        # Step 4: Push to ECR
        print(f"\n☁️  Step 4: Pushing to ECR...")

        # ECR login
        print(f"   Logging in to ECR...")
        try:
            login_result = subprocess.run(
                ["aws", "ecr", "get-login-password", "--region", AWS_REGION],
                capture_output=True,
                text=True,
            )

            if login_result.returncode == 0:
                subprocess.run(
                    ["docker", "login", "--username", "AWS", "--password-stdin", ECR_REGISTRY],
                    input=login_result.stdout,
                    text=True,
                    check=True,
                )
                print(f"   ✅ ECR login successful")
            else:
                print(f"   ❌ ECR login failed: {login_result.stderr}")
                return False
        except Exception as e:
            print(f"   ❌ ECR login error: {e}")
            return False

        # Push image
        print(f"   Pushing image...")
        try:
            push_result = subprocess.run(
                ["docker", "push", image_uri], capture_output=True, text=True, timeout=600
            )

            if push_result.returncode == 0:
                print(f"✅ Image pushed successfully")
            else:
                print(f"❌ Push failed: {push_result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Push error: {e}")
            return False

        # Step 5: Deploy to EKS
        print(f"\n☸️  Step 5: Deploying to EKS...")

        deployment_name = f"{model_name}-inference"
        service_name = f"{model_name}-inference"

        # Create deployment manifest
        deployment_yaml = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {deployment_name}
  namespace: {NAMESPACE}
  labels:
    app: {deployment_name}
    model: {model_name}
    version: "v{model_version}"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {deployment_name}
  template:
    metadata:
      labels:
        app: {deployment_name}
        model: {model_name}
    spec:
      containers:
      - name: inference
        image: {image_uri}
        ports:
        - containerPort: 80
          protocol: TCP
        env:
        - name: MODEL_NAME
          value: "{model_name}"
        - name: MODEL_VERSION
          value: "{model_version}"
        - name: RUN_ID
          value: "{run_id}"
        - name: MLFLOW_TRACKING_URI
          value: "http://mlflow-service.{NAMESPACE}.svc.cluster.local:5000"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  namespace: {NAMESPACE}
  labels:
    app: {deployment_name}
spec:
  type: ClusterIP
  selector:
    app: {deployment_name}
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
    name: http
"""

        deployment_file = os.path.join(tmpdir, "deployment.yaml")
        with open(deployment_file, "w") as f:
            f.write(deployment_yaml)

        # Apply deployment
        try:
            apply_result = subprocess.run(
                ["kubectl", "apply", "-f", deployment_file], capture_output=True, text=True
            )

            if apply_result.returncode == 0:
                print(f"✅ Deployment applied successfully")
                print(apply_result.stdout)
            else:
                print(f"❌ Deployment failed: {apply_result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            return False

    # Step 6: Wait for deployment
    print(f"\n⏳ Step 6: Waiting for deployment to be ready...")

    for i in range(12):  # Wait up to 2 minutes
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "deployment",
                    deployment_name,
                    "-n",
                    NAMESPACE,
                    "-o",
                    "jsonpath={.status.availableReplicas}",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip() == "1":
                print(f"✅ Deployment is ready!")
                break
        except:
            pass

        print(f"   Waiting... ({i+1}/12)")
        time.sleep(10)

    # Print final status
    print(f"\n" + "=" * 80)
    print(f"✅ DEPLOYMENT COMPLETED")
    print(f"=" * 80)
    print(f"Model: {model_name} v{model_version}")
    print(f"Image: {image_uri}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Deployment: {deployment_name}")
    print(f"Service: {service_name}")
    print(f"\nTo test the inference endpoint:")
    print(f"  kubectl port-forward -n {NAMESPACE} svc/{service_name} 8080:80")
    print(f"  curl http://localhost:8080/health")
    print(f"=" * 80)

    return True


if __name__ == "__main__":
    # Deploy the model
    success = build_and_deploy_model(
        model_name="test_model_feast", model_version="2", run_id="4f522d759c7442d2a9e877ecc6068a0a"
    )

    if not success:
        print("\n❌ Deployment failed!")
        exit(1)
