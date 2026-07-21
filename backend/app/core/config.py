from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gravel Manager API"
    environment: str = "development"
    database_url: str = "sqlite:///./gravel_manager.db"
    jwt_secret: str = Field(default="development-secret-change-before-production", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    ctl_time_constant_days: int = Field(default=42, gt=0)
    atl_time_constant_days: int = Field(default=7, gt=0)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
