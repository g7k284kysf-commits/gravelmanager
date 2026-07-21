from datetime import datetime

from app.domain.integrations import IntegrationCapability
from app.models.integration import (
    ConnectionStatus,
    EventSeverity,
    ImportFileStatus,
    ImportRecordStatus,
    SyncStatus,
    SyncType,
)
from pydantic import BaseModel, ConfigDict, Field


class ProviderResponse(BaseModel):
    provider_key: str
    display_name: str
    capabilities: tuple[IntegrationCapability, ...]
    availability: str
    description: str


class ConnectionCreate(BaseModel):
    provider_key: str = Field(min_length=2, max_length=80)
    display_name: str | None = Field(default=None, max_length=160)
    scopes: list[str] = Field(default_factory=list, max_length=50)
    configuration: dict[str, object] = Field(default_factory=dict)
    credentials: dict[str, object] | None = Field(default=None, repr=False)


class ConnectionUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    scopes: list[str] | None = Field(default=None, max_length=50)
    configuration: dict[str, object] | None = None
    credentials: dict[str, object] | None = Field(default=None, repr=False)


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    athlete_id: int
    provider_key: str
    display_name: str
    status: ConnectionStatus
    external_account_id: str | None
    scopes: list[str]
    configuration: dict[str, object]
    last_successful_sync_at: datetime | None
    last_sync_attempt_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None


class ConnectionTestResponse(BaseModel):
    supported: bool
    succeeded: bool
    message: str


class SyncRequest(BaseModel):
    sync_type: SyncType = SyncType.MANUAL
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class SyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    athlete_id: int
    connection_id: int
    provider_key: str
    sync_type: SyncType
    status: SyncStatus
    idempotency_key: str
    correlation_id: str
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    cursor_before: str | None
    cursor_after: str | None
    records_discovered: int
    records_created: int
    records_updated: int
    records_skipped: int
    records_failed: int
    error_code: str | None
    error_message: str | None
    metadata: dict[str, object] = Field(validation_alias="sync_metadata")


class ImportFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    athlete_id: int
    connection_id: int | None
    original_filename: str
    content_type: str
    file_extension: str
    file_size_bytes: int
    checksum_sha256: str
    status: ImportFileStatus
    detected_format: str | None
    correlation_id: str
    uploaded_at: datetime
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    metadata: dict[str, object] = Field(validation_alias="file_metadata")


class ImportRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    import_file_id: int
    external_id: str | None
    record_type: str
    status: ImportRecordStatus
    normalized_payload: dict[str, object] | None
    linked_entity_type: str | None
    linked_entity_id: int | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class IntegrationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    provider_key: str
    event_type: str
    severity: EventSeverity
    connection_id: int | None
    sync_id: int | None
    import_file_id: int | None
    correlation_id: str
    message: str
    details: dict[str, object]
    created_at: datetime


class ProcessResponse(BaseModel):
    id: int
    status: ImportFileStatus | SyncStatus
    correlation_id: str
    message: str
