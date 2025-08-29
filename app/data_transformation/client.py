"""
Kubernetes client for SparkApplication operations.
"""

from kubernetes import client, config
from fastapi import HTTPException
from datetime import datetime
from typing import Dict, List, Optional, Any
import os


class SparkApplicationClient:
    """Client for managing SparkApplications in Kubernetes."""
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self._setup_kubernetes_client()
    
    def _setup_kubernetes_client(self):
        """Initialize Kubernetes client."""
        try:
            config.load_incluster_config()
        except Exception:
            try:
                config.load_kube_config()
            except Exception as e:
                raise HTTPException(500, f"Kube config error: {e}")
    
    def create_spark_application(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a SparkApplication in Kubernetes."""
        co = client.CustomObjectsApi()
        
        try:
            response = co.create_namespaced_custom_object(
                group="sparkoperator.k8s.io",
                version="v1beta2",
                namespace=self.namespace,
                plural="sparkapplications",
                body=spec,
            )
            return response
            
        except client.ApiException as e:
            error_detail = f"SparkApplication create failed: {e.reason}"
            if e.body:
                try:
                    import json
                    error_body = json.loads(e.body)
                    error_detail += f" - {error_body.get('message', e.body)}"
                except:
                    error_detail += f" - {e.body}"
            raise HTTPException(500, error_detail)
        except Exception as e:
            error_detail = f"Unexpected error creating SparkApplication: {str(e)}"
            raise HTTPException(500, error_detail)
    
    def get_spark_application(self, name: str) -> Dict[str, Any]:
        """Get a SparkApplication by name."""
        co = client.CustomObjectsApi()
        
        try:
            spark_app = co.get_namespaced_custom_object(
                group="sparkoperator.k8s.io",
                version="v1beta2",
                namespace=self.namespace,
                plural="sparkapplications",
                name=name
            )
            return spark_app
            
        except client.ApiException as e:
            if e.status == 404:
                raise HTTPException(404, f"SparkApplication {name} not found")
            raise HTTPException(500, f"Failed to get SparkApplication: {e.reason}")
        except Exception as e:
            raise HTTPException(500, f"Unexpected error getting SparkApplication: {str(e)}")
    
    def list_spark_applications(self, limit: int = 20, label_selector: str = "") -> List[Dict[str, Any]]:
        """List SparkApplications."""
        co = client.CustomObjectsApi()
        
        try:
            spark_apps = co.list_namespaced_custom_object(
                group="sparkoperator.k8s.io",
                version="v1beta2",
                namespace=self.namespace,
                plural="sparkapplications",
                label_selector=label_selector,
                limit=limit
            )
            return spark_apps.get("items", [])
            
        except client.ApiException as e:
            raise HTTPException(500, f"Failed to list SparkApplications: {e.reason}")
        except Exception as e:
            raise HTTPException(500, f"Unexpected error listing SparkApplications: {str(e)}")
    
    def get_pod_logs(self, pod_name: str, container: str = "spark-kubernetes-driver") -> str:
        """Get logs from a pod."""
        v1 = client.CoreV1Api()
        
        try:
            logs = v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.namespace,
                container=container
            )
            return logs
            
        except client.ApiException as e:
            if e.status == 404:
                return "Driver pod not found or logs not available yet"
            else:
                return f"Error getting logs: {e.reason}"
    
    def get_events(self, object_name: str) -> List[Dict[str, Any]]:
        """Get Kubernetes events for an object."""
        v1 = client.CoreV1Api()
        
        try:
            events = v1.list_namespaced_event(
                namespace=self.namespace,
                field_selector=f"involvedObject.name={object_name}"
            )
            
            return [
                {
                    "time": event.first_timestamp.isoformat() if event.first_timestamp else "",
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "object": f"{event.involved_object.kind}/{object_name}"
                }
                for event in events.items
            ]
            
        except client.ApiException as e:
            return []
        except Exception as e:
            return []


class SparkApplicationFactory:
    """Factory for creating SparkApplication specifications."""
    
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
        spark_image: str = None,
        service_account: str = "spark-sa",
        s3_secret_name: str = "s3-credentials"
    ) -> Dict[str, Any]:
        """Create a SparkApplication spec for SQL execution."""
        
        import json
        # Use custom spark image with S3A support
        if not spark_image:
            spark_image = os.getenv("SPARK_IMAGE", "637423187518.dkr.ecr.eu-north-1.amazonaws.com/spark-custom:latest")
        
        # Create a simple Python script content that reads from S3 and runs SQL
        python_script_content = f'''
import os
import sys
from pyspark.sql import SparkSession

# Initialize Spark session with S3 configuration
spark = SparkSession.builder \\
    .appName("SQL Data Transformation - {name}") \\
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \\
    .config("spark.hadoop.fs.s3a.access.key", os.getenv("AWS_ACCESS_KEY_ID")) \\
    .config("spark.hadoop.fs.s3a.secret.key", os.getenv("AWS_SECRET_ACCESS_KEY")) \\
    .config("spark.hadoop.fs.s3a.endpoint", "s3.amazonaws.com") \\
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \\
    .config("spark.hadoop.fs.s3a.fast.upload", "true") \\
    .config("spark.sql.adaptive.enabled", "true") \\
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \\
    .getOrCreate()

print("Spark session initialized successfully")

try:
    # Source paths from environment
    source_paths = {sources}
    destination_path = "{destination}"
    sql_query = "{sql}" if "{sql}".strip() else "SELECT *, '{name}' as processing_run_id FROM source_data"
    
    print(f"Reading data from sources: {{source_paths}}")
    
    # Read data from all source paths and union them
    dfs = []
    for source_path in source_paths:
        print(f"Reading from: {{source_path}}")
        try:
            df = spark.read.parquet(source_path)
            print(f"Successfully read {{df.count()}} rows from {{source_path}}")
            dfs.append(df)
        except Exception as e:
            print(f"Warning: Could not read from {{source_path}}: {{e}}")
    
    if not dfs:
        print("No data found in any source paths")
        sys.exit(1)
    
    # Union all dataframes
    if len(dfs) == 1:
        combined_df = dfs[0]
    else:
        combined_df = dfs[0]
        for df in dfs[1:]:
            combined_df = combined_df.union(df)
    
    print(f"Combined dataset has {{combined_df.count()}} total rows")
    
    # Show schema and sample data
    print("Schema:")
    combined_df.printSchema()
    print("Sample data (first 5 rows):")
    combined_df.show(5, truncate=False)
    
    # Create temporary view for SQL
    combined_df.createOrReplaceTempView("source_data")
    
    # Execute SQL transformation
    print(f"Executing SQL: {{sql_query}}")
    result_df = spark.sql(sql_query)
    
    print("Transformation result sample:")
    result_df.show(5, truncate=False)
    print(f"Result has {{result_df.count()}} rows")
    
    # Write results to destination
    print(f"Writing results to: {{destination_path}}")
    result_df.coalesce(1) \\
        .write \\
        .mode("{write_mode}") \\
        .parquet(destination_path)
    
    print("✅ Transformation completed successfully!")
    
except Exception as e:
    print(f"❌ Error during transformation: {{str(e)}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
finally:
    spark.stop()
'''
        
        # Create spec for the transformation
        spec_json = json.dumps({
            "sql": sql,
            "sources": sources,
            "destination": destination,
            "write_mode": write_mode
        })
        
        return {
            "apiVersion": "sparkoperator.k8s.io/v1beta2",
            "kind": "SparkApplication",
            "metadata": {"name": name, "namespace": namespace},
            "spec": {
                "type": "Python",
                "pythonVersion": "3",
                "mode": "cluster",
                "image": spark_image,
                "imagePullPolicy": "IfNotPresent",
                "mainApplicationFile": "local:///opt/bitnami/spark/work-dir/sql_transform.py",
                "sparkVersion": "3.4.0",
                "restartPolicy": {"type": "Never"},
                "volumes": [
                    {
                        "name": "sql-script",
                        "configMap": {
                            "name": "sql-transform-script"
                        }
                    }
                ],
                "driver": {
                    "cores": driver_cores,
                    "memory": driver_memory,
                    "serviceAccount": service_account,
                    "envFrom": [{"secretRef": {"name": s3_secret_name}}],
                    "env": [
                        {"name": "TRANSFORM_SPEC", "value": spec_json},
                        {"name": "SQL_QUERY", "value": sql},
                        {"name": "SOURCE_PATHS", "value": json.dumps(sources)},
                        {"name": "DESTINATION_PATH", "value": destination},
                        {"name": "WRITE_MODE", "value": write_mode}
                    ],
                    "volumeMounts": [
                        {
                            "name": "sql-script",
                            "mountPath": "/opt/bitnami/spark/work-dir/sql_transform.py",
                            "subPath": "sql_transform.py"
                        }
                    ]
                },
                "executor": {
                    "cores": executor_cores,
                    "instances": executor_instances,
                    "memory": executor_memory,
                    "envFrom": [{"secretRef": {"name": s3_secret_name}}],
                    "env": [
                        {"name": "TRANSFORM_SPEC", "value": spec_json},
                        {"name": "SQL_QUERY", "value": sql},
                        {"name": "SOURCE_PATHS", "value": json.dumps(sources)},
                        {"name": "DESTINATION_PATH", "value": destination},
                        {"name": "WRITE_MODE", "value": write_mode}
                    ]
                },
                "sparkConf": {
                    "spark.sql.adaptive.enabled": "true",
                    "spark.hadoop.fs.s3a.aws.credentials.provider": "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
                    "spark.hadoop.fs.s3a.access.key": "$(AWS_ACCESS_KEY_ID)",
                    "spark.hadoop.fs.s3a.secret.key": "$(AWS_SECRET_ACCESS_KEY)",
                    "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
                    "spark.hadoop.fs.s3a.fast.upload": "true",
                    "spark.hadoop.fs.s3a.aws.region": "$(AWS_REGION)"
                }
            }
        }


def get_spark_client() -> SparkApplicationClient:
    """Dependency function to get SparkApplicationClient."""
    namespace = os.getenv("SPARK_NAMESPACE", "default")
    return SparkApplicationClient(namespace=namespace)
