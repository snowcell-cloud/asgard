#!/usr/bin/env python3
"""
Helper script to encode training scripts for MLOps deployment.

Usage:
    python encode_script.py train.py
    python encode_script.py train.py --output encoded.txt
    python encode_script.py train.py --deploy --model-name my_model
"""

import argparse
import base64
import json
import sys
from pathlib import Path


def encode_script(script_path: Path) -> str:
    """Encode a Python script to base64."""
    try:
        with open(script_path, "rb") as f:
            content = f.read()
        encoded = base64.b64encode(content).decode("utf-8")
        return encoded
    except FileNotFoundError:
        print(f"❌ Error: File not found: {script_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error encoding file: {e}", file=sys.stderr)
        sys.exit(1)


def create_deploy_request(
    script_path: Path,
    model_name: str,
    experiment_name: str = "default",
    requirements: list = None,
    timeout: int = 300,
    replicas: int = 2,
    namespace: str = "asgard",
) -> dict:
    """Create a deployment request JSON."""
    encoded_script = encode_script(script_path)

    return {
        "script_name": script_path.name,
        "script_content": encoded_script,
        "experiment_name": experiment_name,
        "model_name": model_name,
        "requirements": requirements or ["scikit-learn==1.3.2", "pandas==2.1.3", "numpy==1.26.2"],
        "environment_vars": {},
        "timeout": timeout,
        "tags": {"source": "encode_script.py"},
        "replicas": replicas,
        "namespace": namespace,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Encode training scripts for MLOps deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Just encode the script
  python encode_script.py train.py

  # Save encoded script to file
  python encode_script.py train.py --output encoded.txt

  # Create deployment request JSON
  python encode_script.py train.py --deploy --model-name my_model

  # Create deployment request with custom parameters
  python encode_script.py train.py --deploy \\
    --model-name customer_churn \\
    --experiment-name production \\
    --requirements scikit-learn pandas xgboost \\
    --timeout 600 \\
    --replicas 3

  # Deploy directly with curl
  python encode_script.py train.py --deploy --model-name my_model > request.json
  curl -X POST http://localhost:8000/mlops/deploy \\
    -H "Content-Type: application/json" \\
    -d @request.json
        """,
    )

    parser.add_argument("script_path", type=Path, help="Path to the training script to encode")

    parser.add_argument(
        "-o", "--output", type=Path, help="Output file for encoded script (default: stdout)"
    )

    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Create full deployment request JSON instead of just encoding",
    )

    parser.add_argument("--model-name", help="Model name for deployment (required if --deploy)")

    parser.add_argument(
        "--experiment-name", default="default", help="MLflow experiment name (default: default)"
    )

    parser.add_argument(
        "--requirements", nargs="+", help="Python package requirements (e.g., scikit-learn pandas)"
    )

    parser.add_argument(
        "--timeout", type=int, default=300, help="Training timeout in seconds (default: 300)"
    )

    parser.add_argument(
        "--replicas", type=int, default=2, help="Number of K8s replicas (default: 2)"
    )

    parser.add_argument(
        "--namespace", default="asgard", help="Kubernetes namespace (default: asgard)"
    )

    args = parser.parse_args()

    # Validate
    if args.deploy and not args.model_name:
        parser.error("--model-name is required when using --deploy")

    # Process
    if args.deploy:
        # Create deployment request
        request = create_deploy_request(
            script_path=args.script_path,
            model_name=args.model_name,
            experiment_name=args.experiment_name,
            requirements=args.requirements,
            timeout=args.timeout,
            replicas=args.replicas,
            namespace=args.namespace,
        )
        output = json.dumps(request, indent=2)
    else:
        # Just encode the script
        output = encode_script(args.script_path)

    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"✅ Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
