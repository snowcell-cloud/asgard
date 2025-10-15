"""
FastAPI router for Data Product API endpoints.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/data-products", tags=["Data Products"])


@router.get("/health")
async def health():
    """Health check for data products service."""
    return {"status": "healthy", "service": "data-products"}
