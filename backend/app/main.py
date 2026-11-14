from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VANTIQ API"
    app_env: str = "development"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "vantiq-api",
        "environment": settings.app_env,
    }


@app.get("/api/v1")
def api_root() -> dict[str, str]:
    return {
        "product": "WORLD-CLASS SALES AI",
        "core": "VANTIQ",
        "status": "bootstrap",
        "message": "Core sales intelligence API scaffold",
    }
