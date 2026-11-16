from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_JWT_SECRET = "CHANGE_THIS_LOCAL_DEVELOPMENT_SECRET_BEFORE_DEPLOYMENT"


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
    jwt_secret: str = _DEFAULT_JWT_SECRET
    access_token_minutes: int = 60
    ai_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-6-astra"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_runtime_secrets_and_provider(self):
        environment = self.app_env.strip().lower()
        provider = self.ai_provider.strip().lower()
        if provider not in {"mock", "openai"}:
            raise ValueError("AI_PROVIDER must be either 'mock' or 'openai'")
        if environment in {"production", "prod"}:
            if self.jwt_secret == _DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError(
                    "Production requires JWT_SECRET to be explicitly configured "
                    "with at least 32 characters"
                )
            if provider == "mock":
                raise ValueError("Production must use a real AI provider, not AI_PROVIDER=mock")
            if provider == "openai" and not self.openai_api_key:
                raise ValueError("Production AI_PROVIDER=openai requires OPENAI_API_KEY")
        return self


settings = Settings()
engine = create_engine(normalize_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass
