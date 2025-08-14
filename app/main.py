"""Application entry point."""

from fastapi import FastAPI

from app.airbyte.router import router

def create_app() -> FastAPI:
    app = FastAPI(title="Airbyte FastAPI Wrapper")
    app.include_router(router)
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
