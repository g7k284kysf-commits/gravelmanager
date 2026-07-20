from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_registration_and_login(client: TestClient) -> None:
    payload = {"email": "athlete@example.com", "password": "StrongPassword!42"}
    registered = client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    assert registered.json()["user"]["email"] == payload["email"]
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409
    logged_in = client.post("/api/v1/auth/login", json=payload)
    assert logged_in.status_code == 200
    assert logged_in.json()["token_type"] == "bearer"


def test_profile_training_and_dashboard(client: TestClient, auth_headers: dict[str, str]) -> None:
    profile = client.put(
        "/api/v1/athlete/profile",
        headers=auth_headers,
        json={"name": "Taylor Gravel", "ftp": 300, "max_hr": 190, "threshold_hr": 172},
    )
    assert profile.status_code == 200
    assert profile.json()["ftp"] == 300
    training = client.post(
        "/api/v1/trainings",
        headers=auth_headers,
        json={
            "date": "2026-07-20",
            "sport": "Gravel",
            "duration_minutes": 120,
            "distance_km": 48.5,
            "elevation_m": 800,
            "average_power": 220,
            "normalized_power": 245,
            "average_hr": 150,
            "max_hr": 182,
            "tss": 150,
            "intensity_factor": 0.86,
            "calories": 1300,
            "notes": "Race simulation",
        },
    )
    assert training.status_code == 201
    assert len(client.get("/api/v1/trainings", headers=auth_headers).json()) == 1
    dashboard = client.get("/api/v1/dashboard", headers=auth_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["ftp"] == 300
    assert dashboard.json()["weekly_tss"] == 150


def test_protected_endpoint_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/dashboard").status_code == 401
