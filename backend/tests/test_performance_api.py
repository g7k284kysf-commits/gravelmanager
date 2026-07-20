from datetime import date, timedelta

from fastapi.testclient import TestClient


def training_payload(
    training_date: date, tss: float = 100, duration: int = 60
) -> dict[str, object]:
    return {
        "date": training_date.isoformat(),
        "sport": "Gravel",
        "duration_minutes": duration,
        "distance_km": 30,
        "elevation_m": 300,
        "average_power": 210,
        "normalized_power": 225,
        "average_hr": 145,
        "max_hr": 175,
        "tss": tss,
        "intensity_factor": 0.8,
        "calories": 700,
        "notes": "Performance test ride",
    }


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPassword!42"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_empty_history_returns_explicit_zero_and_empty_states(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    summary = client.get("/api/v1/performance/summary", headers=auth_headers)
    chart = client.get("/api/v1/performance/chart?range=28d", headers=auth_headers)
    recalculation = client.post("/api/v1/performance/recalculate", headers=auth_headers, json={})

    assert summary.status_code == 200
    assert all(value == 0 for value in summary.json().values())
    assert chart.status_code == 200
    assert chart.json()["points"] == []
    assert recalculation.json() == {
        "recalculated_from": None,
        "recalculated_through": None,
        "rows_written": 0,
    }


def test_training_crud_recalculates_aggregated_daily_metrics(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    today = date.today()
    first = client.post(
        "/api/v1/trainings",
        headers=auth_headers,
        json=training_payload(today, 80, 60),
    )
    second = client.post(
        "/api/v1/trainings",
        headers=auth_headers,
        json=training_payload(today, 40, 30),
    )

    chart = client.get(
        f"/api/v1/performance/chart?start_date={today}&end_date={today}",
        headers=auth_headers,
    ).json()
    assert len(chart["points"]) == 1
    assert chart["points"][0]["daily_tss"] == 120
    assert chart["points"][0]["ctl"] == round(120 / 42, 2)
    assert client.get("/api/v1/dashboard", headers=auth_headers).json()["weekly_tss"] == 120

    moved_day = today - timedelta(days=2)
    updated_payload = training_payload(moved_day, 50, 45)
    updated = client.put(
        f"/api/v1/trainings/{first.json()['id']}",
        headers=auth_headers,
        json=updated_payload,
    )
    assert updated.status_code == 200
    assert (
        client.delete(f"/api/v1/trainings/{second.json()['id']}", headers=auth_headers).status_code
        == 204
    )

    recalculated = client.post(
        "/api/v1/performance/recalculate",
        headers=auth_headers,
        json={"start_date": moved_day.isoformat()},
    )
    repeated = client.post(
        "/api/v1/performance/recalculate",
        headers=auth_headers,
        json={"start_date": moved_day.isoformat()},
    )
    assert recalculated.status_code == repeated.status_code == 200
    assert recalculated.json()["rows_written"] == repeated.json()["rows_written"]
    summary = client.get("/api/v1/performance/summary", headers=auth_headers).json()
    assert summary["seven_day_tss"] == 50


def test_performance_data_is_isolated_per_user(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    second_headers = register(client, "second-rider@example.com")
    today = date.today()
    assert (
        client.post(
            "/api/v1/trainings", headers=auth_headers, json=training_payload(today, 90)
        ).status_code
        == 201
    )

    own_summary = client.get("/api/v1/performance/summary", headers=auth_headers).json()
    other_summary = client.get("/api/v1/performance/summary", headers=second_headers).json()
    assert own_summary["seven_day_tss"] == 90
    assert other_summary["seven_day_tss"] == 0
    assert (
        client.get("/api/v1/performance/chart?range=28d", headers=second_headers).json()["points"]
        == []
    )


def test_chart_range_controls_and_validation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    today = date.today()
    response = client.get("/api/v1/performance/chart?range=28d", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["start_date"] == (today - timedelta(days=27)).isoformat()
    assert response.json()["end_date"] == today.isoformat()

    future = today + timedelta(days=1)
    assert (
        client.get(f"/api/v1/performance/chart?end_date={future}", headers=auth_headers).status_code
        == 422
    )
    assert (
        client.get(
            f"/api/v1/performance/chart?start_date={today}&end_date={today - timedelta(days=1)}",
            headers=auth_headers,
        ).status_code
        == 422
    )
    assert (
        client.get("/api/v1/performance/chart?range=invalid", headers=auth_headers).status_code
        == 422
    )


def test_performance_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/performance/summary").status_code == 401
    assert client.get("/api/v1/performance/chart").status_code == 401
    assert client.post("/api/v1/performance/recalculate", json={}).status_code == 401
