from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConnectionStatus(StrEnum):
    DISCONNECTED = "disconnected"
    PENDING = "pending"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"
    REVOKED = "revoked"


class SyncStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncType(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"
    MANUAL = "manual"
    WEBHOOK = "webhook"
    FILE_IMPORT = "file_import"


class ImportFileStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class ImportRecordStatus(StrEnum):
    DISCOVERED = "discovered"
    NORMALIZED = "normalized"
    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"
    FAILED = "failed"


class EventSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "athlete_id", "provider_key", name="uq_connection_provider"),
        Index("ix_connection_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider_key: Mapped[str] = mapped_column(String(80))
    display_name: Mapped[str] = mapped_column(String(160))
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, native_enum=False, length=30), default=ConnectionStatus.PENDING
    )
    external_account_id: Mapped[str | None] = mapped_column(String(255))
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    encrypted_credentials: Mapped[str | None] = mapped_column(Text)
    configuration: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntegrationSync(Base):
    __tablename__ = "integration_syncs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_sync_idempotency"),
        Index("ix_sync_provider_status", "tenant_id", "provider_key", "status"),
        Index("ix_sync_connection_requested", "connection_id", "requested_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="CASCADE")
    )
    provider_key: Mapped[str] = mapped_column(String(80))
    sync_type: Mapped[SyncType] = mapped_column(Enum(SyncType, native_enum=False, length=30))
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, native_enum=False, length=30), default=SyncStatus.QUEUED
    )
    idempotency_key: Mapped[str] = mapped_column(String(120))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cursor_before: Mapped[str | None] = mapped_column(String(500))
    cursor_after: Mapped[str | None] = mapped_column(String(500))
    records_discovered: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(500))
    sync_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSON, default=dict)


class ImportFile(Base):
    __tablename__ = "import_files"
    __table_args__ = (
        UniqueConstraint("tenant_id", "athlete_id", "checksum_sha256", name="uq_import_checksum"),
        Index("ix_import_tenant_uploaded", "tenant_id", "uploaded_at"),
        Index("ix_import_status", "tenant_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="SET NULL")
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    file_extension: Mapped[str] = mapped_column(String(12))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[ImportFileStatus] = mapped_column(
        Enum(ImportFileStatus, native_enum=False, length=40), default=ImportFileStatus.UPLOADED
    )
    detected_format: Mapped[str | None] = mapped_column(String(30))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(500))
    file_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSON, default=dict)


class ImportRecord(Base):
    __tablename__ = "import_records"
    __table_args__ = (Index("ix_import_record_file_status", "import_file_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    import_file_id: Mapped[int] = mapped_column(ForeignKey("import_files.id", ondelete="CASCADE"))
    external_id: Mapped[str | None] = mapped_column(String(255))
    record_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[ImportRecordStatus] = mapped_column(
        Enum(ImportRecordStatus, native_enum=False, length=30)
    )
    source_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    normalized_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    linked_entity_type: Mapped[str | None] = mapped_column(String(80))
    linked_entity_id: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class IntegrationEvent(Base):
    __tablename__ = "integration_events"
    __table_args__ = (
        Index("ix_event_tenant_created", "tenant_id", "created_at"),
        Index("ix_event_provider_severity", "provider_key", "severity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    athlete_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    provider_key: Mapped[str] = mapped_column(String(80))
    event_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity, native_enum=False, length=20), default=EventSeverity.INFO
    )
    connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_connections.id", ondelete="SET NULL")
    )
    sync_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_syncs.id", ondelete="SET NULL")
    )
    import_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_files.id", ondelete="SET NULL")
    )
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    message: Mapped[str] = mapped_column(String(500))
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
