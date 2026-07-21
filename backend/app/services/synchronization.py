from datetime import UTC, datetime
from uuid import uuid4

from app.domain.integrations import IntegrationCapability
from app.integrations.exceptions import (
    IntegrationError,
    InvalidSyncStateError,
    ProviderExecutionError,
    ProviderOperationNotSupported,
)
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
                IntegrationSync.athlete_id == connection.athlete_id,
                IntegrationSync.connection_id == connection.id,
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
        if not provider.operational or not provider.supports(IntegrationCapability.POLLING):
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
        if sync.status not in {SyncStatus.QUEUED, SyncStatus.FAILED}:
            raise InvalidSyncStateError(
                f"Synchronization cannot run from status {sync.status.value}"
            )
        if sync.status == SyncStatus.FAILED and not sync.sync_metadata.get("retryable", False):
            raise InvalidSyncStateError("Non-retryable synchronization cannot run again")
        if sync.status == SyncStatus.FAILED:
            previous_attempts = sync.sync_metadata.get("retry_attempts", 0)
            attempts = (previous_attempts if isinstance(previous_attempts, int) else 0) + 1
            sync.sync_metadata = {**sync.sync_metadata, "retry_attempts": attempts}
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
        sync.completed_at = None
        sync.error_code = None
        sync.error_message = None
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
        try:
            provider = self.registry.get(sync.provider_key)
            result = provider.start_sync(sync.cursor_before)
            sync.records_discovered = result.records_discovered
            sync.records_created = result.records_created
            sync.records_updated = result.records_updated
            sync.records_skipped = result.records_skipped
            sync.records_failed = result.records_failed
            sync.cursor_after = result.cursor
            successful_records = result.records_created + result.records_updated
            if result.records_failed and successful_records:
                sync.status = SyncStatus.PARTIALLY_SUCCEEDED
            elif result.records_failed:
                sync.status = SyncStatus.FAILED
                sync.error_code = "provider_record_failures"
                sync.error_message = "All discovered provider records failed"
            else:
                sync.status = SyncStatus.SUCCEEDED
            sync.completed_at = datetime.now(UTC)
            if sync.status in {SyncStatus.SUCCEEDED, SyncStatus.PARTIALLY_SUCCEEDED}:
                connection.last_successful_sync_at = sync.completed_at
                connection.last_error_code = None
                connection.last_error_message = None
            else:
                connection.last_error_code = sync.error_code
                connection.last_error_message = "Synchronization failed"
            self.audit.record(
                tenant_id=sync.tenant_id,
                athlete_id=sync.athlete_id,
                provider_key=sync.provider_key,
                event_type=(
                    "synchronization_completed"
                    if sync.status != SyncStatus.FAILED
                    else "synchronization_failed"
                ),
                message=(
                    "Synchronization completed"
                    if sync.status != SyncStatus.FAILED
                    else "Synchronization failed"
                ),
                correlation_id=sync.correlation_id,
                connection_id=sync.connection_id,
                sync_id=sync.id,
                severity=(
                    EventSeverity.WARNING
                    if sync.status == SyncStatus.PARTIALLY_SUCCEEDED
                    else EventSeverity.ERROR
                    if sync.status == SyncStatus.FAILED
                    else EventSeverity.INFO
                ),
                details={
                    "records_created": result.records_created,
                    "records_updated": result.records_updated,
                    "records_skipped": result.records_skipped,
                    "records_failed": result.records_failed,
                },
            )
        except IntegrationError as exc:
            sync.status = SyncStatus.FAILED
            sync.completed_at = datetime.now(UTC)
            sync.error_code = exc.code
            sync.error_message = str(exc)[:500]
            connection.last_error_code = exc.code
            connection.last_error_message = "Synchronization failed"
            sync.sync_metadata = {**sync.sync_metadata, "retryable": exc.retryable}
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
        except Exception as exc:
            safe_error = ProviderExecutionError("Provider synchronization failed unexpectedly")
            sync.status = SyncStatus.FAILED
            sync.completed_at = datetime.now(UTC)
            sync.error_code = safe_error.code
            sync.error_message = str(safe_error)
            sync.sync_metadata = {**sync.sync_metadata, "retryable": False}
            connection.last_error_code = safe_error.code
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
                details={"error_code": safe_error.code, "retryable": False},
            )
            raise safe_error from exc
        return sync
