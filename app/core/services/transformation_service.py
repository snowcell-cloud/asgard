"""
Transformation service - Core business logic for data transformations
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
from app.infrastructure.aws.emr_client import EMRExecutor
from app.infrastructure.aws.s3_client import S3Client
from app.utils.logging import get_logger
from app.utils.validators import SQLValidator

logger = get_logger(__name__)


class TransformationService:
    """Service for managing data transformations"""

    def __init__(
        self,
        db_session: AsyncSession,
        transformation_repo: TransformationRepository,
        s3_client: S3Client,
        glue_executor: GlueExecutor,
        emr_executor: EMRExecutor,
        sql_validator: SQLValidator,
    ):
        self.db_session = db_session
        self.transformation_repo = transformation_repo
        self.s3_client = s3_client
        self.glue_executor = glue_executor
        self.emr_executor = emr_executor
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

    async def execute_transformation(
        self,
        execute_request: TransformationExecuteRequest,
        transformation: TransformationResponse,
        background_tasks: BackgroundTasks,
        executed_by: str,
    ) -> TransformationExecuteResponse:
        """Execute a transformation"""

        execution_id = uuid4()

        # Determine execution engine
        engine = (
            execute_request.execution_config.get("engine", "glue")
            if execute_request.execution_config
            else "glue"
        )

        # Prepare execution context
        execution_context = {
            "execution_id": str(execution_id),
            "transformation_id": str(transformation.id),
            "query": transformation.query,
            "source_path": transformation.config.source_path,
            "target_path": transformation.config.target_path,
            "partition_columns": transformation.config.partition_columns,
            "data_format": transformation.config.data_format,
            "compression": transformation.config.compression,
            "overwrite_mode": transformation.config.overwrite_mode,
            "dry_run": execute_request.dry_run,
            "sample_size": execute_request.sample_size,
            "executed_by": executed_by,
        }

        # Override with execution config if provided
        if execute_request.execution_config:
            execution_context.update(execute_request.execution_config)

        # Submit job
        if engine == "glue":
            job_id = await self.glue_executor.submit_job(execution_context)
        elif engine == "emr":
            job_id = await self.emr_executor.submit_job(execution_context)
        else:
            raise ValueError(f"Unsupported execution engine: {engine}")

        # Store execution record
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

        # Start background monitoring
        background_tasks.add_task(
            self._monitor_execution, execution_id, job_id, engine, transformation.id
        )

        return TransformationExecuteResponse(
            execution_id=execution_id,
            transformation_id=transformation.id,
            status="submitted",
            message=f"Transformation execution started with {engine}",
            job_id=job_id,
            dry_run=execute_request.dry_run,
        )

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

        # Estimate cost and runtime (simplified)
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

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "estimated_cost": estimated_cost,
            "estimated_runtime": estimated_runtime,
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

    async def preview_transformation(
        self, transformation: TransformationResponse, sample_size: int = 100
    ) -> Dict[str, Any]:
        """Generate a preview of transformation results"""

        # Create a limited query for preview
        preview_query = f"""
        WITH preview_data AS (
            {transformation.query}
        )
        SELECT * FROM preview_data LIMIT {sample_size}
        """

        # Execute preview using Glue (faster for small datasets)
        preview_context = {
            "query": preview_query,
            "source_path": transformation.config.source_path,
            "target_path": "/tmp/preview",  # Temporary location
            "dry_run": True,
            "sample_size": sample_size,
        }

        start_time = datetime.utcnow()
        preview_result = await self.glue_executor.execute_preview(preview_context)
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return {
            "data": preview_result["data"],
            "schema": preview_result["schema"],
            "row_count": len(preview_result["data"]),
            "execution_time_ms": execution_time,
        }

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

    async def _estimate_execution_cost(
        self, transformation: TransformationResponse
    ) -> float:
        """Estimate execution cost in USD"""

        # Simplified cost estimation based on data size and complexity
        try:
            source_size_gb = await self.s3_client.get_path_size(
                transformation.config.source_path
            )

            # Basic cost calculation (simplified)
            # Glue: $0.44 per DPU-hour, EMR: variable based on instance type
            base_cost_per_gb = 0.10  # Simplified rate
            query_complexity_multiplier = 1.0

            # Analyze query complexity
            if "JOIN" in transformation.query.upper():
                query_complexity_multiplier *= 2.0
            if "GROUP BY" in transformation.query.upper():
                query_complexity_multiplier *= 1.5
            if "WINDOW" in transformation.query.upper():
                query_complexity_multiplier *= 2.5

            estimated_cost = (
                source_size_gb * base_cost_per_gb * query_complexity_multiplier
            )
            return round(estimated_cost, 2)

        except Exception as e:
            logger.warning(f"Could not estimate cost: {str(e)}")
            return 0.0

    async def _estimate_execution_time(
        self, transformation: TransformationResponse
    ) -> int:
        """Estimate execution time in minutes"""

        try:
            source_size_gb = await self.s3_client.get_path_size(
                transformation.config.source_path
            )

            # Base processing rate: ~1GB per minute for simple queries
            base_time_per_gb = 1.0
            query_complexity_multiplier = 1.0

            # Analyze query complexity
            if "JOIN" in transformation.query.upper():
                query_complexity_multiplier *= 3.0
            if "GROUP BY" in transformation.query.upper():
                query_complexity_multiplier *= 2.0
            if "ORDER BY" in transformation.query.upper():
                query_complexity_multiplier *= 1.5

            estimated_minutes = (
                source_size_gb * base_time_per_gb * query_complexity_multiplier
            )
            return max(1, int(estimated_minutes))  # Minimum 1 minute

        except Exception as e:
            logger.warning(f"Could not estimate execution time: {str(e)}")
            return 5  # Default 5 minutes

    async def _monitor_execution(
        self, execution_id: UUID, job_id: str, engine: str, transformation_id: UUID
    ) -> None:
        """Monitor job execution and update status"""

        max_attempts = 360  # 30 minutes with 5-second intervals
        attempt = 0

        while attempt < max_attempts:
            try:
                # Check job status based on engine
                if engine == "glue":
                    job_status = await self.glue_executor.get_job_status(job_id)
                elif engine == "emr":
                    job_status = await self.emr_executor.get_job_status(job_id)
                else:
                    logger.error(f"Unknown engine: {engine}")
                    break

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

                # Check if job is complete
                if job_status["status"] in ["completed", "failed", "cancelled"]:
                    logger.info(
                        f"Execution {execution_id} finished with status: {job_status['status']}"
                    )
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
                    "error_message": "Monitoring timeout",
                    "updated_at": datetime.utcnow(),
                },
            )
