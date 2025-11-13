 
from fastapi import FastAPI

from app.airbyte.router import router as airbyte_router
from app.data_transformation.router import router as transform_router
from app.data_products.router import router as data_products_router
from app.dbt_transformations.router import router as dbt_transformations_router
from app.feast.router import router as feast_router
from app.mlops.router import router as mlops_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Asgard Data Platform API",
        description="End-to-end ML platform: Data ingestion → Feature engineering → Model training → Serving",
        version="3.0.0",
    )

    # Include routers
    app.include_router(airbyte_router)
    app.include_router(transform_router)
    # app.include_router(data_products_router)
    app.include_router(dbt_transformations_router)
    app.include_router(feast_router)
    app.include_router(mlops_router)

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "asgard-data-platform",
            "version": "3.0.0",
            "apis": {
                "airbyte": "/airbyte",
                "dbt_transformations": "/dbt",
                "feast_features": "/feast",
                "mlops_lifecycle": "/mlops",
            },
            "ml_pipeline": {
                "1_data_ingestion": "/airbyte → Ingest raw data",
                "2_transformation": "/dbt → Transform to Gold layer",
                "3_feature_engineering": "/feast/features → Register features",
                "4_model_training": "/mlops/models → Train with MLflow",
                "5_model_registry": "/mlops/registry → Version & promote",
                "6_predictions": "/mlops/serve → Real-time & batch predictions",
            },
            "clear_separation": {
                "feast": "Feature store management only",
                "mlops": "All ML training, registry, and predictions",
            },
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
