from fastapi import FastAPI
from sqlalchemy import text
from .db import engine, settings

app = FastAPI(title=settings.app_name, version="0.2.0")


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
        "status": "database-foundation",
        "message": "Tenant, user, customer, conversation, message and customer-memory schema is available.",
    }
