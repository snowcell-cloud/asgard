from fastapi import APIRouter, HTTPException, Depends

from kubernetes import client, config
import os, json, uuid

from app.data_transformation.schemas import TransformReq
from app.airbyte.client import get_airbyte_client_dependency, AirbyteClient, AirbyteClientError

router = APIRouter(tags=["transform"])  # POST /transform

NAMESPACE = os.getenv("PIPELINE_NAMESPACE", "asgard")
SPARK_IMAGE = os.getenv("SPARK_IMAGE", "<REGISTRY>/spark-parquet-aws:3.5.1")
SPARK_SERVICE_ACCOUNT = os.getenv("SPARK_SERVICE_ACCOUNT", "spark-sa")
S3_SECRET_NAME = os.getenv("S3_SECRET_NAME", "s3-credentials")


def kube_co() -> client.CustomObjectsApi:
    try:
        config.load_incluster_config()
    except Exception:
        try:
            config.load_kube_config()
        except Exception as e:
            raise HTTPException(500, f"Kube config error: {e}")
    return client.CustomObjectsApi()


async def _resolve_workspace_id(client: AirbyteClient, workspace_name: str | None = None) -> str:
    """Resolve workspace ID from name or get default workspace."""
    try:
        workspaces = await client.list_workspaces()
        
        if not workspaces:
            raise HTTPException(status_code=404, detail="No workspaces found")
        
        if workspace_name:
            # Find workspace by name
            for workspace in workspaces:
                if workspace.get("name") == workspace_name:
                    return workspace["workspaceId"]
            raise HTTPException(status_code=404, detail=f"Workspace '{workspace_name}' not found")
        
        # Return first workspace as default
        return workspaces[0]["workspaceId"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving workspace: {str(e)}")


async def _get_s3_destinations(airbyte_client: AirbyteClient) -> list[dict]:
    """Fetch S3 destinations from Airbyte."""
    try:
        workspace_id = await _resolve_workspace_id(airbyte_client)
        destinations = await airbyte_client.list_destinations(workspace_id)
        
        # Filter for S3 destinations only
        s3_destinations = []
        for dest in destinations:
            if dest.get("destinationName", "").lower() == "s3":
                s3_destinations.append(dest)
        
        if not s3_destinations:
            raise HTTPException(
                status_code=404, 
                detail="No S3 destinations found in Airbyte. Please register an S3 sink first using /sink endpoint."
            )
        
        return s3_destinations
    except AirbyteClientError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Airbyte error: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching S3 destinations: {str(e)}")


@router.post("/transform")
async def submit_transform(
    req: TransformReq, 
    co: client.CustomObjectsApi = Depends(kube_co),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client_dependency)
):
    # Fetch S3 destinations from Airbyte
    s3_destinations = await _get_s3_destinations(airbyte_client)
    
    # Use the first S3 destination as source
    source_dest = s3_destinations[0]
    
    # Extract S3 configuration from the destination
    dest_config = source_dest.get("configuration", {})
    source_bucket = dest_config.get("s3_bucket_name")
    source_path = dest_config.get("s3_bucket_path", "")
    
    if not source_bucket:
        raise HTTPException(
            status_code=500,
            detail="S3 destination configuration is missing bucket name"
        )
    
    # Construct source and destination paths
    source_s3_path = f"s3a://{source_bucket}/{source_path}"
    destination_s3_path = f"s3a://{source_bucket}/silver/"
    
    # Sources list for Spark (bronze layer data)
    sources = [source_s3_path]
    destination = destination_s3_path
    
    run_id = uuid.uuid4().hex[:8]
    name = f"sql-exec-{run_id}"

    spec_json = json.dumps({
        "sql": req.sql,
        "sources": sources,
        "destination": destination,
        "write_mode": req.write_mode
    })

    body = {
      "apiVersion": "sparkoperator.k8s.io/v1beta2",
      "kind": "SparkApplication",
      "metadata": {"name": name, "namespace": NAMESPACE},
      "spec": {
        "type": "Python",
        "pythonVersion": "3",
        "mode": "cluster",
        "image": SPARK_IMAGE,
        "imagePullPolicy": "IfNotPresent",
        "mainApplicationFile": "local:///opt/jobs/transform_sql_exec.py",
        "sparkVersion": "3.5.1",
        "restartPolicy": {"type": "Never"},
        "driver": {
          "cores": req.driver_cores,
          "memory": req.driver_memory,
          "serviceAccount": SPARK_SERVICE_ACCOUNT,
          "envFrom": [{"secretRef": {"name": S3_SECRET_NAME}}],
        },
        "executor": {
          "cores": req.executor_cores,
          "instances": req.executor_instances,
          "memory": req.executor_memory,
          "envFrom": [{"secretRef": {"name": S3_SECRET_NAME}}],
        },
        "deps": {
          "packages": [
            "org.apache.hadoop:hadoop-aws:3.3.4",
            "com.amazonaws:aws-java-sdk-bundle:1.12.367"
          ]
        },
        "sparkConf": {
          "spark.sql.adaptive.enabled": "true",
          "spark.hadoop.fs.s3a.aws.region": "$(AWS_REGION)",
          "spark.hadoop.fs.s3a.aws.credentials.provider": "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
          "spark.hadoop.fs.s3a.access.key": "$(AWS_ACCESS_KEY_ID)",
          "spark.hadoop.fs.s3a.secret.key": "$(AWS_SECRET_ACCESS_KEY)",
          "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem"
        },
        "driverEnv": {"TRANSFORM_SPEC_JSON": spec_json}
      }
    }

    try:
        co.create_namespaced_custom_object(
            group="sparkoperator.k8s.io",
            version="v1beta2",
            namespace=NAMESPACE,
            plural="sparkapplications",
            body=body,
        )
    except client.ApiException as e:
        raise HTTPException(500, f"SparkApplication create failed: {e.reason} {e.body}")

    return {
        "run_id": run_id, 
        "spark_application": name, 
        "status": "submitted",
        "source": source_s3_path,
        "destination": destination_s3_path,
        "message": f"Transformation submitted. Source: {source_s3_path} -> Destination: {destination_s3_path}"
    }
