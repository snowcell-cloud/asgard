"""
Dependency injection for the FastAPI application
"""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.transformation_repository import (
    TransformationRepository,
)
from app.infrastructure.aws.s3_client import get_s3_client, S3Client
from app.infrastructure.aws.glue_client import get_glue_executor, GlueExecutor
from app.core.services.transformation_service import TransformationService
from app.utils.validators import SQLValidator


async def get_transformation_repository(
    db_session: AsyncSession = Depends(get_db_session),
) -> TransformationRepository:
    """Get transformation repository instance"""
    return TransformationRepository(db_session)


async def get_sql_validator() -> SQLValidator:
    """Get SQL validator instance"""
    return SQLValidator()


async def get_transformation_service(
    db_session: AsyncSession = Depends(get_db_session),
    transformation_repo: TransformationRepository = Depends(
        get_transformation_repository
    ),
    s3_client: S3Client = Depends(get_s3_client),
    glue_executor: GlueExecutor = Depends(get_glue_executor),
    sql_validator: SQLValidator = Depends(get_sql_validator),
) -> TransformationService:
    """Get transformation service instance with all dependencies"""
    return TransformationService(
        db_session=db_session,
        transformation_repo=transformation_repo,
        s3_client=s3_client,
        glue_executor=glue_executor,
        sql_validator=sql_validator,
    )


async def get_current_user() -> str:
    """Get current user (simplified for demo - implement proper auth)"""
    # In production, this would decode JWT token and return user info
    return "demo_user"


def get_settings_dependency():
    """Get settings as dependency"""
    return get_settings()
