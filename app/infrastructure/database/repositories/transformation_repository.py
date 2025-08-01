"""
Transformation repository for database operations
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.transformation import (
    TransformationModel,
    TransformationExecutionModel,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TransformationRepository:
    """Repository for transformation database operations"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(self, transformation_data: Dict[str, Any]) -> TransformationModel:
        """Create a new transformation"""

        transformation = TransformationModel(**transformation_data)
        self.db_session.add(transformation)
        await self.db_session.flush()
        await self.db_session.refresh(transformation)

        logger.info(f"Created transformation in database: {transformation.id}")
        return transformation

    async def get_by_id(self, transformation_id: UUID) -> Optional[TransformationModel]:
        """Get transformation by ID"""

        stmt = select(TransformationModel).where(
            TransformationModel.id == transformation_id
        )
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[TransformationModel]:
        """Get transformation by name"""

        stmt = select(TransformationModel).where(
            TransformationModel.name == name, TransformationModel.status != "inactive"
        )
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_with_filters(
        self, offset: int = 0, limit: int = 20, filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[TransformationModel], int]:
        """List transformations with filters and pagination"""

        filters = filters or {}

        # Base query
        query = select(TransformationModel)
        count_query = select(func.count(TransformationModel.id))

        # Apply filters
        conditions = []

        if filters.get("status"):
            conditions.append(TransformationModel.status == filters["status"])

        if filters.get("transformation_type"):
            conditions.append(
                TransformationModel.transformation_type
                == filters["transformation_type"]
            )

        if filters.get("tag"):
            conditions.append(TransformationModel.tags.contains([filters["tag"]]))

        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            conditions.append(
                or_(
                    TransformationModel.name.ilike(search_term),
                    TransformationModel.description.ilike(search_term),
                )
            )

        if filters.get("created_by"):
            conditions.append(TransformationModel.created_by == filters["created_by"])

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total count
        count_result = await self.db_session.execute(count_query)
        total = count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(TransformationModel.created_at.desc())
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await self.db_session.execute(query)
        transformations = result.scalars().all()

        return list(transformations), total

    async def update(
        self, transformation_id: UUID, update_data: Dict[str, Any]
    ) -> TransformationModel:
        """Update transformation"""

        stmt = (
            update(TransformationModel)
            .where(TransformationModel.id == transformation_id)
            .values(**update_data)
            .returning(TransformationModel)
        )

        result = await self.db_session.execute(stmt)
        transformation = result.scalar_one()
        await self.db_session.flush()

        logger.info(f"Updated transformation: {transformation_id}")
        return transformation

    async def delete(self, transformation_id: UUID) -> bool:
        """Hard delete transformation (use with caution)"""

        stmt = delete(TransformationModel).where(
            TransformationModel.id == transformation_id
        )

        result = await self.db_session.execute(stmt)
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(f"Deleted transformation: {transformation_id}")
            return True

        return False

    async def create_execution(
        self, execution_data: Dict[str, Any]
    ) -> TransformationExecutionModel:
        """Create transformation execution record"""

        execution = TransformationExecutionModel(**execution_data)
        self.db_session.add(execution)
        await self.db_session.flush()
        await self.db_session.refresh(execution)

        logger.info(f"Created execution record: {execution.execution_id}")
        return execution

    async def get_execution(
        self, execution_id: UUID
    ) -> Optional[TransformationExecutionModel]:
        """Get execution by ID"""

        stmt = select(TransformationExecutionModel).where(
            TransformationExecutionModel.execution_id == execution_id
        )
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_execution(
        self, execution_id: UUID, update_data: Dict[str, Any]
    ) -> TransformationExecutionModel:
        """Update execution record"""

        stmt = (
            update(TransformationExecutionModel)
            .where(TransformationExecutionModel.execution_id == execution_id)
            .values(**update_data)
            .returning(TransformationExecutionModel)
        )

        result = await self.db_session.execute(stmt)
        execution = result.scalar_one()
        await self.db_session.flush()

        return execution

    async def get_execution_history(
        self, transformation_id: UUID, limit: int = 50
    ) -> List[TransformationExecutionModel]:
        """Get execution history for a transformation"""

        stmt = (
            select(TransformationExecutionModel)
            .where(TransformationExecutionModel.transformation_id == transformation_id)
            .order_by(TransformationExecutionModel.executed_at.desc())
            .limit(limit)
        )

        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_executions(
        self, since: datetime
    ) -> List[TransformationExecutionModel]:
        """Get recent executions since given datetime"""

        stmt = (
            select(TransformationExecutionModel)
            .where(TransformationExecutionModel.executed_at >= since)
            .order_by(TransformationExecutionModel.executed_at.desc())
        )

        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def get_stats(self) -> Dict[str, Any]:
        """Get transformation statistics"""

        # Total transformations
        total_stmt = select(func.count(TransformationModel.id))
        total_result = await self.db_session.execute(total_stmt)
        total_transformations = total_result.scalar()

        # Active transformations
        active_stmt = select(func.count(TransformationModel.id)).where(
            TransformationModel.status == "active"
        )
        active_result = await self.db_session.execute(active_stmt)
        active_transformations = active_result.scalar()

        # Most used transformations (by execution count)
        most_used_stmt = (
            select(
                TransformationModel.name,
                func.count(TransformationExecutionModel.execution_id).label(
                    "execution_count"
                ),
            )
            .join(TransformationExecutionModel)
            .group_by(TransformationModel.id, TransformationModel.name)
            .order_by(func.count(TransformationExecutionModel.execution_id).desc())
            .limit(5)
        )
        most_used_result = await self.db_session.execute(most_used_stmt)
        most_used = [
            {"name": row.name, "execution_count": row.execution_count}
            for row in most_used_result
        ]

        # Transformation types breakdown
        types_stmt = select(
            TransformationModel.transformation_type,
            func.count(TransformationModel.id).label("count"),
        ).group_by(TransformationModel.transformation_type)
        types_result = await self.db_session.execute(types_stmt)
        transformation_types = {
            row.transformation_type: row.count for row in types_result
        }

        return {
            "total_transformations": total_transformations,
            "active_transformations": active_transformations,
            "most_used_transformations": most_used,
            "transformation_types": transformation_types,
        }

    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """Clean up old execution records"""

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        stmt = delete(TransformationExecutionModel).where(
            and_(
                TransformationExecutionModel.executed_at < cutoff_date,
                TransformationExecutionModel.status.in_(
                    ["completed", "failed", "cancelled"]
                ),
            )
        )

        result = await self.db_session.execute(stmt)
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old execution records")

        return deleted_count

    async def get_active_executions(self) -> List[TransformationExecutionModel]:
        """Get currently active executions"""

        stmt = (
            select(TransformationExecutionModel)
            .where(TransformationExecutionModel.status.in_(["submitted", "running"]))
            .order_by(TransformationExecutionModel.executed_at.desc())
        )

        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())
