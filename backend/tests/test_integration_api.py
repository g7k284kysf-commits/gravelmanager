from io import BytesIO
from typing import BinaryIO

import pytest
from app.core.config import settings
from app.core.database import SessionLocal
from app.domain.integrations import IntegrationCapability, NormalizedImportRecord
from app.integrations.exceptions import (
    IntegrationError,
    InvalidSyncStateError,
    ProviderOperationNotSupported,
    ProviderTemporaryError,
)
from app.integrations.parsers import PARSERS, FileParser
from app.integrations.providers import (
    IntegrationProvider,
    ProviderRegistry,
    ProviderSyncResult,
)
from app.jobs import process_import_file
from app.models import IntegrationConnection, IntegrationEvent, User
from app.models.integration import ConnectionStatus, EventSeverity, SyncStatus, SyncType
from app.services.audit import IntegrationAuditService
from app.services.synchronization import SynchronizationService
from fastapi.testclient import TestClient
from sqlalchemy import select


class DeterministicProvider(IntegrationProvider):
    provider_key = "deterministic"
    display_name = "Deterministic"
    capabilities = frozenset({IntegrationCapability.POLLING, IntegrationCapability.ACTIVITY_IMPORT})
    operational = True

    def start_sync(self, cursor: str | None = None) -> ProviderSyncResult:
        return ProviderSyncResult(
            records=(
                NormalizedImportRecord(
                    record_type="activity", normalized_payload={"source": "test"}
                ),
            ),
            cursor="next-cursor",
            records_created=1,
        )


class TemporaryFailureProvider(DeterministicProvider):
    provider_key = "temporary_failure"

    def start_sync(self, cursor: str | None = None) -> ProviderSyncResult:
        raise ProviderTemporaryError("Provider is temporarily unavailable")


class PermanentFailureProvider(DeterministicProvider):
    provider_key = "permanent_failure"

    def start_sync(self, cursor: str | None = None) -> ProviderSyncResult:
        raise ProviderOperationNotSupported("Provider operation is unavailable")


class PartialProvider(DeterministicProvider):
    provider_key = "partial"

    def start_sync(self, cursor: str | None = None) -> ProviderSyncResult:
        return ProviderSyncResult(
            records=(
                NormalizedImportRecord(
                    record_type="activity", normalized_payload={"source": "partial-test"}
                ),
            ),
            cursor="partial-cursor",
            records_created=1,
            records_failed=1,
        )


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

    unsafe_configuration = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers,
        json={
            "provider_key": "garmin",
            "configuration": {"nested": {"access_token": "must-not-leak"}},
        },
    )
    assert unsafe_configuration.status_code == 422
    assert "credentials field" in unsafe_configuration.text


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
    assert (
        client.patch(
            f"/api/v1/integrations/connections/{connection['id']}",
            headers=other,
            json={"display_name": "Stolen connection"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/integrations/connections/{connection['id']}/test", headers=other
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/integrations/connections/{connection['id']}/revoke", headers=other
        ).status_code
        == 404
    )
    assert client.get("/api/v1/integrations/events", headers=other).json() == []

    with SessionLocal() as db:
        from app.models import TenantMembership

        membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == 1))
        assert membership is not None
        other_athlete = User(email="same-tenant-athlete@example.com", password_hash="hashed")
        db.add(other_athlete)
        db.flush()
        db.add(
            IntegrationEvent(
                tenant_id=membership.tenant_id,
                athlete_id=other_athlete.id,
                provider_key="manual_upload",
                event_type="other_athlete_event",
                severity=EventSeverity.INFO,
                correlation_id="other-athlete-event",
                message="Must remain private",
                details={},
            )
        )
        db.commit()
    original_events = client.get("/api/v1/integrations/events", headers=auth_headers).json()
    assert "other_athlete_event" not in {event["event_type"] for event in original_events}


def test_audit_details_are_recursively_redacted(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with SessionLocal() as db:
        from app.models import TenantMembership

        membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == 1))
        assert membership is not None
        event = IntegrationAuditService(db).record(
            tenant_id=membership.tenant_id,
            athlete_id=1,
            provider_key="manual_upload",
            event_type="redaction_test",
            message="Safe message",
            correlation_id="redaction-test",
            details={
                "access_token": "secret-token",
                "nested": {"password": "secret-password", "safe": "visible"},
            },
        )
        db.commit()
        db.refresh(event)
        assert event.details == {
            "access_token": "[REDACTED]",
            "nested": {"password": "[REDACTED]", "safe": "visible"},
        }


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
    completed_before = client.get(
        f"/api/v1/imports/files/{import_id}", headers=auth_headers
    ).json()["processing_completed_at"]
    process_import_file(import_id)
    completed_after = client.get(f"/api/v1/imports/files/{import_id}", headers=auth_headers).json()[
        "processing_completed_at"
    ]
    assert completed_after == completed_before
    assert (
        len(client.get(f"/api/v1/imports/files/{import_id}/records", headers=auth_headers).json())
        == 1
    )
    second = client.post(
        "/api/v1/auth/register",
        json={"email": "other-importer@example.com", "password": "StrongPassword!42"},
    ).json()
    other = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.get(f"/api/v1/imports/files/{import_id}", headers=other).status_code == 404
    assert (
        client.get(f"/api/v1/imports/files/{import_id}/records", headers=other).status_code == 404
    )
    assert (
        client.post(f"/api/v1/imports/files/{import_id}/process", headers=other).status_code == 404
    )
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

    malformed_response = client.post(
        "/api/v1/imports/files",
        headers=auth_headers,
        files={"file": ("bad.gpx", BytesIO(b"<gpx><trk"), "application/gpx+xml")},
    )
    assert malformed_response.status_code == 201
    malformed = malformed_response.json()
    processed = client.post(
        f"/api/v1/imports/files/{malformed['id']}/process", headers=auth_headers
    )
    assert processed.json()["status"] == "failed"
    detail = client.get(f"/api/v1/imports/files/{malformed['id']}", headers=auth_headers).json()
    assert detail["error_code"] == "import_parse_error"


def test_upload_rejects_spoofed_and_oversized_files_before_persistence(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spoofed = client.post(
        "/api/v1/imports/files",
        headers=auth_headers,
        files={
            "file": (
                "route.gpx",
                BytesIO(b"date,tss\n2026-01-01,80\n"),
                "application/gpx+xml",
            )
        },
    )
    assert spoofed.status_code == 422
    assert "GPX format" in spoofed.json()["detail"]

    monkeypatch.setattr(settings, "max_upload_size_bytes", 7)
    oversized = client.post(
        "/api/v1/imports/files",
        headers=auth_headers,
        files={"file": ("training.csv", BytesIO(b"a,b\n1,2\n"), "text/csv")},
    )
    assert oversized.status_code == 422
    assert "upload limit" in oversized.json()["detail"]


def test_unexpected_import_failure_is_persisted_without_raw_diagnostics(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ExplodingParser(FileParser):
        def parse(self, stream: BinaryIO) -> list[NormalizedImportRecord]:
            raise RuntimeError("/private/server/path database-password")

    monkeypatch.setitem(PARSERS, "csv", ExplodingParser())
    uploaded = client.post(
        "/api/v1/imports/files",
        headers=auth_headers,
        files={
            "file": (
                "unexpected.csv",
                BytesIO(b"date,tss\n2026-02-01,70\n"),
                "text/csv",
            )
        },
    ).json()
    processed = client.post(f"/api/v1/imports/files/{uploaded['id']}/process", headers=auth_headers)
    assert processed.json()["status"] == "failed"
    detail = client.get(f"/api/v1/imports/files/{uploaded['id']}", headers=auth_headers).json()
    assert detail["error_code"] == "unexpected_import_error"
    assert detail["error_message"] == "Import processing failed safely"
    assert "/private/server/path" not in processed.text


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
        with pytest.raises(IntegrationError, match="already active"):
            service.request(connection, SyncType.MANUAL, "different-request-key")
        service.execute(sync)
        assert sync.status == SyncStatus.SUCCEEDED
        assert sync.cursor_after == "next-cursor"
        assert sync.records_created == 1
        with pytest.raises(InvalidSyncStateError, match="cannot run"):
            service.execute(sync)
        db.commit()

    assert (
        client.get("/api/v1/integrations/syncs", headers=auth_headers).json()[0]["status"]
        == "succeeded"
    )


def test_sync_retryable_non_retryable_and_partial_outcomes(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with SessionLocal() as db:
        from app.models import TenantMembership

        membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == 1))
        assert membership is not None

        def connection_for(
            provider: IntegrationProvider,
        ) -> tuple[IntegrationConnection, ProviderRegistry]:
            registry = ProviderRegistry()
            registry.register(provider)
            connection = IntegrationConnection(
                tenant_id=membership.tenant_id,
                athlete_id=1,
                provider_key=provider.provider_key,
                display_name=provider.display_name,
                status=ConnectionStatus.CONNECTED,
                scopes=[],
                configuration={},
            )
            db.add(connection)
            db.flush()
            return connection, registry

        temporary_connection, temporary_registry = connection_for(TemporaryFailureProvider())
        temporary, _ = SynchronizationService(db, temporary_registry).request(
            temporary_connection, SyncType.MANUAL, "temporary-request"
        )
        with pytest.raises(ProviderTemporaryError):
            SynchronizationService(db, temporary_registry).execute(temporary)
        assert temporary.status == SyncStatus.FAILED
        assert temporary.error_code == "provider_temporary_error"
        assert temporary.sync_metadata["retryable"] is True

        permanent_connection, permanent_registry = connection_for(PermanentFailureProvider())
        permanent, _ = SynchronizationService(db, permanent_registry).request(
            permanent_connection, SyncType.MANUAL, "permanent-request"
        )
        SynchronizationService(db, permanent_registry).execute(permanent)
        assert permanent.status == SyncStatus.FAILED
        assert permanent.sync_metadata["retryable"] is False

        partial_connection, partial_registry = connection_for(PartialProvider())
        partial, _ = SynchronizationService(db, partial_registry).request(
            partial_connection, SyncType.MANUAL, "partial-request"
        )
        SynchronizationService(db, partial_registry).execute(partial)
        assert partial.status == SyncStatus.PARTIALLY_SUCCEEDED
        assert partial.records_discovered == 2
        assert partial.records_created == 1
        assert partial.records_failed == 1
        db.commit()

    retry_non_retryable = client.post(
        f"/api/v1/integrations/syncs/{permanent.id}/retry", headers=auth_headers
    )
    assert retry_non_retryable.status_code == 409
    assert retry_non_retryable.json()["detail"] == "Synchronization failure is not retryable"


def test_manual_upload_connection_rejects_unsupported_sync(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    connection = client.post(
        "/api/v1/integrations/connections",
        headers=auth_headers,
        json={"provider_key": "manual_upload"},
    ).json()
    response = client.post(
        f"/api/v1/integrations/connections/{connection['id']}/sync",
        headers=auth_headers,
        json={"sync_type": "manual"},
    )
    assert response.status_code == 422
    assert "does not support" in response.json()["detail"]


def test_integration_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/integrations/providers").status_code == 401
    assert client.get("/api/v1/integrations/connections").status_code == 401
    assert client.get("/api/v1/imports/files").status_code == 401
