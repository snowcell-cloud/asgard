#!/usr/bin/env python3
"""
Example: Complete ML Deployment Workflow

This script demonstrates the entire workflow from training to deployment.
"""

import os
import sys
import time
import requests
from datetime import datetime


def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_training_api():
    """Test model training via MLOps API."""
    print_header("Step 1: Train Model via MLOps API")

    import base64

    # Read training script
    with open("ml_deployment/train_with_feast.py", "rb") as f:
        script_content = base64.b64encode(f.read()).decode("utf-8")

    # Upload training script
    payload = {
        "script_name": "train_with_feast.py",
        "script_content": script_content,
        "experiment_name": "feast_deployment_demo",
        "model_name": "churn_predictor_feast",
        "requirements": ["feast", "scikit-learn", "pandas", "numpy"],
        "environment_vars": {
            "FEAST_REPO_PATH": "/tmp/feast_repo",
            "MODEL_NAME": "churn_predictor_feast",
        },
        "timeout": 600,
        "tags": {"version": "1.0", "deployment": "demo"},
    }

    print("📤 Uploading training script...")
    response = requests.post("http://localhost:8000/mlops/training/upload", json=payload)

    if response.status_code == 202:
        job = response.json()
        job_id = job["job_id"]
        print(f"✅ Job submitted: {job_id}")

        # Monitor job status
        print("\n⏳ Monitoring training progress...")
        while True:
            status_response = requests.get(f"http://localhost:8000/mlops/training/jobs/{job_id}")
            status = status_response.json()

            print(
                f"   Status: {status['status']} (duration: {status.get('duration_seconds', 0):.1f}s)"
            )

            if status["status"] in ["completed", "failed"]:
                break

            time.sleep(5)

        if status["status"] == "completed":
            print(f"\n✅ Training completed!")
            print(f"   Run ID: {status['run_id']}")
            print(f"   Model: {status['model_name']}")
            print(f"   Version: {status['model_version']}")
            return status["model_name"], status["model_version"]
        else:
            print(f"\n❌ Training failed!")
            print(f"   Error: {status.get('error', 'Unknown')}")
            return None, None
    else:
        print(f"❌ Failed to submit job: {response.status_code}")
        print(response.text)
        return None, None


def test_inference_service(model_name, model_version):
    """Test inference service."""
    print_header("Step 2: Test Inference Service")

    # Wait for service to be ready
    print("⏳ Waiting for inference service...")
    for i in range(30):
        try:
            health_response = requests.get("http://localhost:8080/health")
            if health_response.status_code == 200:
                print("✅ Inference service is ready")
                print(f"   {health_response.json()}")
                break
        except requests.exceptions.ConnectionError:
            pass

        time.sleep(2)
        print(f"   Waiting... ({i+1}/30)")
    else:
        print("❌ Inference service not ready")
        return

    # Test metadata endpoint
    print("\n📊 Getting model metadata...")
    metadata_response = requests.get("http://localhost:8080/metadata")
    if metadata_response.status_code == 200:
        metadata = metadata_response.json()
        print(f"✅ Model loaded:")
        print(f"   Name: {metadata['model_name']}")
        print(f"   Version: {metadata['model_version']}")
        print(f"   Type: {metadata['model_type']}")
        print(f"   Features: {len(metadata['feature_names'])}")

    # Test prediction endpoint
    print("\n🔮 Making predictions...")
    predict_payload = {
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

    predict_response = requests.post("http://localhost:8080/predict", json=predict_payload)

    if predict_response.status_code == 200:
        result = predict_response.json()
        print(f"✅ Predictions successful!")
        print(f"   Predictions: {result['predictions']}")
        print(f"   Inference time: {result['inference_time_ms']:.2f}ms")

        print("\n   Customer Risk Analysis:")
        for i, (pred, prob) in enumerate(zip(result["predictions"], result["probabilities"]), 1):
            risk = "HIGH" if pred == 1 else "LOW"
            confidence = prob[1] if pred == 1 else prob[0]
            print(f"   Customer {i}: {risk} risk ({confidence*100:.1f}% confidence)")
    else:
        print(f"❌ Prediction failed: {predict_response.status_code}")
        print(predict_response.text)


def test_batch_inference():
    """Test batch inference endpoint."""
    print_header("Step 3: Test Batch Inference")

    batch_payload = {
        "instances": [
            {
                "total_purchases": 10,
                "avg_purchase_value": 50.0,
                "days_since_last_purchase": 5,
                "customer_lifetime_value": 500.0,
                "account_age_days": 365,
                "support_tickets_count": 2,
            },
            {
                "total_purchases": 5,
                "avg_purchase_value": 30.0,
                "days_since_last_purchase": 200,
                "customer_lifetime_value": 150.0,
                "account_age_days": 180,
                "support_tickets_count": 8,
            },
        ],
        "return_probabilities": True,
    }

    print("📦 Sending batch prediction request...")
    response = requests.post("http://localhost:8080/batch_predict", json=batch_payload)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Batch predictions successful!")
        print(f"   Predictions: {result['predictions']}")
        print(f"   Probabilities: {result['probabilities']}")
        print(f"   Inference time: {result['inference_time_ms']:.2f}ms")
    else:
        print(f"❌ Batch prediction failed: {response.status_code}")
        print(response.text)


def main():
    """Main workflow demonstration."""
    print_header("ML Model Deployment Workflow Demo")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Check prerequisites
    print("\n🔍 Checking prerequisites...")

    # Check MLOps API
    try:
        response = requests.get("http://localhost:8000/mlops/status")
        if response.status_code == 200:
            print("✅ MLOps API is accessible")
        else:
            print("❌ MLOps API not accessible")
            print("   Run: kubectl port-forward -n asgard svc/asgard-app 8000:80")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ MLOps API not accessible")
        print("   Run: kubectl port-forward -n asgard svc/asgard-app 8000:80")
        sys.exit(1)

    # Option to skip training
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--skip-train":
        print("\n⏩ Skipping training (using existing model)")
        model_name = "churn_predictor_feast"
        model_version = "latest"
    else:
        # Train model
        model_name, model_version = test_training_api()

        if not model_name:
            print("\n❌ Training failed. Exiting.")
            sys.exit(1)

    # Test inference service
    print("\n" + "=" * 80)
    print("NOTE: Ensure inference service is running:")
    print("  kubectl port-forward -n ml-inference svc/ml-inference-service 8080:80")
    print("=" * 80)
    input("\nPress Enter when inference service is ready...")

    test_inference_service(model_name, model_version)
    test_batch_inference()

    # Summary
    print_header("Demo Completed Successfully! 🎉")
    print("You have successfully:")
    print("  ✅ Trained a model with Feast features")
    print("  ✅ Deployed the model to EKS")
    print("  ✅ Made predictions via REST API")
    print("\nNext steps:")
    print("  1. Configure production ingress")
    print("  2. Set up monitoring and alerts")
    print("  3. Implement A/B testing")
    print("  4. Deploy to production")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
