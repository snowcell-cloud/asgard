"""
Main FastAPI application entry point
"""

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog
import time

from app.api.router import api_router
from app.config import get_settings
from app.exceptions import (
    TransformationNotFoundError,
    ValidationError,
    ExecutionError,
)
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""

    # Startup
    logger = structlog.get_logger()
    logger.info("Starting Data Lake Transformation API...")

    # Initialize database connection pool
    from app.infrastructure.database.connection import init_db

    await init_db()

    # Initialize AWS clients
    from app.infrastructure.aws.s3_client import init_s3_client
    from app.infrastructure.aws.glue_client import init_glue_client
    from app.infrastructure.aws.emr_client import init_emr_client

    await init_s3_client()
    await init_glue_client()
    await init_emr_client()

    logger.info("Application startup completed")

    yield

    # Shutdown
    logger.info("Shutting down Data Lake Transformation API...")

    # Close database connections
    from app.infrastructure.database.connection import close_db

    await close_db()

    logger.info("Application shutdown completed")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application"""

    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="Data Lake Transformation API",
        description="""
        ## 🏗️ Data Lake Transformation API
        
        A comprehensive API for managing and executing data transformations on your S3 data lake.
        
        ### 🔁 Customer Data - Transformations
        
        #### Example Operations:
        - **Remove columns**: Remove sensitive or unnecessary data fields
        - **Add columns**: Create computed columns and derived metrics
        - **Update existing data**: Clean, standardize, and validate data
        - **Aggregate data**: Create summary tables and analytics views
        - **Join datasets**: Combine multiple data sources
        
        ### 📄 Data Transformation Definition
        
        Each transformation includes:
        - **SQL Query**: The transformation logic
        - **Configuration**: Source/target paths, partitioning, format
        - **Column Operations**: Specific column-level transformations
        - **Validation Rules**: Data quality and business rules
        - **Execution History**: Track all runs and results
        
        ### 🎯 Key Features
        
        - **Multi-Engine Support**: Execute on AWS Glue or EMR
        - **Customer PII Handling**: Built-in anonymization and masking
        - **Query Validation**: Syntax and security validation
        - **Preview Mode**: Test transformations on sample data
        - **Monitoring**: Real-time job status and metrics
        - **Templates**: Pre-built transformations for common use cases
        """,
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    if not settings.debug:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Log request
        logger = structlog.get_logger()
        logger.info(
            "Request processed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time,
        )

        return response

    # Include API router
    app.include_router(api_router, prefix="/api")

    # Custom exception handlers
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation Error",
                "message": str(exc),
                "details": exc.details if hasattr(exc, "details") else None,
            },
        )

    @app.exception_handler(TransformationNotFoundError)
    async def transformation_not_found_handler(
        request: Request, exc: TransformationNotFoundError
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Transformation Not Found", "message": str(exc)},
        )

    @app.exception_handler(ExecutionError)
    async def execution_error_handler(request: Request, exc: ExecutionError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Execution Error",
                "message": str(exc),
                "job_id": exc.job_id if hasattr(exc, "job_id") else None,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Request Validation Error",
                "message": "Invalid request data",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger = structlog.get_logger()
        logger.error(
            "Unhandled exception",
            exception=str(exc),
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            },
        )

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root() -> Dict[str, Any]:
        """Root endpoint with API information"""
        return {
            "name": "Data Lake Transformation API",
            "version": "1.0.0",
            "status": "healthy",
            "documentation": "/docs",
            "health_check": "/api/v1/health",
            "transformations_endpoint": "/api/v1/transformations",
            "jobs_endpoint": "/api/v1/jobs",
        }

    return app


# Create the application instance
app = create_application()


def start():
    """Start the application (used by UV script)"""
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else settings.workers,
        access_log=settings.debug,
    )


if __name__ == "__main__":
    start()
