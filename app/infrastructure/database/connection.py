"""
Database connection management
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import asyncio

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Database models base
Base = declarative_base()

# Global database engine and session factory
_engine = None
_session_factory = None


async def init_db():
    """Initialize database connection"""
    global _engine, _session_factory

    settings = get_settings()

    _engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.debug,
        future=True,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    logger.info("Database connection initialized")


async def close_db():
    """Close database connection"""
    global _engine

    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")


async def create_database():
    """Create database tables"""
    global _engine

    if _engine:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    global _session_factory

    if not _session_factory:
        raise Exception("Database not initialized. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
