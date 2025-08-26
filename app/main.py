
from fastapi import FastAPI

from app.airbyte.router import router as airbyte_router
from app.data_transformation.router import router as transform_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Asgard Data Platform API",
        description="FastAPI wrapper for Airbyte data ingestion and Spark transformations",
        version="1.0.0"
    )
    
    # Include routers
    app.include_router(airbyte_router)
    app.include_router(transform_router)
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "asgard-data-platform"}
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
