#!/usr/bin/env python3
"""
Simplified deployment script that creates an inference service in K8s
that pulls the model directly from MLflow (no Docker build/push needed).
"""

import subprocess
import time


def deploy_mlflow_model_to_k8s(model_name: str, model_version: str):
    """
    Deploy a model from MLflow Model Registry to Kubernetes.
    Uses MLflow's built-in model serving without custom Docker images.
    """

    print(f"=" * 80)
    print(f"SIMPLIFIED MODEL DEPLOYMENT (MLflow Native)")
    print(f"=" * 80)
    print(f"Model: {model_name}")
    print(f"Version: {model_version}")
    print(f"=" * 80)
    print()

    namespace = "asgard"
    # K8s names must be lowercase and can't contain underscores
    safe_model_name = model_name.replace("_", "-").lower()
    deployment_name = f"{safe_model_name}-inference"
    service_name = f"{safe_model_name}-inference"
    mlflow_uri = f"http://mlflow-service.{namespace}.svc.cluster.local:5000"

    # Create deployment YAML for MLflow model serving
    deployment_yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {deployment_name}
  namespace: {namespace}
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
      - name: mlflow-server
        image: python:3.11-slim
        command:
          - /bin/bash
          - -c
          - |
            pip install --no-cache-dir mlflow==2.16.2 scikit-learn==1.3.2 pandas numpy boto3 &&
            mlflow models serve -m "models:/{model_name}/{model_version}" -h 0.0.0.0 -p 8080 --no-conda
        ports:
        - containerPort: 8080
          protocol: TCP
        env:
        - name: MLFLOW_TRACKING_URI
          value: "{mlflow_uri}"
        - name: MODEL_NAME
          value: "{model_name}"
        - name: MODEL_VERSION
          value: "{model_version}"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        readinessProbe:
          httpGet:
            path: /ping
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        livenessProbe:
          httpGet:
            path: /ping
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  namespace: {namespace}
  labels:
    app: {deployment_name}
spec:
  type: ClusterIP
  selector:
    app: {deployment_name}
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
"""

    print(f"📝 Step 1: Creating Kubernetes manifests...")

    # Write YAML to temporary file
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(deployment_yaml)
        yaml_file = f.name

    print(f"✅ Manifests created")

    try:
        # Step 2: Apply deployment
        print(f"\n☸️  Step 2: Deploying to Kubernetes...")
        print(f"   Namespace: {namespace}")
        print(f"   Deployment: {deployment_name}")
        print(f"   Service: {service_name}")

        result = subprocess.run(
            ["kubectl", "apply", "-f", yaml_file], capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"✅ Deployment applied successfully")
            print(result.stdout)
        else:
            print(f"❌ Deployment failed: {result.stderr}")
            return False

        # Step 3: Wait for deployment
        print(f"\n⏳ Step 3: Waiting for deployment to be ready...")

        for i in range(24):  # Wait up to 4 minutes
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "deployment",
                    deployment_name,
                    "-n",
                    namespace,
                    "-o",
                    "jsonpath={.status.availableReplicas}",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip() == "1":
                print(f"✅ Deployment is ready!")
                break

            print(f"   Waiting... ({i+1}/24) - Installing dependencies and loading model...")
            time.sleep(10)
        else:
            print(f"⚠️ Deployment may still be starting, check status manually")

        # Step 4: Show status
        print(f"\n📊 Step 4: Deployment Status")
        print(f"-" * 80)

        result = subprocess.run(
            ["kubectl", "get", "deployment", deployment_name, "-n", namespace],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(result.stdout)

        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-l", f"app={deployment_name}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(result.stdout)

        result = subprocess.run(
            ["kubectl", "get", "svc", service_name, "-n", namespace], capture_output=True, text=True
        )
        if result.returncode == 0:
            print(result.stdout)

        # Step 5: Instructions
        print(f"\n" + "=" * 80)
        print(f"✅ DEPLOYMENT COMPLETED")
        print(f"=" * 80)
        print(f"\nModel: {model_name} v{model_version}")
        print(f"Namespace: {namespace}")
        print(f"Service: {service_name}")
        print(f"\nTo test the inference endpoint:")
        print(f"  kubectl port-forward -n {namespace} svc/{service_name} 8080:80")
        print(f"\nThen in another terminal:")
        print(f"  # Health check")
        print(f"  curl http://localhost:8080/ping")
        print(f"\n  # Prediction")
        print(f"  curl -X POST http://localhost:8080/invocations \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"inputs\": [[10, 50, 5, 500, 365, 2]]}}'")
        print(f"\n" + "=" * 80)

        return True

    finally:
        # Cleanup temp file
        try:
            os.unlink(yaml_file)
        except:
            pass


if __name__ == "__main__":
    import sys

    # Use latest version of test_model_feast
    model_name = "test_model_feast"
    model_version = "3"  # Latest version from our tests

    if len(sys.argv) > 1:
        model_name = sys.argv[1]
    if len(sys.argv) > 2:
        model_version = sys.argv[2]

    print(f"\nDeploying model: {model_name} version {model_version}\n")

    success = deploy_mlflow_model_to_k8s(model_name, model_version)

    if not success:
        print("\n❌ Deployment failed!")
        sys.exit(1)

    print("\n✅ Deployment successful!")
