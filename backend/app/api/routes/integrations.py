from datetime import UTC, datetime
from typing import Annotated

from app.api.deps import CurrentTenant, DbSession
from app.core.config import settings
from app.integrations.credentials import CredentialEncryptionService
from app.integrations.exceptions import IntegrationError, ProviderOperationNotSupported
from app.integrations.providers import provider_registry
from app.jobs import get_job_dispatcher
from app.models import IntegrationConnection, IntegrationEvent, IntegrationSync
from app.models.integration import ConnectionStatus, EventSeverity, SyncStatus
from app.schemas.integration import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestResponse,
    ConnectionUpdate,
    IntegrationEventResponse,
    ProviderResponse,
    SyncRequest,
    SyncResponse,
)
from app.services.audit import IntegrationAuditService
from app.services.synchronization import SynchronizationService
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/integrations", tags=["Integrations"])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def owned_connection(
    connection_id: int, db: DbSession, tenant: CurrentTenant
) -> IntegrationConnection:
    connection = db.scalar(
        select(IntegrationConnection).where(
            IntegrationConnection.id == connection_id,
            IntegrationConnection.tenant_id == tenant.tenant_id,
            IntegrationConnection.athlete_id == tenant.athlete_id,
        )
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="Integration connection not found")
    return connection


def owned_sync(sync_id: int, db: DbSession, tenant: CurrentTenant) -> IntegrationSync:
    sync = db.scalar(
        select(IntegrationSync).where(
            IntegrationSync.id == sync_id,
            IntegrationSync.tenant_id == tenant.tenant_id,
            IntegrationSync.athlete_id == tenant.athlete_id,
        )
    )
    if sync is None:
        raise HTTPException(status_code=404, detail="Integration sync not found")
    return sync


@router.get("/providers", response_model=list[ProviderResponse])
def providers(_: CurrentTenant) -> list[ProviderResponse]:
    return [
        ProviderResponse.model_validate(item, from_attributes=True)
        for item in provider_registry.list()
    ]


@router.get("/connections", response_model=list[ConnectionResponse])
def connections(
    db: DbSession,
    tenant: CurrentTenant,
    limit: Limit = 50,
    offset: Offset = 0,
    provider_key: Annotated[str | None, Query(max_length=80)] = None,
    connection_status: ConnectionStatus | None = None,
) -> list[IntegrationConnection]:
    statement = select(IntegrationConnection).where(
        IntegrationConnection.tenant_id == tenant.tenant_id,
        IntegrationConnection.athlete_id == tenant.athlete_id,
    )
    if provider_key:
        statement = statement.where(IntegrationConnection.provider_key == provider_key)
    if connection_status:
        statement = statement.where(IntegrationConnection.status == connection_status)
    return list(
        db.scalars(
            statement.order_by(IntegrationConnection.created_at.desc()).limit(limit).offset(offset)
        )
    )


@router.post(
    "/connections",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_connection(
    payload: ConnectionCreate, db: DbSession, tenant: CurrentTenant
) -> IntegrationConnection:
    try:
        provider = provider_registry.get(payload.provider_key)
        provider.validate_configuration(payload.configuration)
    except IntegrationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    existing = db.scalar(
        select(IntegrationConnection).where(
            IntegrationConnection.tenant_id == tenant.tenant_id,
            IntegrationConnection.athlete_id == tenant.athlete_id,
            IntegrationConnection.provider_key == provider.provider_key,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Provider connection already exists")
    encrypted_credentials = None
    if payload.credentials:
        encrypted_credentials = CredentialEncryptionService(
            settings.credential_encryption_key
        ).encrypt(payload.credentials)
    connection = IntegrationConnection(
        tenant_id=tenant.tenant_id,
        athlete_id=tenant.athlete_id,
        provider_key=provider.provider_key,
        display_name=payload.display_name or provider.display_name,
        status=(
            ConnectionStatus.CONNECTED
            if provider.availability == "manual_import_only"
            else ConnectionStatus.PENDING
        ),
        scopes=payload.scopes,
        configuration=payload.configuration,
        encrypted_credentials=encrypted_credentials,
    )
    db.add(connection)
    db.flush()
    IntegrationAuditService(db).record(
        tenant_id=tenant.tenant_id,
        athlete_id=tenant.athlete_id,
        provider_key=provider.provider_key,
        event_type="connection_created",
        message="Integration connection created",
        correlation_id=f"connection-{connection.id}",
        connection_id=connection.id,
        details={"availability": provider.availability},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Provider connection already exists") from exc
    db.refresh(connection)
    return connection


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: int, db: DbSession, tenant: CurrentTenant
) -> IntegrationConnection:
    return owned_connection(connection_id, db, tenant)


@router.patch("/connections/{connection_id}", response_model=ConnectionResponse)
def update_connection(
    connection_id: int,
    payload: ConnectionUpdate,
    db: DbSession,
    tenant: CurrentTenant,
) -> IntegrationConnection:
    connection = owned_connection(connection_id, db, tenant)
    if connection.status == ConnectionStatus.REVOKED:
        raise HTTPException(status_code=409, detail="Revoked connections cannot be updated")
    updates = payload.model_dump(exclude_unset=True, exclude={"credentials"})
    provider_registry.get(connection.provider_key).validate_configuration(
        updates.get("configuration", connection.configuration)
    )
    for field, value in updates.items():
        setattr(connection, field, value)
    if payload.credentials is not None:
        connection.encrypted_credentials = CredentialEncryptionService(
            settings.credential_encryption_key
        ).encrypt(payload.credentials)
    IntegrationAuditService(db).record(
        tenant_id=tenant.tenant_id,
        athlete_id=tenant.athlete_id,
        provider_key=connection.provider_key,
        event_type="connection_updated",
        message="Integration connection updated",
        correlation_id=f"connection-{connection.id}",
        connection_id=connection.id,
    )
    db.commit()
    db.refresh(connection)
    return connection


@router.post("/connections/{connection_id}/revoke", response_model=ConnectionResponse)
def revoke_connection(
    connection_id: int, db: DbSession, tenant: CurrentTenant
) -> IntegrationConnection:
    connection = owned_connection(connection_id, db, tenant)
    provider_registry.get(connection.provider_key).revoke_authorization()
    connection.status = ConnectionStatus.REVOKED
    connection.revoked_at = datetime.now(UTC)
    connection.encrypted_credentials = None
    IntegrationAuditService(db).record(
        tenant_id=tenant.tenant_id,
        athlete_id=tenant.athlete_id,
        provider_key=connection.provider_key,
        event_type="connection_revoked",
        message="Integration connection revoked",
        correlation_id=f"connection-{connection.id}",
        connection_id=connection.id,
    )
    db.commit()
    db.refresh(connection)
    return connection


@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResponse)
def test_connection(
    connection_id: int, db: DbSession, tenant: CurrentTenant
) -> ConnectionTestResponse:
    connection = owned_connection(connection_id, db, tenant)
    provider = provider_registry.get(connection.provider_key)
    try:
        succeeded = provider.test_connection()
    except ProviderOperationNotSupported:
        IntegrationAuditService(db).record(
            tenant_id=tenant.tenant_id,
            athlete_id=tenant.athlete_id,
            provider_key=connection.provider_key,
            event_type="connection_test_failed",
            message="Connection test is not supported by this provider",
            correlation_id=f"connection-{connection.id}",
            connection_id=connection.id,
            severity=EventSeverity.WARNING,
        )
        db.commit()
        return ConnectionTestResponse(
            supported=False,
            succeeded=False,
            message="Connection testing will be available with the live provider adapter.",
        )
    event_type = "connection_test_succeeded" if succeeded else "connection_test_failed"
    IntegrationAuditService(db).record(
        tenant_id=tenant.tenant_id,
        athlete_id=tenant.athlete_id,
        provider_key=connection.provider_key,
        event_type=event_type,
        message="Connection test completed",
        correlation_id=f"connection-{connection.id}",
        connection_id=connection.id,
    )
    db.commit()
    return ConnectionTestResponse(
        supported=True,
        succeeded=succeeded,
        message="Connection is ready" if succeeded else "Connection test failed",
    )


@router.post(
    "/connections/{connection_id}/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_sync(
    connection_id: int,
    payload: SyncRequest,
    db: DbSession,
    tenant: CurrentTenant,
) -> IntegrationSync:
    connection = owned_connection(connection_id, db, tenant)
    try:
        sync, created = SynchronizationService(db, provider_registry).request(
            connection, payload.sync_type, payload.idempotency_key
        )
    except IntegrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    if created:
        get_job_dispatcher().integration_sync(sync.id)
        db.refresh(sync)
    return sync


@router.get("/syncs", response_model=list[SyncResponse])
def syncs(
    db: DbSession,
    tenant: CurrentTenant,
    limit: Limit = 50,
    offset: Offset = 0,
    provider_key: Annotated[str | None, Query(max_length=80)] = None,
    sync_status: SyncStatus | None = None,
) -> list[IntegrationSync]:
    statement = select(IntegrationSync).where(
        IntegrationSync.tenant_id == tenant.tenant_id,
        IntegrationSync.athlete_id == tenant.athlete_id,
    )
    if provider_key:
        statement = statement.where(IntegrationSync.provider_key == provider_key)
    if sync_status:
        statement = statement.where(IntegrationSync.status == sync_status)
    return list(
        db.scalars(
            statement.order_by(IntegrationSync.requested_at.desc()).limit(limit).offset(offset)
        )
    )


@router.get("/syncs/{sync_id}", response_model=SyncResponse)
def get_sync(sync_id: int, db: DbSession, tenant: CurrentTenant) -> IntegrationSync:
    return owned_sync(sync_id, db, tenant)


@router.post("/syncs/{sync_id}/retry", response_model=SyncResponse)
def retry_sync(sync_id: int, db: DbSession, tenant: CurrentTenant) -> IntegrationSync:
    sync = owned_sync(sync_id, db, tenant)
    if sync.status != SyncStatus.FAILED:
        raise HTTPException(status_code=409, detail="Only failed syncs can be retried")
    previous_attempts = sync.sync_metadata.get("retry_attempts", 0)
    attempts = (previous_attempts if isinstance(previous_attempts, int) else 0) + 1
    if attempts > settings.job_max_retries:
        raise HTTPException(status_code=409, detail="Synchronization retry limit reached")
    sync.sync_metadata = {**sync.sync_metadata, "retry_attempts": attempts}
    sync.status = SyncStatus.QUEUED
    sync.error_code = None
    sync.error_message = None
    db.commit()
    get_job_dispatcher().integration_sync(sync.id)
    db.refresh(sync)
    return sync


@router.get("/events", response_model=list[IntegrationEventResponse])
def events(
    db: DbSession,
    tenant: CurrentTenant,
    limit: Limit = 50,
    offset: Offset = 0,
    provider_key: Annotated[str | None, Query(max_length=80)] = None,
    severity: EventSeverity | None = None,
) -> list[IntegrationEvent]:
    statement = select(IntegrationEvent).where(IntegrationEvent.tenant_id == tenant.tenant_id)
    if provider_key:
        statement = statement.where(IntegrationEvent.provider_key == provider_key)
    if severity:
        statement = statement.where(IntegrationEvent.severity == severity)
    return list(
        db.scalars(
            statement.order_by(IntegrationEvent.created_at.desc()).limit(limit).offset(offset)
        )
    )
