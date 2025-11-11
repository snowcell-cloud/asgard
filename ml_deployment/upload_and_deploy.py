#!/usr/bin/env python3
"""
Example: Upload Training Script to MLOps API

This demonstrates the complete workflow:
1. Upload training script via /mlops/training/upload
2. Script trains model with Feast features
3. Model is automatically registered to MLflow
4. Docker image is automatically built
5. Image is pushed to ECR: 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model
6. Model is deployed to OVH EKS in asgard namespace
7. Inference endpoint becomes available

Usage:
    python3 upload_and_deploy.py

Prerequisites:
    - MLOps API accessible at http://localhost:8000
    - AWS credentials configured
    - kubectl configured for OVH EKS
"""

import base64
import time
import requests
from pathlib import Path


def upload_training_script(
    script_path: str,
    model_name: str = "churn_predictor_feast",
    experiment_name: str = "feast_deployment_demo",
    use_feast: bool = False,
):
    """Upload training script to MLOps API."""

    print("=" * 80)
    print("UPLOADING TRAINING SCRIPT TO MLOPS API")
    print("=" * 80)

    # Read and encode script
    script_file = Path(script_path)
    if not script_file.exists():
        print(f"❌ Script not found: {script_path}")
        return None

    with open(script_file, "rb") as f:
        script_content = base64.b64encode(f.read()).decode("utf-8")

    # Prepare request payload
    payload = {
        "script_name": script_file.name,
        "script_content": script_content,
        "experiment_name": experiment_name,
        "model_name": model_name,
        "requirements": ["feast==0.38.0", "scikit-learn==1.3.2", "pandas==2.1.3", "numpy==1.26.2"],
        "environment_vars": {
            "FEAST_REPO_PATH": "/tmp/feast_repo",
            "MODEL_NAME": model_name,
            "USE_FEAST": "true" if use_feast else "false",
            "FEATURE_VIEW_NAME": "customer_churn_features",
        },
        "timeout": 600,
        "tags": {
            "version": "1.0",
            "deployment": "automated",
            "target_cluster": "ovh-eks",
            "target_namespace": "asgard",
            "ecr_repo": "637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model",
        },
    }

    print(f"\n📤 Uploading script: {script_file.name}")
    print(f"   Model name: {model_name}")
    print(f"   Experiment: {experiment_name}")
    print(f"   Use Feast: {use_feast}")

    # Send request
    try:
        response = requests.post(
            "http://localhost:8000/mlops/training/upload", json=payload, timeout=30
        )

        if response.status_code == 202:
            job = response.json()
            print(f"\n✅ Upload successful!")
            print(f"   Job ID: {job['job_id']}")
            print(f"   Status: {job['status']}")
            return job["job_id"]
        else:
            print(f"\n❌ Upload failed: {response.status_code}")
            print(f"   {response.text}")
            return None

    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        return None


def monitor_training_job(job_id: str):
    """Monitor training job progress."""

    print("\n" + "=" * 80)
    print(f"MONITORING TRAINING JOB: {job_id}")
    print("=" * 80)

    start_time = time.time()
    last_status = None

    while True:
        try:
            response = requests.get(
                f"http://localhost:8000/mlops/training/jobs/{job_id}", timeout=10
            )

            if response.status_code == 200:
                status = response.json()

                # Print status updates
                if status["status"] != last_status:
                    print(f"\n📊 Status: {status['status']}")
                    last_status = status["status"]

                duration = status.get("duration_seconds", 0) or 0
                print(f"   Duration: {duration:.1f}s", end="\r")

                # Check if job is complete
                if status["status"] in ["completed", "failed"]:
                    print()  # New line

                    if status["status"] == "completed":
                        print(f"\n✅ Training completed successfully!")
                        print(f"   Run ID: {status.get('run_id', 'N/A')}")
                        print(f"   Model: {status.get('model_name', 'N/A')}")
                        print(f"   Version: {status.get('model_version', 'N/A')}")

                        # Check deployment info
                        deployment_info = status.get("deployment_info")
                        if deployment_info:
                            print(f"\n🚀 Automated Deployment:")
                            print(f"   Status: {deployment_info.get('status', 'N/A')}")
                            print(f"   Image: {deployment_info.get('image_uri', 'N/A')}")
                            print(f"   Namespace: {deployment_info.get('namespace', 'N/A')}")

                            if deployment_info.get("deployment_info"):
                                dep = deployment_info["deployment_info"]
                                print(f"   Endpoint: {dep.get('endpoint', 'N/A')}")
                                print(f"   Cluster IP: {dep.get('cluster_ip', 'N/A')}")

                        # Print logs
                        if status.get("logs"):
                            print(f"\n📋 Training Logs:")
                            print("-" * 80)
                            # Print last 50 lines
                            logs = status["logs"].split("\n")
                            for line in logs[-50:]:
                                print(f"   {line}")

                        return status
                    else:
                        print(f"\n❌ Training failed!")
                        error = status.get("error", "Unknown error")
                        print(f"   Error: {error}")

                        if status.get("logs"):
                            print(f"\n📋 Logs:")
                            print("-" * 80)
                            print(status["logs"])

                        return None

                time.sleep(5)

            else:
                print(f"\n❌ Failed to get status: {response.status_code}")
                return None

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Monitoring interrupted by user")
            print(f"   Job is still running. Check status with:")
            print(f"   curl http://localhost:8000/mlops/training/jobs/{job_id}")
            return None
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(5)


def test_inference_endpoint(model_name: str, namespace: str = "asgard"):
    """Test the deployed inference endpoint."""

    print("\n" + "=" * 80)
    print(f"TESTING INFERENCE ENDPOINT")
    print("=" * 80)

    # Construct endpoint URL (internal cluster URL)
    endpoint = f"http://{model_name}-inference.{namespace}.svc.cluster.local/predict"

    print(f"\n📍 Endpoint: {endpoint}")
    print(f"\nℹ️  To test from outside cluster, use port-forward:")
    print(f"   kubectl port-forward -n {namespace} svc/{model_name}-inference 8080:80")
    print(f"   Then access: http://localhost:8080/predict")

    # Example prediction payload
    payload = {
        "inputs": {
            "total_purchases": [10, 25, 5, 40],
            "avg_purchase_value": [50.0, 120.5, 30.0, 200.0],
            "days_since_last_purchase": [5, 15, 200, 10],
            "customer_lifetime_value": [500.0, 3000.0, 150.0, 8000.0],
            "account_age_days": [365, 730, 180, 1095],
            "support_tickets_count": [2, 1, 8, 0],
        },
        "return_probabilities": True,
    }

    print(f"\n📦 Example prediction request:")
    print(f"   curl -X POST {endpoint} \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{payload}'")


def main():
    """Main workflow."""

    print("\n" + "=" * 80)
    print("ML MODEL TRAINING & DEPLOYMENT WORKFLOW")
    print("=" * 80)
    print("\nThis will:")
    print("  1. Upload training script to /mlops/training/upload")
    print("  2. Train model with Feast features (or synthetic data)")
    print("  3. Register model to MLflow")
    print("  4. Build Docker image")
    print("  5. Push to ECR: 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model")
    print("  6. Deploy to OVH EKS (asgard namespace)")
    print("  7. Create inference endpoint")
    print()

    # Configuration
    script_path = "ml_deployment/train_with_feast.py"
    model_name = "churn_predictor_feast"
    experiment_name = "feast_deployment_demo"
    use_feast = False  # Set to True to use actual Feast features

    # Step 1: Upload training script
    job_id = upload_training_script(
        script_path=script_path,
        model_name=model_name,
        experiment_name=experiment_name,
        use_feast=use_feast,
    )

    if not job_id:
        print("\n❌ Upload failed. Exiting.")
        return

    # Step 2: Monitor training
    result = monitor_training_job(job_id)

    if not result:
        print("\n❌ Training failed. Exiting.")
        return

    # Step 3: Show inference endpoint info
    test_inference_endpoint(model_name)

    print("\n" + "=" * 80)
    print("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\nYour model is now deployed and ready for inference!")
    print(f"\nTo verify deployment:")
    print(f"  kubectl get all -n asgard -l app={model_name}-inference")
    print(f"\nTo access inference API:")
    print(f"  kubectl port-forward -n asgard svc/{model_name}-inference 8080:80")
    print(f"  curl http://localhost:8080/health")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Workflow interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Workflow failed: {e}")
        import traceback

        traceback.print_exc()
