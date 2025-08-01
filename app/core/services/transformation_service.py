"""
Transformation service - Core business logic for data transformations
Enhanced with complete PySpark job lifecycle management
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.transformation import (
    CustomerDataTransformation,
    TransformationCreate,
    TransformationExecuteRequest,
    TransformationExecuteResponse,
    TransformationHistory,
    TransformationList,
    TransformationResponse,
    TransformationStatus,
    TransformationType,
    TransformationUpdate,
    TransformationMetrics,
)
from app.infrastructure.database.repositories.transformation_repository import (
    TransformationRepository,
)
from app.infrastructure.aws.glue_client import GlueExecutor
from app.infrastructure.aws.s3_client import S3Client
from app.utils.logging import get_logger
from app.utils.validators import SQLValidator

logger = get_logger(__name__)


class TransformationService:
    """Service for managing data transformations with complete PySpark lifecycle"""

    def __init__(
        self,
        db_session: AsyncSession,
        transformation_repo: TransformationRepository,
        s3_client: S3Client,
        glue_executor: GlueExecutor,
        sql_validator: SQLValidator,
    ):
        self.db_session = db_session
        self.transformation_repo = transformation_repo
        self.s3_client = s3_client
        self.glue_executor = glue_executor
        self.sql_validator = sql_validator

    async def create_transformation(
        self, transformation: TransformationCreate, created_by: str
    ) -> TransformationResponse:
        """Create a new transformation definition"""

        # Validate SQL query
        validation_result = await self.sql_validator.validate_query(
            transformation.query
        )
        if not validation_result["is_valid"]:
            raise ValueError(f"Invalid SQL query: {validation_result['errors']}")

        # Check if name already exists
        existing = await self.transformation_repo.get_by_name(transformation.name)
        if existing:
            raise ValueError(
                f"Transformation with name '{transformation.name}' already exists"
            )

        # Validate source path exists
        source_exists = await self.s3_client.path_exists(
            transformation.config.source_path
        )
        if not source_exists:
            logger.warning(
                f"Source path may not exist: {transformation.config.source_path}"
            )

        # Auto-sync source data to Glue catalog if needed
        await self._ensure_glue_catalog_sync(
            transformation.config.source_path, "bronze_data"
        )

        # Create transformation record
        transformation_data = transformation.dict()
        transformation_data.update(
            {
                "id": uuid4(),
                "status": TransformationStatus.DRAFT,
                "created_by": created_by,
                "created_at": datetime.utcnow(),
                "modified_at": datetime.utcnow(),
            }
        )

        result = await self.transformation_repo.create(transformation_data)

        logger.info(f"Created transformation: {result.id}", user=created_by)
        return TransformationResponse.from_orm(result)

    async def execute_transformation(
        self,
        execute_request: TransformationExecuteRequest,
        transformation: TransformationResponse,
        background_tasks: BackgroundTasks,
        executed_by: str,
    ) -> TransformationExecuteResponse:
        """Execute a transformation with complete PySpark lifecycle"""

        execution_id = uuid4()

        logger.info(f"Starting transformation execution: {execution_id}")

        # Ensure source data is cataloged
        await self._ensure_glue_catalog_sync(
            transformation.config.source_path,
            self._extract_table_name(transformation.config.source_path),
        )

        # Prepare execution context with all necessary parameters
        execution_context = {
            "execution_id": str(execution_id),
            "transformation_id": str(transformation.id),
            "transformation_name": transformation.name,
            "query": transformation.query,
            "source_path": transformation.config.source_path,
            "target_path": transformation.config.target_path,
            "partition_columns": transformation.config.partition_columns or [],
            "data_format": transformation.config.data_format,
            "compression": transformation.config.compression,
            "overwrite_mode": transformation.config.overwrite_mode,
            "dry_run": execute_request.dry_run,
            "sample_size": execute_request.sample_size or 0,
            "executed_by": executed_by,
            "validation_rules": transformation.config.validation_rules,
            "column_operations": transformation.column_operations,
        }

        # Add execution config overrides if provided
        if execute_request.execution_config:
            execution_context.update(execute_request.execution_config)

        try:
            # Submit job to Glue (creates PySpark job, executes, and schedules cleanup)
            job_id = await self.glue_executor.submit_job(execution_context)

            # Store execution record in database
            execution_record = {
                "execution_id": execution_id,
                "transformation_id": transformation.id,
                "job_id": job_id,
                "status": "submitted",
                "executed_by": executed_by,
                "executed_at": datetime.utcnow(),
                "execution_config": execution_context,
                "dry_run": execute_request.dry_run,
            }

            await self.transformation_repo.create_execution(execution_record)

            # Start background monitoring that will handle job lifecycle
            background_tasks.add_task(
                self._monitor_job_lifecycle,
                execution_id,
                job_id,
                transformation.id,
                execution_context,
            )

            logger.info(
                f"Transformation execution submitted: {execution_id} (Job: {job_id})"
            )

            return TransformationExecuteResponse(
                execution_id=execution_id,
                transformation_id=transformation.id,
                status="submitted",
                message=f"PySpark transformation job created and submitted to AWS Glue",
                job_id=job_id,
                dry_run=execute_request.dry_run,
            )

        except Exception as e:
            logger.error(f"Failed to execute transformation: {str(e)}")

            # Update execution record with error
            try:
                await self.transformation_repo.update_execution(
                    execution_id,
                    {
                        "status": "failed",
                        "error_message": str(e),
                        "updated_at": datetime.utcnow(),
                    },
                )
            except:
                pass  # Don't fail if we can't update the record

            raise ValueError(f"Transformation execution failed: {str(e)}")

    async def preview_transformation(
        self, transformation: TransformationResponse, sample_size: int = 100
    ) -> Dict[str, Any]:
        """Generate a preview of transformation results using PySpark"""

        logger.info(f"Generating preview for transformation: {transformation.id}")

        # Ensure source data is cataloged
        await self._ensure_glue_catalog_sync(
            transformation.config.source_path,
            self._extract_table_name(transformation.config.source_path),
        )

        # Prepare preview context
        preview_context = {
            "execution_id": str(uuid4()),
            "transformation_id": str(transformation.id),
            "query": transformation.query,
            "source_path": transformation.config.source_path,
            "sample_size": sample_size,
        }

        try:
            # Execute preview using Glue (creates temporary PySpark job)
            start_time = datetime.utcnow()
            preview_result = await self.glue_executor.execute_preview(preview_context)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            preview_result["execution_time_ms"] = execution_time

            logger.info(f"Preview completed in {execution_time}ms")
            return preview_result

        except Exception as e:
            logger.error(f"Preview generation failed: {str(e)}")
            raise ValueError(f"Preview generation failed: {str(e)}")

    async def validate_transformation(
        self, transformation: TransformationResponse
    ) -> Dict[str, Any]:
        """Validate a transformation without executing it"""

        # SQL validation
        sql_result = await self.sql_validator.validate_query(transformation.query)

        # Check source data availability
        source_exists = await self.s3_client.path_exists(
            transformation.config.source_path
        )

        # Estimate cost and runtime
        estimated_cost = await self._estimate_execution_cost(transformation)
        estimated_runtime = await self._estimate_execution_time(transformation)

        errors = []
        warnings = []

        if not sql_result["is_valid"]:
            errors.extend(sql_result["errors"])

        if not source_exists:
            warnings.append(
                f"Source path may not exist: {transformation.config.source_path}"
            )

        if sql_result.get("warnings"):
            warnings.extend(sql_result["warnings"])

        # Validate Glue catalog access
        try:
            table_name = self._extract_table_name(transformation.config.source_path)
            # This would check if the table exists in Glue catalog
            warnings.append(
                f"Ensure Glue catalog table '{table_name}' exists for source data"
            )
        except Exception as e:
            warnings.append(f"Glue catalog validation: {str(e)}")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "estimated_cost": estimated_cost,
            "estimated_runtime": estimated_runtime,
        }

    async def _monitor_job_lifecycle(
        self,
        execution_id: UUID,
        job_id: str,
        transformation_id: UUID,
        execution_context: Dict[str, Any],
    ) -> None:
        """Monitor complete PySpark job lifecycle: creation -> execution -> completion -> cleanup"""

        max_attempts = 720  # 60 minutes with 5-second intervals
        attempt = 0

        logger.info(f"Starting job lifecycle monitoring for execution: {execution_id}")

        while attempt < max_attempts:
            try:
                # Get job status from Glue
                job_status = await self.glue_executor.get_job_status(job_id)

                # Update execution record
                update_data = {
                    "status": job_status["status"],
                    "updated_at": datetime.utcnow(),
                }

                if job_status.get("error_message"):
                    update_data["error_message"] = job_status["error_message"]

                if job_status.get("metrics"):
                    update_data["metrics"] = job_status["metrics"]

                await self.transformation_repo.update_execution(
                    execution_id, update_data
                )

                # Handle different job states
                if job_status["status"] == "completed":
                    logger.info(f"Job {job_id} completed successfully")
                    await self._handle_job_completion(
                        execution_id, job_id, execution_context
                    )
                    break

                elif job_status["status"] == "failed":
                    logger.error(
                        f"Job {job_id} failed: {job_status.get('error_message', 'Unknown error')}"
                    )
                    await self._handle_job_failure(
                        execution_id,
                        job_id,
                        execution_context,
                        job_status.get("error_message"),
                    )
                    break

                elif job_status["status"] == "cancelled":
                    logger.info(f"Job {job_id} was cancelled")
                    break

                # Wait before next check
                import asyncio

                await asyncio.sleep(5)
                attempt += 1

            except Exception as e:
                logger.error(f"Error monitoring execution {execution_id}: {str(e)}")
                attempt += 1
                import asyncio

                await asyncio.sleep(5)

        if attempt >= max_attempts:
            logger.warning(f"Monitoring timeout for execution {execution_id}")
            await self.transformation_repo.update_execution(
                execution_id,
                {
                    "status": "timeout",
                    "error_message": "Job monitoring timeout",
                    "updated_at": datetime.utcnow(),
                },
            )

        logger.info(f"Job lifecycle monitoring completed for execution: {execution_id}")

    async def _handle_job_completion(
        self, execution_id: UUID, job_id: str, execution_context: Dict[str, Any]
    ) -> None:
        """Handle successful job completion"""

        try:
            # Sync output data to Glue catalog
            target_path = execution_context["target_path"]
            target_table_name = self._extract_table_name(target_path)
            data_format = execution_context.get("data_format", "parquet")

            await self._ensure_glue_catalog_sync(
                target_path, target_table_name, data_format
            )

            # Read and store job metrics if available
            metrics = await self._collect_job_metrics(job_id, execution_context)

            # Update execution record with final metrics
            await self.transformation_repo.update_execution(
                execution_id,
                {
                    "status": "completed",
                    "metrics": metrics,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
            )

            logger.info(
                f"Job completion handled successfully for execution: {execution_id}"
            )

        except Exception as e:
            logger.error(f"Error handling job completion for {execution_id}: {str(e)}")

    async def _handle_job_failure(
        self,
        execution_id: UUID,
        job_id: str,
        execution_context: Dict[str, Any],
        error_message: str = None,
    ) -> None:
        """Handle job failure"""

        try:
            # Collect any available metrics/logs
            failure_info = await self._collect_failure_info(job_id, execution_context)

            # Update execution record
            await self.transformation_repo.update_execution(
                execution_id,
                {
                    "status": "failed",
                    "error_message": error_message or "Job execution failed",
                    "failure_info": failure_info,
                    "failed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
            )

            logger.info(f"Job failure handled for execution: {execution_id}")

        except Exception as e:
            logger.error(f"Error handling job failure for {execution_id}: {str(e)}")

    async def _ensure_glue_catalog_sync(
        self, s3_path: str, table_name: str, data_format: str = "parquet"
    ) -> None:
        """Ensure S3 data is synced to Glue Data Catalog"""

        try:
            database_name = "datalake_db"  # Default database name

            # Sync to Glue catalog
            success = await self.s3_client.sync_to_glue_catalog(
                database_name=database_name,
                table_name=table_name,
                s3_path=s3_path,
                data_format=data_format,
            )

            if success:
                logger.info(
                    f"Successfully synced {s3_path} to Glue catalog as {database_name}.{table_name}"
                )
            else:
                logger.warning(f"Failed to sync {s3_path} to Glue catalog")

        except Exception as e:
            logger.error(f"Error syncing to Glue catalog: {str(e)}")

    def _extract_table_name(self, s3_path: str) -> str:
        """Extract table name from S3 path"""

        # Remove leading/trailing slashes and extract last meaningful part
        clean_path = s3_path.strip("/")
        parts = clean_path.split("/")

        # Use the last non-empty part as table name
        table_name = parts[-1] if parts else "data"

        # Clean table name for Glue compatibility
        table_name = table_name.replace("-", "_").replace(".", "_").lower()

        return table_name

    async def _collect_job_metrics(
        self, job_id: str, execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect job execution metrics"""

        try:
            # Get metrics from Glue job
            glue_metrics = await self.glue_executor._get_job_metrics(job_id)

            # Try to read metrics written by the PySpark job
            target_path = execution_context["target_path"]
            metrics_path = f"{target_path}_metrics/execution_{execution_context['execution_id']}.json"

            try:
                job_metrics = await self.s3_client.read_json_object(
                    metrics_path.lstrip("/")
                )
                # Merge Glue metrics with job-specific metrics
                glue_metrics.update(job_metrics)
            except Exception:
                logger.warning(
                    f"Could not read job-specific metrics from {metrics_path}"
                )

            return glue_metrics

        except Exception as e:
            logger.error(f"Error collecting job metrics: {str(e)}")
            return {
                "records_processed": 0,
                "records_output": 0,
                "execution_time_seconds": 0,
                "data_quality_score": 0,
                "error": str(e),
            }

    async def _collect_failure_info(
        self, job_id: str, execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect information about job failure"""

        try:
            # Try to read error information written by the PySpark job
            target_path = execution_context["target_path"]
            error_path = f"{target_path}_errors/execution_{execution_context['execution_id']}.json"

            try:
                error_info = await self.s3_client.read_json_object(
                    error_path.lstrip("/")
                )
                return error_info
            except Exception:
                logger.warning(f"Could not read job error info from {error_path}")

            # Return basic failure info
            return {
                "job_id": job_id,
                "execution_id": execution_context["execution_id"],
                "failed_at": datetime.utcnow().isoformat(),
                "source_path": execution_context["source_path"],
                "target_path": execution_context["target_path"],
            }

        except Exception as e:
            logger.error(f"Error collecting failure info: {str(e)}")
            return {"error": str(e)}

    async def _estimate_execution_cost(
        self, transformation: TransformationResponse
    ) -> float:
        """Estimate execution cost in USD"""

        try:
            source_size_gb = await self.s3_client.get_path_size(
                transformation.config.source_path
            )

            # Glue pricing: $0.44 per DPU-hour
            # Estimate DPU hours based on data size and query complexity
            base_dpu_hours = source_size_gb * 0.1  # ~0.1 DPU hours per GB

            query_complexity_multiplier = 1.0

            # Analyze query complexity
            query_upper = transformation.query.upper()
            if "JOIN" in query_upper:
                query_complexity_multiplier *= 2.0
            if "GROUP BY" in query_upper:
                query_complexity_multiplier *= 1.5
            if "WINDOW" in query_upper or "OVER" in query_upper:
                query_complexity_multiplier *= 2.5
            if "ORDER BY" in query_upper:
                query_complexity_multiplier *= 1.3

            estimated_dpu_hours = base_dpu_hours * query_complexity_multiplier
            estimated_cost = estimated_dpu_hours * 0.44  # $0.44 per DPU-hour

            return round(max(0.44, estimated_cost), 2)  # Minimum 1 DPU-hour

        except Exception as e:
            logger.warning(f"Could not estimate cost: {str(e)}")
            return 0.44  # Default minimum cost

    async def _estimate_execution_time(
        self, transformation: TransformationResponse
    ) -> int:
        """Estimate execution time in minutes"""

        try:
            source_size_gb = await self.s3_client.get_path_size(
                transformation.config.source_path
            )

            # Base processing rate varies by operation type
            if transformation.transformation_type == TransformationType.AGGREGATE:
                base_time_per_gb = 2.0  # Aggregations are slower
            elif transformation.transformation_type == TransformationType.JOIN:
                base_time_per_gb = 3.0  # Joins are slowest
            else:
                base_time_per_gb = 1.0  # Simple transformations

            query_complexity_multiplier = 1.0

            query_upper = transformation.query.upper()
            if "JOIN" in query_upper:
                query_complexity_multiplier *= 2.5
            if "GROUP BY" in query_upper:
                query_complexity_multiplier *= 2.0
            if "ORDER BY" in query_upper:
                query_complexity_multiplier *= 1.5
            if "DISTINCT" in query_upper:
                query_complexity_multiplier *= 1.3

            estimated_minutes = (
                source_size_gb * base_time_per_gb * query_complexity_multiplier
            )

            # Add overhead for job startup/teardown
            estimated_minutes += 3  # 3 minute overhead

            return max(5, int(estimated_minutes))  # Minimum 5 minutes

        except Exception as e:
            logger.warning(f"Could not estimate execution time: {str(e)}")
            return 10  # Default 10 minutes

    async def list_transformations(
        self, page: int = 1, size: int = 20, filters: Optional[Dict[str, Any]] = None
    ) -> TransformationList:
        """List transformations with pagination and filtering"""

        filters = filters or {}
        offset = (page - 1) * size

        transformations, total = await self.transformation_repo.list_with_filters(
            offset=offset, limit=size, filters=filters
        )

        items = [TransformationResponse.from_orm(t) for t in transformations]
        pages = (total + size - 1) // size

        return TransformationList(
            items=items, total=total, page=page, size=size, pages=pages
        )

    async def get_transformation(
        self, transformation_id: UUID
    ) -> Optional[TransformationResponse]:
        """Get a transformation by ID"""

        transformation = await self.transformation_repo.get_by_id(transformation_id)
        if not transformation:
            return None

        return TransformationResponse.from_orm(transformation)

    async def update_transformation(
        self,
        transformation_id: UUID,
        update_data: TransformationUpdate,
        modified_by: str,
    ) -> TransformationResponse:
        """Update an existing transformation"""

        # Get existing transformation
        existing = await self.transformation_repo.get_by_id(transformation_id)
        if not existing:
            raise ValueError(f"Transformation {transformation_id} not found")

        # Validate SQL query if provided
        if update_data.query:
            validation_result = await self.sql_validator.validate_query(
                update_data.query
            )
            if not validation_result["is_valid"]:
                raise ValueError(f"Invalid SQL query: {validation_result['errors']}")

        # Check name uniqueness if provided
        if update_data.name and update_data.name != existing.name:
            name_exists = await self.transformation_repo.get_by_name(update_data.name)
            if name_exists:
                raise ValueError(
                    f"Transformation with name '{update_data.name}' already exists"
                )

        # Update transformation
        update_dict = update_data.dict(exclude_unset=True)
        update_dict.update(
            {
                "modified_by": modified_by,
                "modified_at": datetime.utcnow(),
            }
        )

        result = await self.transformation_repo.update(transformation_id, update_dict)

        logger.info(f"Updated transformation: {transformation_id}", user=modified_by)
        return TransformationResponse.from_orm(result)

    async def delete_transformation(
        self, transformation_id: UUID, deleted_by: str
    ) -> None:
        """Soft delete a transformation"""

        update_data = {
            "status": TransformationStatus.INACTIVE,
            "modified_by": deleted_by,
            "modified_at": datetime.utcnow(),
        }

        await self.transformation_repo.update(transformation_id, update_data)
        logger.info(f"Deleted transformation: {transformation_id}", user=deleted_by)

    async def get_transformation_history(
        self, transformation_id: UUID, limit: int = 50
    ) -> List[TransformationHistory]:
        """Get execution history for a transformation"""

        executions = await self.transformation_repo.get_execution_history(
            transformation_id, limit=limit
        )

        return [
            TransformationHistory(
                execution_id=exec.execution_id,
                transformation_id=exec.transformation_id,
                executed_at=exec.executed_at,
                status=exec.status,
                metrics=(
                    TransformationMetrics(**exec.metrics)
                    if exec.metrics
                    else TransformationMetrics()
                ),
                error_message=exec.error_message,
                execution_config=exec.execution_config or {},
            )
            for exec in executions
        ]

    async def get_transformation_stats(self) -> Dict[str, Any]:
        """Get summary statistics for transformations"""

        stats = await self.transformation_repo.get_stats()

        # Calculate additional metrics
        recent_executions = await self.transformation_repo.get_recent_executions(
            since=datetime.utcnow() - timedelta(hours=24)
        )

        success_count = sum(
            1 for exec in recent_executions if exec.status == "completed"
        )
        success_rate = (
            (success_count / len(recent_executions) * 100) if recent_executions else 0
        )

        avg_execution_time = (
            sum(
                exec.metrics.get("execution_time_seconds", 0)
                for exec in recent_executions
                if exec.metrics
            )
            / len(recent_executions)
            if recent_executions
            else 0
        )

        return {
            "total": stats["total_transformations"],
            "active": stats["active_transformations"],
            "executions_24h": len(recent_executions),
            "success_rate": round(success_rate, 2),
            "avg_execution_time": round(avg_execution_time, 2),
            "most_used": stats["most_used_transformations"],
            "types_breakdown": stats["transformation_types"],
        }

    async def create_customer_transformation(
        self,
        base_transformation: TransformationCreate,
        customer_config: CustomerDataTransformation,
        created_by: str,
    ) -> TransformationResponse:
        """Create a customer-specific transformation with PII handling"""

        # Apply customer-specific query modifications
        enhanced_query = await self._apply_customer_transformations(
            base_transformation.query, customer_config
        )

        # Update the base transformation with enhanced query
        base_transformation.query = enhanced_query
        base_transformation.tags.extend(
            ["customer", "pii", customer_config.pii_handling]
        )

        # Add customer-specific metadata to config
        base_transformation.config.validation_rules.extend(
            [
                {
                    "column": field,
                    "rule_type": "customer_pii",
                    "parameters": {"handling": customer_config.pii_handling},
                }
                for field in customer_config.customer_fields
            ]
        )

        return await self.create_transformation(base_transformation, created_by)

    async def duplicate_transformation(
        self, transformation_id: UUID, new_name: str, created_by: str
    ) -> TransformationResponse:
        """Duplicate an existing transformation"""

        original = await self.transformation_repo.get_by_id(transformation_id)
        if not original:
            raise ValueError(f"Transformation {transformation_id} not found")

        # Check new name doesn't exist
        existing = await self.transformation_repo.get_by_name(new_name)
        if existing:
            raise ValueError(f"Transformation with name '{new_name}' already exists")

        # Create duplicate
        duplicate_data = {
            "id": uuid4(),
            "name": new_name,
            "description": f"Copy of {original.description or original.name}",
            "transformation_type": original.transformation_type,
            "query": original.query,
            "column_operations": original.column_operations,
            "config": original.config,
            "tags": original.tags + ["duplicate"],
            "status": TransformationStatus.DRAFT,
            "version": "1.0.0",
            "created_by": created_by,
            "created_at": datetime.utcnow(),
            "modified_at": datetime.utcnow(),
        }

        result = await self.transformation_repo.create(duplicate_data)

        logger.info(
            f"Duplicated transformation: {transformation_id} -> {result.id}",
            user=created_by,
        )
        return TransformationResponse.from_orm(result)

    async def _apply_customer_transformations(
        self, base_query: str, customer_config: CustomerDataTransformation
    ) -> str:
        """Apply customer-specific transformations to the base query"""

        # Parse and modify query based on customer configuration
        modified_query = base_query

        # Apply PII handling
        if customer_config.pii_handling == "mask":
            # Add masking functions for PII fields
            pii_fields = ["email", "phone", "ssn", "credit_card"]
            for field in pii_fields:
                if field in customer_config.customer_fields:
                    if "email" in field.lower():
                        modified_query = modified_query.replace(
                            f"SELECT {field}",
                            f"SELECT CONCAT(LEFT({field}, 3), '***@', SUBSTRING_INDEX({field}, '@', -1)) as {field}",
                        )
                    elif "phone" in field.lower():
                        modified_query = modified_query.replace(
                            f"SELECT {field}",
                            f"SELECT CONCAT('***-***-', RIGHT({field}, 4)) as {field}",
                        )

        elif customer_config.pii_handling == "remove":
            # Remove PII fields from SELECT clause
            pii_fields = ["email", "phone", "ssn", "credit_card", "address"]
            for field in pii_fields:
                if field in customer_config.customer_fields:
                    # This is a simplified approach - in production, use a proper SQL parser
                    modified_query = modified_query.replace(f", {field}", "")
                    modified_query = modified_query.replace(f"{field},", "")

        # Apply data retention filter
        if customer_config.data_retention_days:
            retention_date = datetime.utcnow() - timedelta(
                days=customer_config.data_retention_days
            )
            retention_filter = (
                f"AND created_date >= '{retention_date.strftime('%Y-%m-%d')}'"
            )

            # Add WHERE clause or extend existing one
            if "WHERE" in modified_query.upper():
                modified_query = modified_query.replace(
                    "WHERE", f"WHERE {retention_filter.replace('AND ', '')} AND"
                )
            else:
                modified_query = (
                    f"{modified_query} WHERE {retention_filter.replace('AND ', '')}"
                )

        # Apply anonymization rules
        for rule in customer_config.anonymization_rules:
            field = rule["field"]
            method = rule["method"]

            if method == "domain_mask" and "email" in field.lower():
                modified_query = modified_query.replace(
                    field, f"CONCAT(LEFT({field}, 3), '***@example.com') as {field}"
                )
            elif method == "partial_mask":
                modified_query = modified_query.replace(
                    field,
                    f"CONCAT(LEFT({field}, 2), REPEAT('*', LENGTH({field}) - 4), RIGHT({field}, 2)) as {field}",
                )

        return modified_query
