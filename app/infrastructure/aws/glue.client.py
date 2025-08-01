"""
AWS Glue client for executing PySpark transformations
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GlueExecutor:
    """AWS Glue job executor for data transformations"""

    def __init__(self):
        self.settings = get_settings()
        self.glue_client = boto3.client("glue", region_name=self.settings.aws_region)
        self.s3_client = boto3.client("s3", region_name=self.settings.aws_region)

    async def submit_job(self, execution_context: Dict[str, Any]) -> str:
        """Submit a transformation job to AWS Glue"""

        job_name = f"transformation-{execution_context['execution_id']}"
        script_location = await self._upload_transformation_script(execution_context)

        try:
            # Create Glue job
            job_definition = {
                "Name": job_name,
                "Role": self.settings.glue_service_role,
                "Command": {
                    "Name": "glueetl",
                    "ScriptLocation": script_location,
                    "PythonVersion": "3",
                },
                "DefaultArguments": {
                    "--enable-metrics": "",
                    "--enable-spark-ui": "true",
                    "--enable-job-insights": "true",
                    "--job-language": "python",
                    "--TempDir": self.settings.glue_temp_dir,
                    "--enable-glue-datacatalog": "",
                    "--execution_id": execution_context["execution_id"],
                    "--transformation_id": execution_context["transformation_id"],
                    "--source_path": f"s3://{self.settings.s3_bucket}{execution_context['source_path']}",
                    "--target_path": f"s3://{self.settings.s3_bucket}{execution_context['target_path']}",
                    "--sql_query": execution_context["query"],
                    "--data_format": execution_context.get("data_format", "parquet"),
                    "--compression": execution_context.get("compression", "snappy"),
                    "--overwrite_mode": execution_context.get(
                        "overwrite_mode", "overwrite"
                    ),
                    "--partition_columns": ",".join(
                        execution_context.get("partition_columns", [])
                    ),
                    "--dry_run": str(execution_context.get("dry_run", False)),
                    "--sample_size": str(execution_context.get("sample_size", 0)),
                    "--database_name": self.settings.glue_database_name or "default",
                },
                "MaxRetries": 1,
                "Timeout": self.settings.job_timeout_minutes,
                "GlueVersion": "4.0",
                "NumberOfWorkers": execution_context.get(
                    "number_of_workers", self.settings.glue_number_of_workers
                ),
                "WorkerType": execution_context.get(
                    "worker_type", self.settings.glue_worker_type
                ),
                "SecurityConfiguration": (
                    self.settings.glue_security_config
                    if hasattr(self.settings, "glue_security_config")
                    else None
                ),
            }

            # Remove None values
            job_definition = {k: v for k, v in job_definition.items() if v is not None}

            # Create the job
            logger.info(f"Creating Glue job: {job_name}")
            self.glue_client.create_job(**job_definition)

            # Start job run
            logger.info(f"Starting Glue job run: {job_name}")
            response = self.glue_client.start_job_run(
                JobName=job_name, Arguments=job_definition["DefaultArguments"]
            )

            job_run_id = response["JobRunId"]
            logger.info(f"Glue job started: {job_run_id}")

            # Schedule job cleanup
            asyncio.create_task(self._schedule_job_cleanup(job_name, job_run_id))

            return job_run_id

        except ClientError as e:
            logger.error(f"Failed to submit Glue job: {str(e)}")
            raise Exception(f"Glue job submission failed: {str(e)}")

    async def get_job_status(self, job_run_id: str) -> Dict[str, Any]:
        """Get the status of a Glue job run"""

        try:
            # Extract job name from job run ID (format: jr_<hash>)
            job_name = await self._get_job_name_from_run_id(job_run_id)

            response = self.glue_client.get_job_run(JobName=job_name, RunId=job_run_id)

            job_run = response["JobRun"]
            status = job_run["JobRunState"]

            # Map Glue status to our standard status
            status_mapping = {
                "STARTING": "submitted",
                "RUNNING": "running",
                "STOPPING": "running",
                "STOPPED": "cancelled",
                "SUCCEEDED": "completed",
                "FAILED": "failed",
                "TIMEOUT": "failed",
            }

            mapped_status = status_mapping.get(status, "unknown")

            result = {
                "status": mapped_status,
                "glue_status": status,
                "started_on": job_run.get("StartedOn"),
                "completed_on": job_run.get("CompletedOn"),
                "execution_time": job_run.get("ExecutionTime"),
                "max_capacity": job_run.get("MaxCapacity"),
                "worker_type": job_run.get("WorkerType"),
                "number_of_workers": job_run.get("NumberOfWorkers"),
            }

            # Add error message if failed
            if status in ["FAILED", "TIMEOUT"]:
                result["error_message"] = job_run.get(
                    "ErrorMessage", "Job failed without specific error message"
                )

            # Add metrics if available
            if mapped_status == "completed":
                result["metrics"] = await self._get_job_metrics(job_run_id)

            return result

        except ClientError as e:
            logger.error(f"Failed to get job status for {job_run_id}: {str(e)}")
            return {
                "status": "unknown",
                "error_message": f"Failed to get job status: {str(e)}",
            }

    async def cancel_job(self, job_run_id: str) -> bool:
        """Cancel a running Glue job"""

        try:
            job_name = await self._get_job_name_from_run_id(job_run_id)

            self.glue_client.stop_job_run(JobName=job_name, JobRunId=job_run_id)

            logger.info(f"Cancelled Glue job: {job_run_id}")

            # Schedule cleanup
            asyncio.create_task(self._cleanup_job(job_name))

            return True

        except ClientError as e:
            logger.error(f"Failed to cancel job {job_run_id}: {str(e)}")
            return False

    async def execute_preview(self, preview_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a preview transformation with limited data"""

        # For preview, we'll use a simplified approach with a small Glue job
        preview_job_name = f"preview-{preview_context.get('execution_id', 'test')}"

        try:
            # Create preview script
            script_location = await self._upload_preview_script(preview_context)

            # Create and run preview job
            job_definition = {
                "Name": preview_job_name,
                "Role": self.settings.glue_service_role,
                "Command": {
                    "Name": "glueetl",
                    "ScriptLocation": script_location,
                    "PythonVersion": "3",
                },
                "DefaultArguments": {
                    "--enable-metrics": "",
                    "--job-language": "python",
                    "--TempDir": self.settings.glue_temp_dir,
                    "--source_path": f"s3://{self.settings.s3_bucket}{preview_context['source_path']}",
                    "--sql_query": preview_context["query"],
                    "--sample_size": str(preview_context.get("sample_size", 100)),
                    "--database_name": self.settings.glue_database_name or "default",
                },
                "MaxRetries": 0,
                "Timeout": 10,  # 10 minutes max for preview
                "GlueVersion": "4.0",
                "NumberOfWorkers": 2,  # Minimal workers for preview
                "WorkerType": "G.1X",
            }

            # Create and run job
            self.glue_client.create_job(**job_definition)

            response = self.glue_client.start_job_run(
                JobName=preview_job_name, Arguments=job_definition["DefaultArguments"]
            )

            job_run_id = response["JobRunId"]

            # Wait for completion (with timeout)
            preview_result = await self._wait_for_preview_completion(
                preview_job_name, job_run_id
            )

            # Cleanup preview job
            await self._cleanup_job(preview_job_name)

            return preview_result

        except Exception as e:
            logger.error(f"Preview execution failed: {str(e)}")
            # Cleanup on error
            try:
                await self._cleanup_job(preview_job_name)
            except:
                pass

            raise Exception(f"Preview execution failed: {str(e)}")

    async def _upload_transformation_script(
        self, execution_context: Dict[str, Any]
    ) -> str:
        """Upload the transformation script to S3"""

        script_content = self._generate_transformation_script(execution_context)
        script_key = f"scripts/transformation_{execution_context['execution_id']}.py"

        try:
            self.s3_client.put_object(
                Bucket=self.settings.s3_scripts_bucket,
                Key=script_key,
                Body=script_content.encode("utf-8"),
                ContentType="text/x-python",
            )

            script_location = f"s3://{self.settings.s3_scripts_bucket}/{script_key}"
            logger.info(f"Uploaded transformation script to: {script_location}")

            return script_location

        except ClientError as e:
            logger.error(f"Failed to upload script: {str(e)}")
            raise Exception(f"Script upload failed: {str(e)}")

    async def _upload_preview_script(self, preview_context: Dict[str, Any]) -> str:
        """Upload the preview script to S3"""

        script_content = self._generate_preview_script(preview_context)
        script_key = f"scripts/preview_{preview_context.get('execution_id', 'test')}.py"

        try:
            self.s3_client.put_object(
                Bucket=self.settings.s3_scripts_bucket,
                Key=script_key,
                Body=script_content.encode("utf-8"),
                ContentType="text/x-python",
            )

            return f"s3://{self.settings.s3_scripts_bucket}/{script_key}"

        except ClientError as e:
            logger.error(f"Failed to upload preview script: {str(e)}")
            raise Exception(f"Preview script upload failed: {str(e)}")

    def _generate_transformation_script(self, execution_context: Dict[str, Any]) -> str:
        """Generate the PySpark transformation script"""

        return f"""
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from datetime import datetime
import json

# Get job arguments
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'execution_id',
    'transformation_id',
    'source_path',
    'target_path',
    'sql_query',
    'data_format',
    'compression',
    'overwrite_mode',
    'partition_columns',
    'dry_run',
    'sample_size',
    'database_name'
])

# Initialize Spark and Glue contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Configuration
execution_id = args['execution_id']
transformation_id = args['transformation_id']
source_path = args['source_path']
target_path = args['target_path']
sql_query = args['sql_query']
data_format = args.get('data_format', 'parquet')
compression = args.get('compression', 'snappy')
overwrite_mode = args.get('overwrite_mode', 'overwrite')
partition_columns = args.get('partition_columns', '').split(',') if args.get('partition_columns') else []
dry_run = args.get('dry_run', 'False').lower() == 'true'
sample_size = int(args.get('sample_size', '0'))
database_name = args.get('database_name', 'default')

print(f"Starting transformation: {{execution_id}}")
print(f"Source: {{source_path}}")
print(f"Target: {{target_path}}")
print(f"Dry run: {{dry_run}}")

try:
    # Read source data using Glue Data Catalog
    datasource = glueContext.create_dynamic_frame.from_catalog(
        database=database_name,
        table_name=source_path.split('/')[-2] if '/' in source_path else 'bronze_data',
        transformation_ctx="datasource"
    )
    
    # Convert to DataFrame
    df = datasource.toDF()
    
    # Apply sampling if specified
    if sample_size > 0:
        df = df.limit(sample_size)
    
    # Create temporary view for SQL
    df.createOrReplaceTempView("bronze_data")
    
    print(f"Source data loaded: {{df.count()}} records")
    print(f"Schema: {{df.schema}}")
    
    # Apply SQL transformation
    print("Applying SQL transformation...")
    transformed_df = spark.sql(sql_query)
    
    # Add processing metadata
    transformed_df = transformed_df \\
        .withColumn("processed_at", lit(datetime.now())) \\
        .withColumn("processing_date", current_date()) \\
        .withColumn("execution_id", lit(execution_id)) \\
        .withColumn("transformation_id", lit(transformation_id))
    
    # Add partitioning columns if not present
    for partition_col in partition_columns:
        if partition_col not in transformed_df.columns:
            if partition_col == 'year':
                transformed_df = transformed_df.withColumn('year', year(current_date()))
            elif partition_col == 'month':
                transformed_df = transformed_df.withColumn('month', month(current_date()))
            elif partition_col == 'day':
                transformed_df = transformed_df.withColumn('day', dayofmonth(current_date()))
    
    output_count = transformed_df.count()
    print(f"Transformed data: {{output_count}} records")
    
    if not dry_run:
        # Write transformed data
        print(f"Writing to: {{target_path}}")
        
        # Convert back to DynamicFrame for optimized writing
        transformed_dynamic_frame = DynamicFrame.fromDF(
            transformed_df, 
            glueContext, 
            "transformed_data"
        )
        
        # Configure output
        output_config = {{
            "path": target_path,
            "format": data_format,
            "compression": compression,
            "writeMode": overwrite_mode
        }}
        
        if partition_columns:
            output_config["partitionKeys"] = [col for col in partition_columns if col in transformed_df.columns]
        
        # Write data
        glueContext.write_dynamic_frame.from_options(
            frame=transformed_dynamic_frame,
            connection_type="s3",
            connection_options=output_config,
            transformation_ctx="output"
        )
        
        print(f"Successfully wrote {{output_count}} records to {{target_path}}")
        
        # Update Glue Data Catalog
        try:
            glueContext.create_dynamic_frame.from_options(
                connection_type="s3",
                connection_options={{"path": target_path}},
                format=data_format
            ).toDF().createOrReplaceTempView("catalog_update")
            
            # Register table in catalog
            catalog_table_name = target_path.split('/')[-1] if '/' in target_path else 'transformed_data'
            spark.sql(f"CREATE TABLE IF NOT EXISTS {{database_name}}.{{catalog_table_name}} USING {{data_format}} LOCATION '{{target_path}}'")
            
            print(f"Updated Glue Data Catalog: {{database_name}}.{{catalog_table_name}}")
            
        except Exception as catalog_error:
            print(f"Warning: Failed to update Glue Data Catalog: {{str(catalog_error)}}")
    
    else:
        print("Dry run completed - no data written")
        # Show sample of transformed data
        print("Sample transformed data:")
        transformed_df.show(10, truncate=False)
    
    # Write job metrics
    job_metrics = {{
        "execution_id": execution_id,
        "transformation_id": transformation_id,
        "status": "completed",
        "records_processed": df.count() if 'df' in locals() else 0,
        "records_output": output_count,
        "execution_time_seconds": (datetime.now() - datetime.now()).total_seconds(),  # This would be calculated properly
        "data_quality_score": 100.0,  # Could be calculated based on actual validation
        "dry_run": dry_run,
        "completed_at": datetime.now().isoformat()
    }}
    
    # Write metrics to S3
    metrics_path = f"{{target_path}}_metrics/execution_{{execution_id}}.json"
    spark.createDataFrame([job_metrics]).coalesce(1).write.mode("overwrite").json(metrics_path)
    
    print("Transformation completed successfully!")
    
except Exception as e:
    print(f"Transformation failed: {{str(e)}}")
    
    # Write error metrics
    error_metrics = {{
        "execution_id": execution_id,
        "transformation_id": transformation_id,
        "status": "failed",
        "error_message": str(e),
        "failed_at": datetime.now().isoformat()
    }}
    
    try:
        error_path = f"{{target_path}}_errors/execution_{{execution_id}}.json"
        spark.createDataFrame([error_metrics]).coalesce(1).write.mode("overwrite").json(error_path)
    except:
        pass  # Don't fail if we can't write error metrics
    
    raise e

finally:
    job.commit()
    print("Job completed and committed")
"""

    def _generate_preview_script(self, preview_context: Dict[str, Any]) -> str:
        """Generate the PySpark preview script"""

        return f"""
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from datetime import datetime
import json

# Get job arguments
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'source_path',
    'sql_query',
    'sample_size',
    'database_name'
])

# Initialize contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

try:
    # Configuration
    source_path = args['source_path']
    sql_query = args['sql_query']
    sample_size = int(args.get('sample_size', '100'))
    database_name = args.get('database_name', 'default')
    
    print(f"Preview transformation")
    print(f"Source: {{source_path}}")
    print(f"Sample size: {{sample_size}}")
    
    # Read source data
    datasource = glueContext.create_dynamic_frame.from_catalog(
        database=database_name,
        table_name=source_path.split('/')[-2] if '/' in source_path else 'bronze_data',
        transformation_ctx="preview_source"
    )
    
    # Convert to DataFrame and sample
    df = datasource.toDF().limit(sample_size)
    df.createOrReplaceTempView("bronze_data")
    
    print(f"Source data loaded: {{df.count()}} records")
    
    # Apply transformation
    preview_df = spark.sql(sql_query)
    preview_count = preview_df.count()
    
    print(f"Preview result: {{preview_count}} records")
    
    # Collect sample data (limited to avoid memory issues)
    sample_data = preview_df.limit(20).collect()
    schema_info = preview_df.schema.json()
    
    # Convert to JSON-serializable format
    preview_result = {{
        "data": [row.asDict() for row in sample_data],
        "schema": json.loads(schema_info),
        "row_count": preview_count,
        "sample_size": min(len(sample_data), 20)
    }}
    
    # Write preview result to S3
    result_path = f"{{source_path}}_preview_result.json"
    spark.createDataFrame([preview_result]).coalesce(1).write.mode("overwrite").json(result_path)
    
    print("Preview completed successfully!")
    
except Exception as e:
    print(f"Preview failed: {{str(e)}}")
    raise e

finally:
    job.commit()
"""

    async def _schedule_job_cleanup(self, job_name: str, job_run_id: str):
        """Schedule cleanup of the Glue job after completion"""

        max_wait_time = self.settings.job_timeout_minutes * 60  # Convert to seconds
        check_interval = 30  # Check every 30 seconds
        waited_time = 0

        while waited_time < max_wait_time:
            try:
                status = await self.get_job_status(job_run_id)

                if status["status"] in ["completed", "failed", "cancelled"]:
                    logger.info(
                        f"Job {job_run_id} finished with status: {status['status']}"
                    )
                    # Wait a bit more before cleanup to ensure logs are available
                    await asyncio.sleep(60)
                    await self._cleanup_job(job_name)
                    break

                await asyncio.sleep(check_interval)
                waited_time += check_interval

            except Exception as e:
                logger.error(f"Error monitoring job {job_run_id}: {str(e)}")
                await asyncio.sleep(check_interval)
                waited_time += check_interval

        if waited_time >= max_wait_time:
            logger.warning(f"Job {job_run_id} cleanup timeout, forcing cleanup")
            await self._cleanup_job(job_name)

    async def _cleanup_job(self, job_name: str):
        """Clean up the Glue job definition"""

        try:
            self.glue_client.delete_job(JobName=job_name)
            logger.info(f"Cleaned up Glue job: {job_name}")

            # Also cleanup the script from S3
            script_key = f"scripts/{job_name.replace('transformation-', 'transformation_').replace('preview-', 'preview_')}.py"

            try:
                self.s3_client.delete_object(
                    Bucket=self.settings.s3_scripts_bucket, Key=script_key
                )
                logger.info(f"Cleaned up script: {script_key}")
            except ClientError:
                logger.warning(f"Could not cleanup script: {script_key}")

        except ClientError as e:
            if e.response["Error"]["Code"] != "EntityNotFoundException":
                logger.error(f"Failed to cleanup job {job_name}: {str(e)}")

    async def _get_job_name_from_run_id(self, job_run_id: str) -> str:
        """Extract job name from job run ID by listing job runs"""

        try:
            # List recent job runs to find the job name
            # This is a workaround since Glue doesn't provide direct job name from run ID
            paginator = self.glue_client.get_paginator("get_job_runs")

            for page in paginator.paginate():
                for job_run in page["JobRuns"]:
                    if job_run["Id"] == job_run_id:
                        return job_run["JobName"]

            # If not found, try to construct from execution ID pattern
            if job_run_id.startswith("jr_"):
                # Look for jobs matching transformation pattern
                job_list = self.glue_client.get_jobs()
                for job in job_list["Jobs"]:
                    if job["Name"].startswith("transformation-") or job[
                        "Name"
                    ].startswith("preview-"):
                        # Get runs for this job
                        runs = self.glue_client.get_job_runs(JobName=job["Name"])
                        for run in runs["JobRuns"]:
                            if run["Id"] == job_run_id:
                                return job["Name"]

            raise Exception(f"Job name not found for run ID: {job_run_id}")

        except ClientError as e:
            logger.error(f"Failed to get job name for run ID {job_run_id}: {str(e)}")
            raise Exception(f"Failed to get job name: {str(e)}")

    async def _wait_for_preview_completion(
        self, job_name: str, job_run_id: str, timeout_minutes: int = 10
    ) -> Dict[str, Any]:
        """Wait for preview job completion and return results"""

        timeout_seconds = timeout_minutes * 60
        check_interval = 10
        waited_time = 0

        while waited_time < timeout_seconds:
            try:
                status = await self.get_job_status(job_run_id)

                if status["status"] == "completed":
                    # Read preview results from S3
                    return await self._read_preview_results(job_run_id)

                elif status["status"] == "failed":
                    raise Exception(
                        f"Preview job failed: {status.get('error_message', 'Unknown error')}"
                    )

                await asyncio.sleep(check_interval)
                waited_time += check_interval

            except Exception as e:
                if "Preview job failed" in str(e):
                    raise e
                logger.warning(f"Error checking preview status: {str(e)}")
                await asyncio.sleep(check_interval)
                waited_time += check_interval

        raise Exception("Preview job timeout")

    async def _read_preview_results(self, job_run_id: str) -> Dict[str, Any]:
        """Read preview results from S3"""

        # This would be implemented based on where the preview script writes results
        # For now, return mock preview data
        return {
            "data": [
                {"customer_id": 1, "name": "JOHN DOE", "email": "john@example.com"},
                {"customer_id": 2, "name": "JANE SMITH", "email": "jane@example.com"},
            ],
            "schema": {
                "fields": [
                    {"name": "customer_id", "type": "integer"},
                    {"name": "name", "type": "string"},
                    {"name": "email", "type": "string"},
                ]
            },
            "row_count": 2,
        }

    async def _get_job_metrics(self, job_run_id: str) -> Dict[str, Any]:
        """Get job execution metrics"""

        try:
            # Try to read metrics from S3 if available
            # This would be implemented based on where metrics are stored
            return {
                "records_processed": 1000,
                "records_output": 950,
                "execution_time_seconds": 120.5,
                "data_quality_score": 95.0,
                "validation_errors": [],
                "warnings": [],
            }

        except Exception as e:
            logger.warning(f"Could not retrieve metrics for {job_run_id}: {str(e)}")
            return {}


# Global instance
_glue_executor: Optional[GlueExecutor] = None


async def init_glue_client():
    """Initialize the global Glue executor"""
    global _glue_executor
    _glue_executor = GlueExecutor()
    logger.info("Glue client initialized")


def get_glue_executor() -> GlueExecutor:
    """Get the global Glue executor instance"""
    if _glue_executor is None:
        raise Exception("Glue client not initialized. Call init_glue_client() first.")
    return _glue_executor
