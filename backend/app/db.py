from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Normalize provider URLs to the psycopg 3 SQLAlchemy dialect."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Settings(BaseSettings):
    app_name: str = "VANTIQ API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://vantiq:vantiq_local_only@localhost:5432/vantiq"
    jwt_secret: str = "CHANGE_THIS_LOCAL_DEVELOPMENT_SECRET_BEFORE_DEPLOYMENT"
    access_token_minutes: int = 60
    openai_api_key: str | None = None
    openai_model: str = "gpt-6-astra"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
engine = create_engine(normalize_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass
