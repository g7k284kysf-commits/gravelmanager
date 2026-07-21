from base64 import b64decode
from binascii import Error as Base64Error
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gravel Manager API"
    app_version: str = "0.3.0"
    environment: str = "development"
    database_url: str = "sqlite:///./gravel_manager.db"
    jwt_secret: str = Field(default="development-secret-change-before-production", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    ctl_time_constant_days: int = Field(default=42, gt=0)
    atl_time_constant_days: int = Field(default=7, gt=0)
    credential_encryption_key: str = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    storage_root: str = "/tmp/gravel-manager-uploads"
    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    job_backend: Literal["sync", "dramatiq"] = "sync"
    redis_url: str = "redis://redis:6379/0"
    job_max_retries: int = Field(default=3, ge=0, le=10)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value

    @field_validator("credential_encryption_key")
    @classmethod
    def validate_credential_key(cls, value: str) -> str:
        try:
            decoded = b64decode(value.encode("ascii"), altchars=b"-_", validate=True)
        except (UnicodeEncodeError, ValueError, Base64Error) as exc:
            raise ValueError("must be a URL-safe base64-encoded Fernet key") from exc
        if len(decoded) != 32:
            raise ValueError("must decode to exactly 32 bytes")
        return value

    @model_validator(mode="after")
    def reject_development_secrets_in_production(self) -> "Settings":
        if self.environment.lower() == "production":
            if self.jwt_secret == "development-secret-change-before-production":
                raise ValueError("JWT_SECRET must be changed in production")
            if self.credential_encryption_key == ("MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="):
                raise ValueError("CREDENTIAL_ENCRYPTION_KEY must be changed in production")
            if self.job_backend != "dramatiq":
                raise ValueError("JOB_BACKEND must be dramatiq in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
