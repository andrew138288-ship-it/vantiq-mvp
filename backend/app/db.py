from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict


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
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass
