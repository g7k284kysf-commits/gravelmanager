from datetime import UTC, datetime
from typing import BinaryIO
from uuid import uuid4

from app.domain.integrations import NormalizedImportRecord
from app.integrations.exceptions import (
    DuplicateImportError,
    ImportParseError,
    StorageValidationError,
)
from app.integrations.parsers import parser_for
from app.integrations.storage import LocalObjectStorage, ObjectStorage
from app.models import ImportFile, ImportRecord
from app.models.integration import (
    EventSeverity,
    ImportFileStatus,
    ImportRecordStatus,
)
from app.services.audit import IntegrationAuditService
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class ImportService:
    def __init__(self, db: Session, storage: ObjectStorage) -> None:
        self.db = db
        self.storage = storage
        self.audit = IntegrationAuditService(db)

    def upload(
        self,
        *,
        tenant_id: int,
        athlete_id: int,
        filename: str,
        content_type: str,
        stream: BinaryIO,
        connection_id: int | None = None,
    ) -> ImportFile:
        stored = self.storage.save(tenant_id, athlete_id, filename, content_type, stream)
        duplicate = self.db.scalar(
            select(ImportFile).where(
                ImportFile.tenant_id == tenant_id,
                ImportFile.athlete_id == athlete_id,
                ImportFile.checksum_sha256 == stored.checksum_sha256,
            )
        )
        if duplicate is not None:
            self.storage.delete(stored.storage_key)
            self.audit.record(
                tenant_id=tenant_id,
                athlete_id=athlete_id,
                provider_key="manual_upload",
                event_type="duplicate_import_detected",
                message="An identical file was already uploaded",
                correlation_id=duplicate.correlation_id,
                import_file_id=duplicate.id,
                severity=EventSeverity.WARNING,
            )
            self.db.commit()
            raise DuplicateImportError(duplicate.id)

        correlation_id = str(uuid4())
        import_file = ImportFile(
            tenant_id=tenant_id,
            athlete_id=athlete_id,
            connection_id=connection_id,
            original_filename=stored.original_filename,
            storage_key=stored.storage_key,
            content_type=stored.content_type,
            file_extension=stored.file_extension,
            file_size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            status=ImportFileStatus.UPLOADED,
            detected_format=stored.file_extension,
            correlation_id=correlation_id,
            file_metadata={},
        )
        self.db.add(import_file)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            self.storage.delete(stored.storage_key)
            duplicate = self.db.scalar(
                select(ImportFile).where(
                    ImportFile.tenant_id == tenant_id,
                    ImportFile.athlete_id == athlete_id,
                    ImportFile.checksum_sha256 == stored.checksum_sha256,
                )
            )
            if duplicate is None:
                raise
            self._record_duplicate(duplicate)
            self.db.commit()
            raise DuplicateImportError(duplicate.id) from exc
        self.audit.record(
            tenant_id=tenant_id,
            athlete_id=athlete_id,
            provider_key="manual_upload",
            event_type="file_uploaded",
            message="File accepted for import",
            correlation_id=correlation_id,
            import_file_id=import_file.id,
            details={"format": stored.file_extension, "size_bytes": stored.size_bytes},
        )
        return import_file

    def queue(self, import_file: ImportFile) -> None:
        if import_file.status not in {
            ImportFileStatus.UPLOADED,
            ImportFileStatus.FAILED,
        }:
            raise StorageValidationError(
                f"Import cannot be queued from status {import_file.status.value}"
            )
        import_file.status = ImportFileStatus.QUEUED
        import_file.error_code = None
        import_file.error_message = None
        self.audit.record(
            tenant_id=import_file.tenant_id,
            athlete_id=import_file.athlete_id,
            provider_key="manual_upload",
            event_type="import_queued",
            message="Import queued for processing",
            correlation_id=import_file.correlation_id,
            import_file_id=import_file.id,
        )

    def process(self, import_file: ImportFile) -> ImportFile:
        if import_file.status != ImportFileStatus.QUEUED:
            raise StorageValidationError(
                f"Import cannot run from status {import_file.status.value}"
            )
        import_file.status = ImportFileStatus.PROCESSING
        import_file.processing_started_at = datetime.now(UTC)
        self.db.flush()
        try:
            with self.storage.open(import_file.storage_key) as stream:
                parsed = parser_for(import_file.file_extension).parse(stream)
            self._persist_records(import_file, parsed)
            import_file.status = ImportFileStatus.SUCCEEDED
            import_file.processing_completed_at = datetime.now(UTC)
            import_file.file_metadata = {
                "records_discovered": len(parsed),
                "records_created": len(parsed),
                "records_updated": 0,
                "records_skipped": 0,
                "records_failed": 0,
            }
            self.audit.record(
                tenant_id=import_file.tenant_id,
                athlete_id=import_file.athlete_id,
                provider_key="manual_upload",
                event_type="import_completed",
                message="Import completed successfully",
                correlation_id=import_file.correlation_id,
                import_file_id=import_file.id,
                details={"records_created": len(parsed)},
            )
        except ImportParseError as exc:
            self._mark_failed(import_file, exc.code, str(exc))
        except OSError:
            self._mark_failed(import_file, "storage_read_error", "Stored upload could not be read")
        except Exception:
            self._mark_failed(
                import_file, "unexpected_import_error", "Import processing failed safely"
            )
        return import_file

    def _record_duplicate(self, duplicate: ImportFile) -> None:
        self.audit.record(
            tenant_id=duplicate.tenant_id,
            athlete_id=duplicate.athlete_id,
            provider_key="manual_upload",
            event_type="duplicate_import_detected",
            message="An identical file was already uploaded",
            correlation_id=duplicate.correlation_id,
            import_file_id=duplicate.id,
            severity=EventSeverity.WARNING,
        )

    def _mark_failed(self, import_file: ImportFile, error_code: str, error_message: str) -> None:
        import_file.status = ImportFileStatus.FAILED
        import_file.processing_completed_at = datetime.now(UTC)
        import_file.error_code = error_code
        import_file.error_message = error_message[:500]
        self.audit.record(
            tenant_id=import_file.tenant_id,
            athlete_id=import_file.athlete_id,
            provider_key="manual_upload",
            event_type="import_failed",
            message="Import processing failed",
            correlation_id=import_file.correlation_id,
            import_file_id=import_file.id,
            severity=EventSeverity.ERROR,
            details={"error_code": error_code},
        )

    def _persist_records(
        self, import_file: ImportFile, records: list[NormalizedImportRecord]
    ) -> None:
        self.db.execute(delete(ImportRecord).where(ImportRecord.import_file_id == import_file.id))
        self.db.add_all(
            [
                ImportRecord(
                    tenant_id=import_file.tenant_id,
                    athlete_id=import_file.athlete_id,
                    import_file_id=import_file.id,
                    external_id=record.external_id,
                    record_type=record.record_type,
                    status=ImportRecordStatus.CREATED,
                    source_payload=record.source_payload,
                    normalized_payload=record.normalized_payload,
                )
                for record in records
            ]
        )


def local_storage(root: str, max_size_bytes: int) -> LocalObjectStorage:
    return LocalObjectStorage(root, max_size_bytes)
