from fastapi import FastAPI

from app.airbyte.router import router as airbyte_router
from app.data_transformation.router import router as transform_router
from app.data_products.router import router as data_products_router
from app.dbt_transformations.router import router as dbt_transformations_router
from app.feast.router import router as feast_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Asgard Data Platform API",
        description="FastAPI wrapper for Airbyte data ingestion, Spark transformations, Data Products, DBT Transformations, and Feast Feature Store",
        version="2.1.0",
    )

    # Include routers
    app.include_router(airbyte_router)
    app.include_router(transform_router)
    # app.include_router(data_products_router)
    app.include_router(dbt_transformations_router)
    app.include_router(feast_router)

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "asgard-data-platform",
            "version": "2.1.0",
            "apis": {
                "airbyte": "/airbyte",
                "spark_transformation": "/spark-transformation",
                "dbt_transformations": "/dbt",
                "feast_feature_store": "/feast",
            },
            "features": [
                "SQL-driven transformations from silver to gold layer",
                "Dynamic dbt model generation",
                "Iceberg table management on S3",
                "Trino-based query execution",
                "Feast feature store with ML model training",
                "Online and batch predictions",
            ],
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
