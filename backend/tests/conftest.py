import os
from collections.abc import Generator
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-validation"
os.environ["ENVIRONMENT"] = "test"
os.environ["JOB_BACKEND"] = "sync"

import pytest
from app.core.config import settings
from app.core.database import Base, engine
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def database(tmp_path: Path) -> Generator[None]:
    settings.storage_root = str(tmp_path)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "rider@example.com", "password": "StrongPassword!42"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
