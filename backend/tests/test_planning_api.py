from fastapi.testclient import TestClient


def season_payload(name: str = "2027 season") -> dict[str, object]:
    return {
        "name": name,
        "start_date": "2027-01-01",
        "end_date": "2027-12-31",
        "status": "active",
        "description": "Gravel season",
    }


def test_season_goal_hierarchy_and_competition_crud(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    season = client.post("/api/v1/planning/seasons", headers=auth_headers, json=season_payload())
    assert season.status_code == 201
    season_id = season.json()["id"]
    parent = client.post(
        "/api/v1/planning/goals",
        headers=auth_headers,
        json={
            "season_id": season_id,
            "title": "Peak for Unbound",
            "goal_type": "season",
            "priority": "critical",
            "target_date": "2027-06-05",
        },
    )
    child = client.post(
        "/api/v1/planning/goals",
        headers=auth_headers,
        json={
            "season_id": season_id,
            "parent_goal_id": parent.json()["id"],
            "title": "Improve heat tolerance",
            "goal_type": "heat_adaptation",
            "priority": "high",
        },
    )
    assert child.status_code == 201

    competition_ids: list[int] = []
    for index, priority in enumerate(("A", "B", "C"), start=1):
        response = client.post(
            "/api/v1/planning/competitions",
            headers=auth_headers,
            json={
                "season_id": season_id,
                "goal_id": parent.json()["id"] if priority == "A" else None,
                "name": f"Race {priority}",
                "start_date": f"2027-0{index + 4}-01",
                "end_date": f"2027-0{index + 4}-01",
                "race_priority": priority,
            },
        )
        assert response.status_code == 201
        competition_ids.append(response.json()["id"])

    assert len(client.get("/api/v1/planning/seasons", headers=auth_headers).json()) == 1
    assert len(client.get("/api/v1/planning/goals", headers=auth_headers).json()) == 2
    assert len(client.get("/api/v1/planning/competitions", headers=auth_headers).json()) == 3
    assert (
        client.delete(
            f"/api/v1/planning/competitions/{competition_ids[-1]}",
            headers=auth_headers,
        ).status_code
        == 204
    )


def test_planning_validation_and_tenant_isolation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    invalid_dates = client.post(
        "/api/v1/planning/seasons",
        headers=auth_headers,
        json={
            "name": "Invalid",
            "start_date": "2027-12-31",
            "end_date": "2027-01-01",
        },
    )
    assert invalid_dates.status_code == 422
    assert (
        client.post(
            "/api/v1/planning/competitions",
            headers=auth_headers,
            json={
                "season_id": 999,
                "name": "Invalid priority",
                "start_date": "2027-01-01",
                "end_date": "2027-01-01",
                "race_priority": "D",
            },
        ).status_code
        == 422
    )

    season = client.post(
        "/api/v1/planning/seasons", headers=auth_headers, json=season_payload()
    ).json()
    goal = client.post(
        "/api/v1/planning/goals",
        headers=auth_headers,
        json={
            "season_id": season["id"],
            "title": "Private goal",
            "goal_type": "custom",
        },
    ).json()
    competition = client.post(
        "/api/v1/planning/competitions",
        headers=auth_headers,
        json={
            "season_id": season["id"],
            "name": "Private race",
            "start_date": "2027-05-01",
            "end_date": "2027-05-01",
            "race_priority": "B",
        },
    ).json()
    second = client.post(
        "/api/v1/auth/register",
        json={"email": "other-planner@example.com", "password": "StrongPassword!42"},
    ).json()
    other_headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert (
        client.get(f"/api/v1/planning/seasons/{season['id']}", headers=other_headers).status_code
        == 404
    )
    cross_parent = client.post(
        "/api/v1/planning/goals",
        headers=other_headers,
        json={
            "parent_goal_id": 1,
            "title": "Cross-tenant child",
            "goal_type": "custom",
        },
    )
    assert cross_parent.status_code == 404
    assert (
        client.put(
            f"/api/v1/planning/seasons/{season['id']}",
            headers=other_headers,
            json=season_payload("Stolen season"),
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/planning/seasons/{season['id']}", headers=other_headers).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/v1/planning/goals/{goal['id']}",
            headers=other_headers,
            json={"title": "Stolen goal", "goal_type": "custom"},
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/planning/goals/{goal['id']}", headers=other_headers).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/v1/planning/competitions/{competition['id']}",
            headers=other_headers,
            json={
                "season_id": season["id"],
                "name": "Stolen race",
                "start_date": "2027-05-01",
                "end_date": "2027-05-01",
                "race_priority": "B",
            },
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/planning/competitions/{competition['id']}", headers=other_headers
        ).status_code
        == 404
    )


def test_planning_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/planning/seasons").status_code == 401
    assert client.get("/api/v1/planning/goals").status_code == 401
    assert client.get("/api/v1/planning/competitions").status_code == 401


def test_goal_hierarchy_rejects_direct_and_indirect_cycles(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    season_id = client.post(
        "/api/v1/planning/seasons", headers=auth_headers, json=season_payload()
    ).json()["id"]

    def create(title: str, parent_goal_id: int | None = None) -> dict[str, object]:
        return client.post(
            "/api/v1/planning/goals",
            headers=auth_headers,
            json={
                "season_id": season_id,
                "parent_goal_id": parent_goal_id,
                "title": title,
                "goal_type": "custom",
            },
        ).json()

    goal_a = create("Goal A")
    goal_b = create("Goal B", int(goal_a["id"]))
    goal_c = create("Goal C", int(goal_b["id"]))

    direct = client.put(
        f"/api/v1/planning/goals/{goal_a['id']}",
        headers=auth_headers,
        json={
            "season_id": season_id,
            "parent_goal_id": goal_a["id"],
            "title": "Goal A",
            "goal_type": "custom",
        },
    )
    assert direct.status_code == 422
    assert direct.json()["detail"] == "Goal hierarchy cannot contain a cycle"

    three_node_cycle = client.put(
        f"/api/v1/planning/goals/{goal_a['id']}",
        headers=auth_headers,
        json={
            "season_id": season_id,
            "parent_goal_id": goal_c["id"],
            "title": "Goal A",
            "goal_type": "custom",
        },
    )
    assert three_node_cycle.status_code == 422
    assert three_node_cycle.json()["detail"] == "Goal hierarchy cannot contain a cycle"
    assert (
        client.get(f"/api/v1/planning/goals/{goal_a['id']}", headers=auth_headers).json()[
            "parent_goal_id"
        ]
        is None
    )
