from fastapi import FastAPI
from sqlalchemy import text
from .db import engine, settings
from .routers import auth, customers, conversations

app = FastAPI(title=settings.app_name, version="0.4.0")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": "vantiq-api",
        "environment": settings.app_env,
        "database": "connected",
    }


@app.get("/api/v1")
def api_root() -> dict[str, str]:
    return {
        "product": "WORLD-CLASS SALES AI",
        "core": "VANTIQ",
        "status": "auth-customer-conversation-api",
        "message": "Authenticated tenant-scoped customer and explicitly authorized conversation APIs are available.",
    }
