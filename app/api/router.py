"""
Main API router configuration
"""

from fastapi import APIRouter

from app.api.v1.endpoints import transformations, jobs, health

# Create main API router
api_router = APIRouter()

# Include v1 endpoints
v1_router = APIRouter(prefix="/v1")

# Add all endpoint routers
v1_router.include_router(health.router)
v1_router.include_router(transformations.router)
v1_router.include_router(jobs.router)

# Include v1 router in main API router
api_router.include_router(v1_router)
