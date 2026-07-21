from datetime import UTC, datetime
from uuid import uuid4

from app.domain.integrations import IntegrationCapability
from app.integrations.exceptions import IntegrationError, ProviderOperationNotSupported
from app.integrations.providers import ProviderRegistry
from app.models import IntegrationConnection, IntegrationSync
from app.models.integration import EventSeverity, SyncStatus, SyncType
from app.services.audit import IntegrationAuditService
from sqlalchemy import select
from sqlalchemy.orm import Session


class SynchronizationService:
    def __init__(self, db: Session, registry: ProviderRegistry) -> None:
        self.db = db
        self.registry = registry
        self.audit = IntegrationAuditService(db)

    def request(
        self,
        connection: IntegrationConnection,
        sync_type: SyncType,
        idempotency_key: str | None,
    ) -> tuple[IntegrationSync, bool]:
        key = idempotency_key or str(uuid4())
        existing = self.db.scalar(
            select(IntegrationSync).where(
                IntegrationSync.tenant_id == connection.tenant_id,
                IntegrationSync.idempotency_key == key,
            )
        )
        if existing is not None:
            return existing, False
        active = self.db.scalar(
            select(IntegrationSync).where(
                IntegrationSync.tenant_id == connection.tenant_id,
                IntegrationSync.connection_id == connection.id,
                IntegrationSync.status.in_([SyncStatus.QUEUED, SyncStatus.RUNNING]),
            )
        )
        if active is not None:
            raise IntegrationError("A synchronization is already active for this connection")
        provider = self.registry.get(connection.provider_key)
        if not provider.supports(IntegrationCapability.POLLING):
            raise ProviderOperationNotSupported(
                "This provider does not support manual synchronization"
            )
        correlation_id = str(uuid4())
        sync = IntegrationSync(
            tenant_id=connection.tenant_id,
            athlete_id=connection.athlete_id,
            connection_id=connection.id,
            provider_key=connection.provider_key,
            sync_type=sync_type,
            status=SyncStatus.QUEUED,
            idempotency_key=key,
            correlation_id=correlation_id,
            sync_metadata={},
        )
        self.db.add(sync)
        self.db.flush()
        self.audit.record(
            tenant_id=sync.tenant_id,
            athlete_id=sync.athlete_id,
            provider_key=sync.provider_key,
            event_type="synchronization_queued",
            message="Synchronization queued",
            correlation_id=sync.correlation_id,
            connection_id=sync.connection_id,
            sync_id=sync.id,
        )
        return sync, True

    def execute(self, sync: IntegrationSync) -> IntegrationSync:
        connection = self.db.scalar(
            select(IntegrationConnection).where(
                IntegrationConnection.id == sync.connection_id,
                IntegrationConnection.tenant_id == sync.tenant_id,
            )
        )
        if connection is None:
            raise IntegrationError("Integration connection no longer exists")
        sync.status = SyncStatus.RUNNING
        sync.started_at = datetime.now(UTC)
        connection.last_sync_attempt_at = sync.started_at
        self.audit.record(
            tenant_id=sync.tenant_id,
            athlete_id=sync.athlete_id,
            provider_key=sync.provider_key,
            event_type="synchronization_started",
            message="Synchronization started",
            correlation_id=sync.correlation_id,
            connection_id=sync.connection_id,
            sync_id=sync.id,
        )
        self.db.flush()
        provider = self.registry.get(sync.provider_key)
        try:
            records, cursor = provider.start_sync(sync.cursor_before)
            sync.records_discovered = len(records)
            sync.records_created = len(records)
            sync.cursor_after = cursor
            sync.status = SyncStatus.SUCCEEDED
            sync.completed_at = datetime.now(UTC)
            connection.last_successful_sync_at = sync.completed_at
            connection.last_error_code = None
            connection.last_error_message = None
            self.audit.record(
                tenant_id=sync.tenant_id,
                athlete_id=sync.athlete_id,
                provider_key=sync.provider_key,
                event_type="synchronization_completed",
                message="Synchronization completed",
                correlation_id=sync.correlation_id,
                connection_id=sync.connection_id,
                sync_id=sync.id,
                details={"records_created": len(records)},
            )
        except IntegrationError as exc:
            sync.status = SyncStatus.FAILED
            sync.completed_at = datetime.now(UTC)
            sync.error_code = exc.code
            sync.error_message = str(exc)[:500]
            connection.last_error_code = exc.code
            connection.last_error_message = "Synchronization failed"
            self.audit.record(
                tenant_id=sync.tenant_id,
                athlete_id=sync.athlete_id,
                provider_key=sync.provider_key,
                event_type="synchronization_failed",
                message="Synchronization failed",
                correlation_id=sync.correlation_id,
                connection_id=sync.connection_id,
                sync_id=sync.id,
                severity=EventSeverity.ERROR,
                details={"error_code": exc.code, "retryable": exc.retryable},
            )
            if exc.retryable:
                raise
        return sync
