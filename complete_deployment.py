#!/usr/bin/env python3
"""
Complete deployment workflow:
1. Train model via API
2. Build Docker image
3. Push to ECR (optimized)
4. Deploy to EKS with LoadBalancer
"""

import subprocess
import time
import json
import requests
import tempfile
import os
import base64
from pathlib import Path

API_BASE = "http://localhost:8000"
ECR_REGISTRY = "637423187518.dkr.ecr.eu-north-1.amazonaws.com"
ECR_REPO = "asgard-model"
AWS_REGION = "eu-north-1"
NAMESPACE = "asgard"


def train_model(model_name: str, experiment_name: str):
    """Step 1: Train model via API."""
    print("=" * 80)
    print("STEP 1: TRAIN MODEL")
    print("=" * 80)

    # Read training script
    script_path = Path("ml_deployment/train_with_feast.py")
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return None

    with open(script_path, "rb") as f:
        script_content = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "script_name": "train_with_feast.py",
        "script_content": script_content,
        "experiment_name": experiment_name,
        "model_name": model_name,
        "requirements": ["scikit-learn", "pandas", "numpy"],
        "environment_vars": {
            "USE_FEAST": "false",
            "MODEL_NAME": model_name,
            "EXPERIMENT_NAME": experiment_name,
        },
        "timeout": 300,
        "tags": {"deployment": "automated", "version": "1.0"},
    }

    print(f"📤 Uploading training script...")
    print(f"   Model: {model_name}")
    print(f"   Experiment: {experiment_name}")

    try:
        response = requests.post(f"{API_BASE}/mlops/training/upload", json=payload, timeout=30)

        if response.status_code != 202:
            print(f"❌ Upload failed: {response.status_code}")
            return None

        job = response.json()
        job_id = job["job_id"]
        print(f"✅ Upload successful! Job ID: {job_id}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

    # Monitor training
    print(f"\n⏳ Monitoring training...")
    max_wait = 300
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE}/mlops/training/jobs/{job_id}", timeout=10)

            if response.status_code == 200:
                status = response.json()
                current_status = status["status"]
                duration = status.get("duration_seconds", 0) or 0

                print(f"   Status: {current_status} | Duration: {duration:.1f}s", end="\r")

                if current_status in ["completed", "failed"]:
                    print()

                    if current_status == "completed":
                        run_id = status.get("run_id")
                        print(f"✅ Training completed!")
                        print(f"   Run ID: {run_id}")

                        # Get model version from MLflow
                        try:
                            model_response = requests.get(
                                f"{API_BASE}/mlops/models/{model_name}", timeout=10
                            )
                            if model_response.status_code == 200:
                                model_info = model_response.json()
                                latest_version = model_info["latest_versions"][0]["version"]
                                print(f"   Model Version: {latest_version}")
                                return {
                                    "model_name": model_name,
                                    "version": latest_version,
                                    "run_id": run_id,
                                }
                        except:
                            pass

                        return {"model_name": model_name, "version": "1", "run_id": run_id}
                    else:
                        print(f"❌ Training failed!")
                        return None

                time.sleep(5)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(5)

    print(f"\n⚠️ Timeout")
    return None


def build_docker_image(model_name: str, model_version: str, run_id: str):
    """Step 2: Build optimized Docker image."""
    print("\n" + "=" * 80)
    print("STEP 2: BUILD DOCKER IMAGE")
    print("=" * 80)

    image_tag = f"{model_name.replace('_', '-')}-v{model_version}"
    image_uri = f"{ECR_REGISTRY}/{ECR_REPO}:{image_tag}"

    print(f"🐳 Building Docker image...")
    print(f"   Image: {image_uri}")

    # Create optimized Dockerfile with multi-stage build
    dockerfile_content = f"""# Multi-stage build for smaller image
FROM python:3.11-slim as builder

# Install build dependencies
RUN pip install --no-cache-dir --user \\
    mlflow==2.16.2 \\
    fastapi==0.104.1 \\
    uvicorn[standard]==0.24.0 \\
    scikit-learn==1.3.2 \\
    pandas==2.1.3 \\
    numpy==1.26.2 \\
    boto3==1.34.0 \\
    python-multipart==0.0.6

FROM python:3.11-slim

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set PATH
ENV PATH=/root/.local/bin:$PATH

# Set working directory
WORKDIR /app

# Environment variables
ENV MLFLOW_TRACKING_URI=http://mlflow-service.asgard.svc.cluster.local:5000
ENV MODEL_NAME={model_name}
ENV MODEL_VERSION={model_version}
ENV RUN_ID={run_id}
ENV AWS_DEFAULT_REGION={AWS_REGION}

# Create inference service
COPY inference_service.py /app/

# Expose port
EXPOSE 80

# Run the service
CMD ["uvicorn", "inference_service:app", "--host", "0.0.0.0", "--port", "80"]
"""

    # Create minimal inference service
    inference_service = f'''import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow.pyfunc
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Model Inference API",
    description="MLflow Model Serving with FastAPI",
    version="1.0.0"
)

# Global model variable
model = None
model_info = {{
    "name": os.getenv("MODEL_NAME", "unknown"),
    "version": os.getenv("MODEL_VERSION", "unknown"),
    "run_id": os.getenv("RUN_ID", "unknown")
}}

class PredictionRequest(BaseModel):
    inputs: Dict[str, List[Any]]
    return_probabilities: Optional[bool] = False

class PredictionResponse(BaseModel):
    predictions: List[int]
    probabilities: Optional[List[List[float]]] = None
    model_name: str
    model_version: str

@app.on_event("startup")
async def load_model():
    """Load model on startup."""
    global model
    try:
        model_uri = f"models:/{{model_info['name']}}/{{model_info['version']}}"
        logger.info(f"Loading model from: {{model_uri}}")
        model = mlflow.pyfunc.load_model(model_uri)
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {{e}}")
        # Don't fail startup, allow health checks to work
        model = None

@app.get("/health")
def health():
    """Health check endpoint."""
    return {{
        "status": "healthy" if model else "model_not_loaded",
        "model": model_info
    }}

@app.get("/metadata")
def metadata():
    """Model metadata endpoint."""
    return {{
        "model_name": model_info["name"],
        "model_version": model_info["version"],
        "run_id": model_info["run_id"],
        "mlflow_uri": os.getenv("MLFLOW_TRACKING_URI"),
        "model_loaded": model is not None
    }}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    """Prediction endpoint."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        import pandas as pd
        
        # Convert inputs to DataFrame
        input_df = pd.DataFrame(request.inputs)
        
        # Get predictions
        predictions = model.predict(input_df)
        
        response = {{
            "predictions": predictions.tolist(),
            "model_name": model_info["name"],
            "model_version": model_info["version"]
        }}
        
        # Get probabilities if requested and model supports it
        if request.return_probabilities:
            try:
                probabilities = model.predict_proba(input_df)
                response["probabilities"] = probabilities.tolist()
            except:
                pass
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    """Root endpoint."""
    return {{
        "message": "Model Inference API",
        "endpoints": ["/health", "/metadata", "/predict"],
        "model": model_info
    }}
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write Dockerfile
        dockerfile_path = os.path.join(tmpdir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Write inference service
        service_path = os.path.join(tmpdir, "inference_service.py")
        with open(service_path, "w") as f:
            f.write(inference_service)

        # Build image
        try:
            result = subprocess.run(
                ["docker", "build", "-t", image_uri, "-f", dockerfile_path, tmpdir],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print(f"✅ Image built successfully")
                return image_uri
            else:
                print(f"❌ Build failed:")
                print(result.stderr)
                return None
        except Exception as e:
            print(f"❌ Build error: {e}")
            return None


def push_to_ecr(image_uri: str):
    """Step 3: Push image to ECR with optimizations."""
    print("\n" + "=" * 80)
    print("STEP 3: PUSH TO ECR")
    print("=" * 80)

    print(f"🔐 Logging in to ECR...")

    try:
        # ECR login
        login_result = subprocess.run(
            ["aws", "ecr", "get-login-password", "--region", AWS_REGION],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if login_result.returncode == 0:
            subprocess.run(
                ["docker", "login", "--username", "AWS", "--password-stdin", ECR_REGISTRY],
                input=login_result.stdout,
                text=True,
                check=True,
                timeout=30,
            )
            print(f"✅ ECR login successful")
        else:
            print(f"❌ ECR login failed")
            return False
    except Exception as e:
        print(f"❌ ECR login error: {e}")
        return False

    # Push image
    print(f"\n☁️  Pushing image to ECR...")
    print(f"   This may take several minutes for large images...")

    try:
        # Use subprocess.Popen to show progress
        process = subprocess.Popen(
            ["docker", "push", image_uri],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Show progress
        for line in process.stdout:
            if "Pushed" in line or "Layer already exists" in line:
                print(f"   {line.strip()}")

        process.wait(timeout=900)  # 15 minutes timeout

        if process.returncode == 0:
            print(f"✅ Image pushed successfully")
            return True
        else:
            print(f"❌ Push failed")
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ Push timeout after 15 minutes")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ Push error: {e}")
        return False


def deploy_to_eks(model_name: str, model_version: str, image_uri: str):
    """Step 4: Deploy to EKS with LoadBalancer."""
    print("\n" + "=" * 80)
    print("STEP 4: DEPLOY TO EKS")
    print("=" * 80)

    safe_model_name = model_name.replace("_", "-").lower()
    deployment_name = f"{safe_model_name}-inference"
    service_name = f"{safe_model_name}-service"

    # Create AWS credentials secret
    print(f"🔑 Creating AWS credentials secret...")

    secret_yaml = f"""apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: {NAMESPACE}
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "************"
  AWS_SECRET_ACCESS_KEY: "************"
  AWS_DEFAULT_REGION: "****"
"""

    # Create deployment YAML
    deployment_yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {deployment_name}
  namespace: {NAMESPACE}
  labels:
    app: {deployment_name}
    model: {safe_model_name}
    version: "v{model_version}"
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {deployment_name}
  template:
    metadata:
      labels:
        app: {deployment_name}
        model: {safe_model_name}
    spec:
      containers:
      - name: inference
        image: {image_uri}
        imagePullPolicy: Always
        ports:
        - containerPort: 80
          protocol: TCP
        envFrom:
        - secretRef:
            name: aws-credentials
        env:
        - name: MODEL_NAME
          value: "{model_name}"
        - name: MODEL_VERSION
          value: "{model_version}"
        - name: MLFLOW_TRACKING_URI
          value: "http://mlflow-service.{NAMESPACE}.svc.cluster.local:5000"
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
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  namespace: {NAMESPACE}
  labels:
    app: {deployment_name}
spec:
  type: LoadBalancer
  selector:
    app: {deployment_name}
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
    name: http
"""

    print(f"☸️  Deploying to Kubernetes...")
    print(f"   Namespace: {NAMESPACE}")
    print(f"   Deployment: {deployment_name}")
    print(f"   Service: {service_name} (LoadBalancer)")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(secret_yaml + "---\n" + deployment_yaml)
        yaml_file = f.name

    try:
        # Apply manifests
        result = subprocess.run(
            ["kubectl", "apply", "-f", yaml_file], capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"✅ Deployment applied successfully")
            print(result.stdout)
        else:
            print(f"❌ Deployment failed")
            print(result.stderr)
            return None

        # Wait for LoadBalancer IP
        print(f"\n⏳ Waiting for LoadBalancer external IP...")

        for i in range(60):  # Wait up to 10 minutes
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "svc",
                    service_name,
                    "-n",
                    NAMESPACE,
                    "-o",
                    "jsonpath={.status.loadBalancer.ingress[0].ip}",
                ],
                capture_output=True,
                text=True,
            )

            external_ip = result.stdout.strip()
            if external_ip:
                print(f"✅ External IP assigned: {external_ip}")

                # Show deployment status
                print(f"\n📊 Deployment Status:")
                subprocess.run(["kubectl", "get", "deployment", deployment_name, "-n", NAMESPACE])
                subprocess.run(
                    ["kubectl", "get", "pods", "-n", NAMESPACE, "-l", f"app={deployment_name}"]
                )
                subprocess.run(["kubectl", "get", "svc", service_name, "-n", NAMESPACE])

                return {
                    "deployment_name": deployment_name,
                    "service_name": service_name,
                    "external_ip": external_ip,
                    "endpoint": f"http://{external_ip}",
                }

            print(f"   Waiting... ({i+1}/60)", end="\r")
            time.sleep(10)

        print(f"\n⚠️  Timeout waiting for external IP")
        print(f"   Check status with: kubectl get svc {service_name} -n {NAMESPACE}")
        return None

    finally:
        try:
            os.unlink(yaml_file)
        except:
            pass


def test_endpoint(endpoint: str, model_name: str):
    """Step 5: Test the deployed endpoint."""
    print("\n" + "=" * 80)
    print("STEP 5: TEST ENDPOINT")
    print("=" * 80)

    print(f"🧪 Testing endpoint: {endpoint}")

    # Wait a bit for pods to be ready
    print(f"⏳ Waiting 30s for pods to be ready...")
    time.sleep(30)

    # Test health
    print(f"\n📡 Testing /health...")
    try:
        response = requests.get(f"{endpoint}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ Health check passed:")
            print(f"   {json.dumps(response.json(), indent=2)}")
        else:
            print(f"⚠️  Health check status: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Health check error: {e}")

    # Test metadata
    print(f"\n📡 Testing /metadata...")
    try:
        response = requests.get(f"{endpoint}/metadata", timeout=10)
        if response.status_code == 200:
            print(f"✅ Metadata retrieved:")
            print(f"   {json.dumps(response.json(), indent=2)}")
        else:
            print(f"⚠️  Metadata status: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Metadata error: {e}")

    # Test prediction
    print(f"\n📡 Testing /predict...")
    payload = {
        "inputs": {
            "total_purchases": [10, 25, 5],
            "avg_purchase_value": [50.0, 120.5, 30.0],
            "days_since_last_purchase": [5, 15, 200],
            "customer_lifetime_value": [500.0, 3000.0, 150.0],
            "account_age_days": [365, 730, 180],
            "support_tickets_count": [2, 1, 8],
        },
        "return_probabilities": True,
    }

    try:
        response = requests.post(f"{endpoint}/predict", json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Prediction successful:")
            print(f"   Predictions: {result.get('predictions', [])}")

            if result.get("probabilities"):
                print(f"\n   Customer Risk Analysis:")
                for i, (pred, prob) in enumerate(
                    zip(result["predictions"], result["probabilities"]), 1
                ):
                    risk = "HIGH" if pred == 1 else "LOW"
                    confidence = prob[1] if pred == 1 else prob[0]
                    print(f"   Customer {i}: {risk} risk ({confidence*100:.1f}% confidence)")
        else:
            print(f"⚠️  Prediction failed: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"⚠️  Prediction error: {e}")


def main():
    """Run complete deployment workflow."""
    print("\n" + "=" * 80)
    print("COMPLETE ML DEPLOYMENT WORKFLOW")
    print("Train → Build → Push to ECR → Deploy to EKS")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    model_name = "production_model"
    experiment_name = "production_experiment"

    # Step 1: Train model
    model_info = train_model(model_name, experiment_name)
    if not model_info:
        print("\n❌ Training failed")
        return

    # Step 2: Build Docker image
    image_uri = build_docker_image(
        model_info["model_name"], model_info["version"], model_info["run_id"]
    )
    if not image_uri:
        print("\n❌ Image build failed")
        return

    # Step 3: Push to ECR
    if not push_to_ecr(image_uri):
        print("\n❌ ECR push failed")
        return

    # Step 4: Deploy to EKS
    deployment_info = deploy_to_eks(model_info["model_name"], model_info["version"], image_uri)
    if not deployment_info:
        print("\n❌ Deployment failed")
        return

    # Step 5: Test endpoint
    test_endpoint(deployment_info["endpoint"], model_info["model_name"])

    # Final summary
    print("\n" + "=" * 80)
    print("✅ DEPLOYMENT COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"\nModel Details:")
    print(f"  Name: {model_info['model_name']}")
    print(f"  Version: {model_info['version']}")
    print(f"  Run ID: {model_info['run_id']}")
    print(f"\nDeployment Details:")
    print(f"  Image: {image_uri}")
    print(f"  Deployment: {deployment_info['deployment_name']}")
    print(f"  Service: {deployment_info['service_name']}")
    print(f"  External IP: {deployment_info['external_ip']}")
    print(f"\nEndpoints:")
    print(f"  Health: {deployment_info['endpoint']}/health")
    print(f"  Metadata: {deployment_info['endpoint']}/metadata")
    print(f"  Predict: {deployment_info['endpoint']}/predict")
    print(f"\nExample curl command:")
    print(
        f"""  curl -X POST {deployment_info['endpoint']}/predict \\
    -H "Content-Type: application/json" \\
    -d '{{"inputs": {{"total_purchases": [10], "avg_purchase_value": [50.0], "days_since_last_purchase": [5], "customer_lifetime_value": [500.0], "account_age_days": [365], "support_tickets_count": [2]}}}}'"""
    )
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Deployment failed: {e}")
        import traceback

        traceback.print_exc()
