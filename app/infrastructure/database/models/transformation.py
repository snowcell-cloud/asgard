"""
Database models for transformations
"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    Boolean,
    JSON,
    Integer,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.infrastructure.database.connection import Base


class TransformationModel(Base):
    """Database model for transformations"""

    __tablename__ = "transformations"

    # Primary fields
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    transformation_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    version = Column(String(20), nullable=False, default="1.0.0")

    # SQL and configuration
    query = Column(Text, nullable=False)
    column_operations = Column(JSON, nullable=True, default=list)
    config = Column(JSON, nullable=False)
    tags = Column(JSON, nullable=True, default=list)

    # Audit fields
    created_by = Column(String(100), nullable=False)
    modified_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    executions = relationship(
        "TransformationExecutionModel",
        back_populates="transformation",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Transformation(id={self.id}, name='{self.name}', status='{self.status}')>"


class TransformationExecutionModel(Base):
    """Database model for transformation executions"""

    __tablename__ = "transformation_executions"

    # Primary fields
    execution_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    transformation_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("transformations.id"),
        nullable=False,
        index=True,
    )
    job_id = Column(String(100), nullable=False, index=True)  # AWS Glue job run ID

    # Execution details
    status = Column(
        String(20), nullable=False, index=True
    )  # submitted, running, completed, failed, cancelled
    executed_by = Column(String(100), nullable=False)
    execution_config = Column(JSON, nullable=True, default=dict)
    dry_run = Column(Boolean, nullable=False, default=False)

    # Timestamps
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    # Results and metrics
    metrics = Column(JSON, nullable=True, default=dict)
    error_message = Column(Text, nullable=True)
    failure_info = Column(JSON, nullable=True, default=dict)

    # Relationships
    transformation = relationship("TransformationModel", back_populates="executions")

    def __repr__(self):
        return f"<TransformationExecution(id={self.execution_id}, job_id='{self.job_id}', status='{self.status}')>"


class DataQualityCheckModel(Base):
    """Database model for data quality checks"""

    __tablename__ = "data_quality_checks"

    # Primary fields
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    execution_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("transformation_executions.execution_id"),
        nullable=False,
        index=True,
    )

    # Quality check details
    check_type = Column(String(50), nullable=False)  # not_null, unique, range, etc.
    column_name = Column(String(100), nullable=False)
    rule_definition = Column(JSON, nullable=False)

    # Results
    status = Column(String(20), nullable=False)  # passed, failed, warning
    passed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    total_count = Column(Integer, nullable=False, default=0)

    # Details
    error_details = Column(JSON, nullable=True, default=list)
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<DataQualityCheck(id={self.id}, type='{self.check_type}', status='{self.status}')>"


class TransformationMetricsModel(Base):
    """Database model for detailed transformation metrics"""

    __tablename__ = "transformation_metrics"

    # Primary fields
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    execution_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("transformation_executions.execution_id"),
        nullable=False,
        index=True,
    )

    # Performance metrics
    records_processed = Column(Integer, nullable=False, default=0)
    records_output = Column(Integer, nullable=False, default=0)
    execution_time_seconds = Column(Integer, nullable=False, default=0)

    # Resource usage
    cpu_usage_percent = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    disk_usage_mb = Column(Integer, nullable=True)

    # Cost metrics
    estimated_cost_usd = Column(
        String(20), nullable=True
    )  # Store as string to avoid precision issues
    actual_cost_usd = Column(String(20), nullable=True)
    dpu_hours = Column(String(20), nullable=True)

    # Data quality metrics
    data_quality_score = Column(Integer, nullable=True)  # 0-100
    validation_errors_count = Column(Integer, nullable=False, default=0)
    warnings_count = Column(Integer, nullable=False, default=0)

    # Additional metrics
    source_data_size_mb = Column(Integer, nullable=True)
    output_data_size_mb = Column(Integer, nullable=True)
    compression_ratio = Column(String(10), nullable=True)  # e.g., "2.5:1"

    # Timestamps
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<TransformationMetrics(id={self.id}, records_processed={self.records_processed})>"


class JobScheduleModel(Base):
    """Database model for scheduled transformation jobs"""

    __tablename__ = "job_schedules"

    # Primary fields
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    transformation_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("transformations.id"),
        nullable=False,
        index=True,
    )

    # Schedule details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cron_expression = Column(
        String(100), nullable=False
    )  # e.g., "0 2 * * *" for daily at 2 AM
    timezone = Column(String(50), nullable=False, default="UTC")

    # Configuration
    execution_config = Column(JSON, nullable=True, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit fields
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Last execution tracking
    last_execution_id = Column(PostgresUUID(as_uuid=True), nullable=True)
    last_execution_at = Column(DateTime, nullable=True)
    last_execution_status = Column(String(20), nullable=True)
    next_execution_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    transformation = relationship("TransformationModel")

    def __repr__(self):
        return f"<JobSchedule(id={self.id}, name='{self.name}', cron='{self.cron_expression}')>"


class AuditLogModel(Base):
    """Database model for audit logging"""

    __tablename__ = "audit_logs"

    # Primary fields
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Audit details
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # transformation, execution, etc.
    entity_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    action = Column(
        String(50), nullable=False, index=True
    )  # create, update, delete, execute

    # Change details
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    changes_summary = Column(Text, nullable=True)

    # Context
    user_id = Column(String(100), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', entity_type='{self.entity_type}')>"
