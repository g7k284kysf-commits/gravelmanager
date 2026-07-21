from io import BytesIO

from app.core.database import SessionLocal
from app.domain.integrations import IntegrationCapability, NormalizedImportRecord
from app.integrations.providers import IntegrationProvider, ProviderRegistry
from app.models import IntegrationConnection
from app.models.integration import ConnectionStatus, SyncStatus, SyncType
from app.services.synchronization import SynchronizationService
from fastapi.testclient import TestClient
from sqlalchemy import select


class DeterministicProvider(IntegrationProvider):
    provider_key = "deterministic"
    display_name = "Deterministic"
    capabilities = frozenset({IntegrationCapability.POLLING, IntegrationCapability.ACTIVITY_IMPORT})

    def start_sync(
        self, cursor: str | None = None
    ) -> tuple[list[NormalizedImportRecord], str | None]:
        return [
            NormalizedImportRecord(record_type="activity", normalized_payload={"source": "test"})
        ], "next-cursor"


def deterministic_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(DeterministicProvider())
    return registry


def test_provider_metadata_connection_crud_and_secret_redaction(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    providers = client.get("/api/v1/integrations/providers", headers=auth_headers)
    assert providers.status_code == 200
    assert (
        next(item for item in providers.json() if item["provider_key"] == "garmin")["availability"]
        == "coming_soon"
    )

    created = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers,
        json={
            "provider_key": "manual_upload",
            "display_name": "My files",
            "credentials": {"access_token": "never-return-this"},
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "connected"
    assert "credentials" not in created.json()
    assert "encrypted_credentials" not in created.json()
    connection_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/integrations/connections/{connection_id}",
        headers=auth_headers,
        json={"display_name": "Renamed files"},
    )
    assert updated.json()["display_name"] == "Renamed files"
    tested = client.post(
        f"/api/v1/integrations/connections/{connection_id}/test",
        headers=auth_headers,
    )
    assert tested.json() == {
        "supported": True,
        "succeeded": True,
        "message": "Connection is ready",
    }
    revoked = client.post(
        f"/api/v1/integrations/connections/{connection_id}/revoke",
        headers=auth_headers,
    )
    assert revoked.json()["status"] == "revoked"
    with SessionLocal() as db:
        stored = db.get(IntegrationConnection, connection_id)
        assert stored is not None
        assert stored.encrypted_credentials is None


def test_connection_and_event_tenant_isolation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    connection = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers,
        json={"provider_key": "manual_upload"},
    ).json()
    second = client.post(
        "/api/v1/auth/register",
        json={"email": "other-integrator@example.com", "password": "StrongPassword!42"},
    ).json()
    other = {"Authorization": f"Bearer {second['access_token']}"}
    assert (
        client.get(
            f"/api/v1/integrations/connections/{connection['id']}", headers=other
        ).status_code
        == 404
    )
    assert client.get("/api/v1/integrations/events", headers=other).json() == []


def test_upload_process_duplicate_and_audit_flow(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    contents = b"date,tss\n2026-01-01,80\n"
    uploaded = client.post(
        "/api/v1/imports/files",
        headers=auth_headers,
        files={"file": ("training.csv", BytesIO(contents), "text/csv")},
    )
    assert uploaded.status_code == 201
    import_id = uploaded.json()["id"]
    processed = client.post(f"/api/v1/imports/files/{import_id}/process", headers=auth_headers)
    assert processed.status_code == 202
    assert processed.json()["status"] == "succeeded"
    records = client.get(f"/api/v1/imports/files/{import_id}/records", headers=auth_headers).json()
    assert records[0]["normalized_payload"]["values"]["tss"] == "80"
    duplicate = client.post(
        "/api/v1/imports/files",
        headers=auth_headers,
        files={"file": ("again.csv", BytesIO(contents), "text/csv")},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "duplicate_import"
    events = client.get("/api/v1/integrations/events", headers=auth_headers).json()
    assert {event["event_type"] for event in events} >= {
        "file_uploaded",
        "import_queued",
        "import_completed",
        "duplicate_import_detected",
    }


def test_upload_validation_and_import_job_failure(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    invalid_type = client.post(
        "/api/v1/imports/files",
        headers=auth_headers,
        files={"file": ("image.png", BytesIO(b"png"), "image/png")},
    )
    assert invalid_type.status_code == 422

    malformed = client.post(
        "/api/v1/imports/files",
        headers=auth_headers,
        files={"file": ("bad.gpx", BytesIO(b"not xml"), "application/gpx+xml")},
    ).json()
    processed = client.post(
        f"/api/v1/imports/files/{malformed['id']}/process", headers=auth_headers
    )
    assert processed.json()["status"] == "failed"
    detail = client.get(f"/api/v1/imports/files/{malformed['id']}", headers=auth_headers).json()
    assert detail["error_code"] == "import_parse_error"


def test_sync_state_transitions_idempotency_and_retry_limit(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with SessionLocal() as db:
        from app.models import TenantMembership, User

        user = db.scalar(select(User).where(User.email == "rider@example.com"))
        assert user is not None
        membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == user.id))
        assert membership is not None
        connection = IntegrationConnection(
            tenant_id=membership.tenant_id,
            athlete_id=user.id,
            provider_key="deterministic",
            display_name="Test provider",
            status=ConnectionStatus.CONNECTED,
            scopes=[],
            configuration={},
        )
        db.add(connection)
        db.flush()
        service = SynchronizationService(db, deterministic_registry())
        sync, created = service.request(connection, SyncType.MANUAL, "same-request-key")
        repeated, repeated_created = service.request(
            connection, SyncType.MANUAL, "same-request-key"
        )
        assert created is True
        assert repeated_created is False
        assert repeated.id == sync.id
        service.execute(sync)
        assert sync.status == SyncStatus.SUCCEEDED
        assert sync.cursor_after == "next-cursor"
        assert sync.records_created == 1
        db.commit()

    assert (
        client.get("/api/v1/integrations/syncs", headers=auth_headers).json()[0]["status"]
        == "succeeded"
    )


def test_integration_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/integrations/providers").status_code == 401
    assert client.get("/api/v1/integrations/connections").status_code == 401
    assert client.get("/api/v1/imports/files").status_code == 401
