"""
Kubernetes client for SparkApplication operations.

Changes vs previous:
- driver/executor `env` entries use valueFrom.secretKeyRef for AWS env vars (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
  to match the successful SparkApplication example.
- Optional embedding of credentials into sparkConf (spark.hadoop.fs.s3a.access.key & spark.hadoop.fs.s3a.secret.key)
  via S3_EMBED_CREDENTIALS_IN_CONF=true (opt-in; default false).
- Keeps envFrom secretRef as well (so pods receive env vars and Spark JVM can use EnvironmentVariableCredentialsProvider).
- Validates presence of the secret when necessary and fetches values for embedding when requested.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import json
import base64

from fastapi import HTTPException

# Kubernetes client
from kubernetes import client, config
from kubernetes.client.rest import ApiException as K8sApiException

# ---------- helpers -----------------------------------------------------------


def _load_k8s_config():
    """
    Load Kubernetes configuration: prefer in-cluster, fallback to kubeconfig.
    Raise HTTPException on failure.
    """
    try:
        config.load_incluster_config()
    except Exception:
        try:
            config.load_kube_config()
        except Exception as e:
            raise HTTPException(500, f"Kube config error: {e}")


def ensure_secret_has_keys(namespace: str, secret_name: str, required_keys: List[str]) -> bool:
    """
    Check that a Kubernetes secret exists and contains the specified keys with non-empty values.
    Returns True if present and non-empty, False otherwise.
    """
    _load_k8s_config()
    v1 = client.CoreV1Api()
    try:
        secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)
    except K8sApiException:
        return False
    except Exception:
        return False

    data = getattr(secret, "data", {}) or {}
    for k in required_keys:
        val = data.get(k)
        if val is None:
            return False
        # Accept non-empty base64-encoded (client returns decoded str/bytes depending on version)
        if isinstance(val, (bytes, bytearray)):
            if len(val) == 0:
                return False
        elif isinstance(val, str):
            if val.strip() == "":
                return False
        else:
            return False
    return True


def get_secret_values(namespace: str, secret_name: str, keys: List[str]) -> Dict[str, str]:
    """
    Read a k8s secret and return a dict of decoded values for the requested keys.
    Raises HTTPException(400) if secret missing or keys not present.
    """
    _load_k8s_config()
    v1 = client.CoreV1Api()
    try:
        secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)
    except K8sApiException as e:
        raise HTTPException(
            400, f"Secret '{secret_name}' not found in namespace '{namespace}': {e.reason}"
        )
    except Exception as e:
        raise HTTPException(
            500, f"Error reading secret '{secret_name}' in namespace '{namespace}': {str(e)}"
        )

    data = getattr(secret, "data", {}) or {}
    result: Dict[str, str] = {}
    for k in keys:
        if k not in data or data.get(k) is None:
            raise HTTPException(400, f"Secret '{secret_name}' missing required key '{k}'")
        val = data.get(k)
        # The kubernetes client may return already-decoded values (str) or base64 strings depending on client version.
        # Try to handle both robustly:
        if isinstance(val, (bytes, bytearray)):
            decoded = val.decode("utf-8")
        else:
            # try base64 decode; if fails, treat as already decoded
            try:
                # if this is base64-encoded string, decoding will succeed and produce bytes
                decoded_bytes = base64.b64decode(val, validate=True)
                # If result decodes to readable UTF-8, use it. If not, fallback to original string.
                decoded = decoded_bytes.decode("utf-8")
            except Exception:
                # assume client already returned decoded string
                decoded = str(val)
        result[k] = decoded
    return result


def _build_image_pull_secrets(raw_value: Optional[str]) -> List[Dict[str, str]]:
    """
    Build imagePullSecrets as a list of {"name": "<secret>"} dicts.
    Accepts a comma-separated string or None. Defaults to ["ecr-secret"].
    """
    if not raw_value:
        raw_value = "ecr-secret"
    names = [s.strip() for s in raw_value.split(",") if s.strip()]
    return [{"name": n} for n in names]


def _secret_keyref_env(secret_name: str, key: str, env_name: str) -> Dict[str, Any]:
    """
    Build an env entry with valueFrom.secretKeyRef form:
    {
      "name": env_name,
      "valueFrom": {
        "secretKeyRef": {"name": secret_name, "key": key}
      }
    }
    """
    return {
        "name": env_name,
        "valueFrom": {
            "secretKeyRef": {
                "name": secret_name,
                "key": key,
            }
        },
    }


# ---------- SparkApplication client ------------------------------------------


class SparkApplicationClient:
    """Client for SparkApplications in Kubernetes."""

    def __init__(self, namespace: str = "asgard"):
        self.namespace = namespace
        _load_k8s_config()
        self.co = client.CustomObjectsApi()
        self.v1 = client.CoreV1Api()

    def create_spark_application(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a SparkApplication in Kubernetes."""
        try:
            response = self.co.create_namespaced_custom_object(
                group="sparkoperator.k8s.io",
                version="v1beta2",
                namespace=self.namespace,
                plural="sparkapplications",
                body=spec,
            )
            return response
        except K8sApiException as e:
            error_detail = f"SparkApplication create failed: {e.reason}"
            if getattr(e, "body", None):
                try:
                    error_body = json.loads(e.body)
                    error_detail += f" - {error_body.get('message', e.body)}"
                except Exception:
                    error_detail += f" - {e.body}"
            raise HTTPException(500, error_detail)
        except Exception as e:
            raise HTTPException(500, f"Unexpected error creating SparkApplication: {str(e)}")

    def get_spark_application(self, name: str) -> Dict[str, Any]:
        """Get a SparkApplication by name."""
        try:
            spark_app = self.co.get_namespaced_custom_object(
                group="sparkoperator.k8s.io",
                version="v1beta2",
                namespace=self.namespace,
                plural="sparkapplications",
                name=name,
            )
            return spark_app
        except K8sApiException as e:
            if e.status == 404:
                raise HTTPException(404, f"SparkApplication {name} not found")
            raise HTTPException(500, f"Failed to get SparkApplication: {e.reason}")
        except Exception as e:
            raise HTTPException(500, f"Unexpected error getting SparkApplication: {str(e)}")

    def list_spark_applications(
        self, limit: int = 20, label_selector: str = ""
    ) -> List[Dict[str, Any]]:
        """List SparkApplications."""
        try:
            spark_apps = self.co.list_namespaced_custom_object(
                group="sparkoperator.k8s.io",
                version="v1beta2",
                namespace=self.namespace,
                plural="sparkapplications",
                label_selector=label_selector,
                limit=limit,
            )
            return spark_apps.get("items", [])
        except K8sApiException as e:
            raise HTTPException(500, f"Failed to list SparkApplications: {e.reason}")
        except Exception as e:
            raise HTTPException(500, f"Unexpected error listing SparkApplications: {str(e)}")

    def delete_spark_application(self, name: str) -> Dict[str, Any]:
        """Delete a SparkApplication CR by name."""
        try:
            return self.co.delete_namespaced_custom_object(
                group="sparkoperator.k8s.io",
                version="v1beta2",
                namespace=self.namespace,
                plural="sparkapplications",
                name=name,
                body=client.V1DeleteOptions(),  # type: ignore[arg-type]
            )
        except K8sApiException as e:
            if e.status == 404:
                raise HTTPException(404, f"SparkApplication {name} not found")
            raise HTTPException(500, f"Failed to delete SparkApplication: {e.reason}")
        except Exception as e:
            raise HTTPException(500, f"Unexpected error deleting SparkApplication: {str(e)}")

    def get_pod_logs(
        self, pod_name: str, container: str = "spark-kubernetes-driver", tail_lines: int = 500
    ) -> str:
        """Get logs from a pod."""
        try:
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name, namespace=self.namespace, container=container, tail_lines=tail_lines
            )
            return logs
        except K8sApiException as e:
            if e.status == 404:
                return "Driver pod not found or logs not available yet"
            else:
                return f"Error getting logs: {e.reason}"
        except Exception as e:
            return f"Error getting logs: {str(e)}"

    def get_events(self, object_name: str) -> List[Dict[str, Any]]:
        """Get Kubernetes events for an object (pod/CR/etc)."""
        try:
            events = self.v1.list_namespaced_event(
                namespace=self.namespace, field_selector=f"involvedObject.name={object_name}"
            )

            def _ts(ev):
                # Prefer firstTimestamp, fallback to eventTime/lastTimestamp
                t = (
                    getattr(ev, "first_timestamp", None)
                    or getattr(ev, "event_time", None)
                    or getattr(ev, "last_timestamp", None)
                )
                if t is None:
                    return ""
                if isinstance(t, datetime):
                    return t.isoformat()
                return str(t)

            return [
                {
                    "time": _ts(event),
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "object": f"{event.involved_object.kind}/{object_name}",
                }
                for event in events.items
            ]
        except Exception:
            return []


# ---------- SparkApplication factory -----------------------------------------


class SparkApplicationFactory:
    """Factory to create SparkApplication specs for SQL executions."""

    @staticmethod
    def create_sql_execution_spec(
        name: str,
        namespace: str,
        sql: str,
        sources: List[str],
        destination: str,
        write_mode: str = "overwrite",
        driver_cores: int = 1,
        driver_memory: str = "512m",
        executor_cores: int = 1,
        executor_instances: int = 1,
        executor_memory: str = "512m",
        spark_image: Optional[str] = None,
        service_account: str = "spark-sa",
        s3_secret_name: str = "s3-credentials",
    ) -> Dict[str, Any]:
        """
        Create a SparkApplication spec for SQL execution.

        Differences / options:
        - Creates explicit env entries with valueFrom.secretKeyRef for AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION.
        - Keeps envFrom: secretRef so environment variables are still populated.
        - Optionally embeds credentials into sparkConf if S3_EMBED_CREDENTIALS_IN_CONF=true (opt-in).
        """

        # Allow overriding spark image via environment
        if not spark_image:
            spark_image = os.getenv(
                "SPARK_IMAGE", "637423187518.dkr.ecr.eu-north-1.amazonaws.com/spark-custom:latest"
            )

        # Provider selection (default: default chain)
        force_env = os.getenv("S3_FORCE_ENV_PROVIDER", "false").lower() in ("1", "true", "yes")

        aws_provider = os.getenv(
            "S3_AWS_PROVIDER", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"
        )

        # Optional explicit endpoint (useful for particular region or S3-compatible storage)
        s3_endpoint = os.getenv("S3_ENDPOINT", "s3.eu-north-1.amazonaws.com")

        # Optionally embed credentials in sparkConf (opt-in; default false)
        embed_creds_in_conf = os.getenv("S3_EMBED_CREDENTIALS_IN_CONF", "false").lower() in (
            "1",
            "true",
            "yes",
        )

        # If we will embed creds in conf we must fetch them from the secret (and validate presence)
        creds_map: Dict[str, str] = {}
        if embed_creds_in_conf:
            # Ensure keys exist
            required = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
            if not ensure_secret_has_keys(namespace, s3_secret_name, required):
                raise HTTPException(
                    400,
                    f"Secret '{s3_secret_name}' must contain non-empty {', '.join(required)} to embed credentials in sparkConf.",
                )
            # Fetch actual values (decoded)
            creds_map = get_secret_values(namespace, s3_secret_name, required)

        # Build env entries for driver & executor (explicit secretKeyRef entries)
        aws_env_entries = [
            _secret_keyref_env(s3_secret_name, "AWS_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID"),
            _secret_keyref_env(s3_secret_name, "AWS_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY"),
            _secret_keyref_env(s3_secret_name, "AWS_REGION", "AWS_REGION"),
        ]

        # Build imagePullSecrets as objects
        image_pull_secrets = _build_image_pull_secrets(
            os.getenv("IMAGE_PULL_SECRETS", "ecr-secret")
        )

        # Base sparkConf
        spark_conf: Dict[str, str] = {
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            "spark.hadoop.fs.s3a.aws.credentials.provider": "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
            "spark.hadoop.fs.s3a.access.key": os.getenv("AWS_ACCESS_KEY_ID"),
            "spark.hadoop.fs.s3a.secret.key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "spark.hadoop.fs.s3a.endpoint.region": os.getenv("AWS_REGION", "eu-north-1"),
            "spark.hadoop.fs.s3a.endpoint": s3_endpoint,
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
            "spark.hadoop.fs.s3a.fast.upload": "true",
            "spark.hadoop.fs.s3a.multipart.size": "67108864",
            "spark.hadoop.fs.s3a.connection.ssl.enabled": "true",
            "spark.hadoop.fs.s3a.path.style.access": "false",
            "spark.driver.extraJavaOptions": "-Dcom.amazonaws.services.s3.enableV4=true",
            "spark.executor.extraJavaOptions": "-Dcom.amazonaws.services.s3.enableV4=true",
            "spark.sql.transform.query": sql,
            "spark.sql.transform.sources": json.dumps(sources),
            "spark.sql.transform.destination": destination,
            "spark.sql.transform.writeMode": write_mode,
        }

        # If embedding credentials in conf (opt-in), add access + secret into sparkConf (mirrors your working spec)
        if embed_creds_in_conf:
            # Note: these are sensitive values embedded into the CRD; only enable in trusted setups.
            spark_conf["spark.hadoop.fs.s3a.access.key"] = creds_map["AWS_ACCESS_KEY_ID"]
            spark_conf["spark.hadoop.fs.s3a.secret.key"] = creds_map["AWS_SECRET_ACCESS_KEY"]
            # Optionally set provider used in working spec
            spark_conf["spark.hadoop.fs.s3a.aws.credentials.provider"] = os.getenv(
                "S3_EMBED_PROVIDER", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"
            )

        spec: Dict[str, Any] = {
            "apiVersion": "sparkoperator.k8s.io/v1beta2",
            "kind": "SparkApplication",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": {"app": "asgard-transform", "type": "sql-transformation"},
            },
            "spec": {
                "type": "Python",
                "pythonVersion": "3",
                "mode": "cluster",
                "image": spark_image,
                "imagePullPolicy": "Always",
                "imagePullSecrets": image_pull_secrets,
                "mainApplicationFile": "local:///opt/spark/sql_transform.py",
                "sparkVersion": "3.4.0",
                "restartPolicy": {"type": "Never"},
                "driver": {
                    "cores": driver_cores,
                    "memory": driver_memory,
                    "serviceAccount": service_account,
                    "envFrom": [{"secretRef": {"name": s3_secret_name}}],
                    "env": [
                        {
                            "name": "AWS_ACCESS_KEY_ID",
                            "valueFrom": {
                                "secretKeyRef": {"name": s3_secret_name, "key": "AWS_ACCESS_KEY_ID"}
                            },
                        },
                        {
                            "name": "AWS_SECRET_ACCESS_KEY",
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": s3_secret_name,
                                    "key": "AWS_SECRET_ACCESS_KEY",
                                }
                            },
                        },
                        {
                            "name": "AWS_REGION",
                            "valueFrom": {
                                "secretKeyRef": {"name": s3_secret_name, "key": "AWS_REGION"}
                            },
                        },
                        {"name": "SQL_QUERY", "value": sql},
                        {"name": "SOURCE_PATHS", "value": json.dumps(sources)},
                        {"name": "DESTINATION_PATH", "value": destination},
                        {"name": "WRITE_MODE", "value": write_mode},
                    ],
                    "volumeMounts": [],
                },
                "executor": {
                    "cores": executor_cores,
                    "instances": executor_instances,
                    "memory": executor_memory,
                    "envFrom": [{"secretRef": {"name": s3_secret_name}}],
                    "env": [
                        {
                            "name": "AWS_ACCESS_KEY_ID",
                            "valueFrom": {
                                "secretKeyRef": {"name": s3_secret_name, "key": "AWS_ACCESS_KEY_ID"}
                            },
                        },
                        {
                            "name": "AWS_SECRET_ACCESS_KEY",
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": s3_secret_name,
                                    "key": "AWS_SECRET_ACCESS_KEY",
                                }
                            },
                        },
                        {
                            "name": "AWS_REGION",
                            "valueFrom": {
                                "secretKeyRef": {"name": s3_secret_name, "key": "AWS_REGION"}
                            },
                        },
                        {"name": "SQL_QUERY", "value": sql},
                        {"name": "SOURCE_PATHS", "value": json.dumps(sources)},
                        {"name": "DESTINATION_PATH", "value": destination},
                        {"name": "WRITE_MODE", "value": write_mode},
                    ],
                },
                "sparkConf": spark_conf,
                "volumes": [],
            },
        }

        return spec


# small helper to ensure type correctness for env list expansion
def _env_to_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return items (no-op helper so mypy/type-checkers like consistent types)."""
    return items


# ---------- convenience ------------------------------------------------------


def get_spark_client() -> SparkApplicationClient:
    """Dependency function to get SparkApplicationClient with namespace from env."""
    namespace = os.getenv("SPARK_NAMESPACE", "asgard")
    return SparkApplicationClient(namespace=namespace)


# Example usage (uncomment for local testing)
# if __name__ == "__main__":
#     client = get_spark_client()
#     spec = SparkApplicationFactory.create_sql_execution_spec(
#         name="sql-exec-example", namespace="asgard",
#         sql="SELECT * FROM source_data LIMIT 10",
#         sources=["s3a://airbytedestination1/bronze/users/2025_08_05_1754375136147_0.parquet"],
#         destination="s3a://airbytedestination1/silver/example/",
#         write_mode="overwrite",
#     )
#     print(json.dumps(spec, indent=2))
#     # To create: client.create_spark_application(spec)
