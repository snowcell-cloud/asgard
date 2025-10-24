#!/usr/bin/env python3
"""
Helper script to upload training scripts to the MLOps API.

This script:
1. Reads a Python training script
2. Base64 encodes it
3. Uploads it to the MLOps API via POST /mlops/training/upload
4. Polls for job status until completion

Usage:
    python upload_training_script.py \
        --script examples/training_scripts/sklearn_classification.py \
        --experiment sklearn_examples \
        --model random_forest_classifier \
        --api-url http://localhost:8000

    # Or with port-forward to Kubernetes
    kubectl port-forward -n asgard svc/asgard-api 8000:8000 &
    python upload_training_script.py \
        --script examples/training_scripts/xgboost_regression.py \
        --experiment xgboost_examples \
        --model xgb_regressor
"""

import argparse
import base64
import json
import time
from pathlib import Path

import requests


def read_and_encode_script(script_path: str) -> str:
    """Read Python script and encode as base64."""
    with open(script_path, "r") as f:
        script_content = f.read()

    # Encode to base64
    encoded = base64.b64encode(script_content.encode("utf-8")).decode("utf-8")
    return encoded


def upload_script(
    api_url: str,
    script_path: str,
    experiment_name: str,
    model_name: str,
    requirements: list = None,
    environment_vars: dict = None,
    timeout: int = 300,
):
    """Upload training script to MLOps API."""
    script_name = Path(script_path).stem

    # Read and encode script
    print(f"📄 Reading script: {script_path}")
    encoded_script = read_and_encode_script(script_path)

    # Prepare request
    payload = {
        "script_name": script_name,
        "script_content": encoded_script,
        "experiment_name": experiment_name,
        "model_name": model_name,
        "requirements": requirements or [],
        "environment_vars": environment_vars or {},
        "timeout": timeout,
        "tags": {"uploaded_by": "upload_script", "script_file": script_path},
    }

    # Upload script
    print(f"🚀 Uploading to: {api_url}/mlops/training/upload")
    response = requests.post(
        f"{api_url}/mlops/training/upload",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 202:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.text)
        return None

    result = response.json()
    job_id = result["job_id"]

    print(f"✅ Script uploaded successfully!")
    print(f"   Job ID: {job_id}")
    print(f"   Experiment: {experiment_name}")
    print(f"   Model: {model_name}")

    return job_id


def poll_job_status(api_url: str, job_id: str, poll_interval: int = 5):
    """Poll job status until completion."""
    print(f"\n⏳ Polling job status...")

    while True:
        response = requests.get(f"{api_url}/mlops/training/jobs/{job_id}")

        if response.status_code != 200:
            print(f"❌ Failed to get job status: {response.status_code}")
            break

        job_status = response.json()
        status = job_status["status"]

        print(f"   Status: {status}")

        if status in ["completed", "failed"]:
            print(f"\n{'='*60}")
            print(f"Job {status.upper()}")
            print(f"{'='*60}")

            if status == "completed":
                print(f"✅ Training completed successfully!")
                print(f"   Run ID: {job_status.get('run_id')}")
                print(f"   Model Version: {job_status.get('model_version')}")

                if job_status.get("duration_seconds"):
                    print(f"   Duration: {job_status['duration_seconds']:.2f}s")
            else:
                print(f"❌ Training failed!")
                print(f"   Error: {job_status.get('error')}")

            # Print logs if available
            if job_status.get("logs"):
                print(f"\n📋 Execution Logs:")
                print(f"{'-'*60}")
                print(job_status["logs"])

            break

        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(
        description="Upload and execute training scripts via MLOps API"
    )
    parser.add_argument("--script", required=True, help="Path to Python training script")
    parser.add_argument("--experiment", required=True, help="MLflow experiment name")
    parser.add_argument("--model", required=True, help="Model name for registration")
    parser.add_argument(
        "--requirements", nargs="*", default=[], help="Additional pip packages to install"
    )
    parser.add_argument(
        "--env",
        action="append",
        help="Environment variables in KEY=VALUE format (can be used multiple times)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Execution timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="MLOps API URL (default: http://localhost:8000)",
    )
    parser.add_argument("--no-poll", action="store_true", help="Don't poll for job status")

    args = parser.parse_args()

    # Parse environment variables
    environment_vars = {}
    if args.env:
        for env_str in args.env:
            key, value = env_str.split("=", 1)
            environment_vars[key] = value

    # Upload script
    job_id = upload_script(
        api_url=args.api_url,
        script_path=args.script,
        experiment_name=args.experiment,
        model_name=args.model,
        requirements=args.requirements,
        environment_vars=environment_vars,
        timeout=args.timeout,
    )

    if not job_id:
        return

    # Poll for status unless --no-poll is specified
    if not args.no_poll:
        poll_job_status(args.api_url, job_id)
    else:
        print(f"\nTo check status later, run:")
        print(f"curl {args.api_url}/mlops/training/jobs/{job_id}")


if __name__ == "__main__":
    main()
