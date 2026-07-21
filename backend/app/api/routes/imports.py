from typing import Annotated
from uuid import uuid4

from app.api.deps import CurrentTenant, DbSession
from app.core.config import settings
from app.integrations.exceptions import DuplicateImportError, StorageValidationError
from app.jobs import get_job_dispatcher
from app.models import ImportFile, ImportRecord
from app.models.integration import ImportFileStatus
from app.schemas.integration import (
    ImportFileResponse,
    ImportRecordResponse,
    ProcessResponse,
)
from app.services.audit import IntegrationAuditService
from app.services.imports import ImportService, local_storage
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select

router = APIRouter(prefix="/imports", tags=["File Imports"])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
UploadedFile = Annotated[UploadFile, File(description="FIT, TCX, GPX, or CSV file")]


def owned_import(import_file_id: int, db: DbSession, tenant: CurrentTenant) -> ImportFile:
    import_file = db.scalar(
        select(ImportFile).where(
            ImportFile.id == import_file_id,
            ImportFile.tenant_id == tenant.tenant_id,
            ImportFile.athlete_id == tenant.athlete_id,
        )
    )
    if import_file is None:
        raise HTTPException(status_code=404, detail="Import file not found")
    return import_file


@router.post(
    "/files",
    response_model=ImportFileResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_file(file: UploadedFile, db: DbSession, tenant: CurrentTenant) -> ImportFile:
    service = ImportService(
        db, local_storage(settings.storage_root, settings.max_upload_size_bytes)
    )
    try:
        imported = service.upload(
            tenant_id=tenant.tenant_id,
            athlete_id=tenant.athlete_id,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            stream=file.file,
        )
        db.commit()
        db.refresh(imported)
        return imported
    except DuplicateImportError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": exc.code,
                "message": str(exc),
                "existing_import_id": exc.existing_import_id,
            },
        ) from exc
    except StorageValidationError as exc:
        db.rollback()
        IntegrationAuditService(db).record(
            tenant_id=tenant.tenant_id,
            athlete_id=tenant.athlete_id,
            provider_key="manual_upload",
            event_type="file_rejected",
            message="File upload rejected by validation",
            correlation_id=str(uuid4()),
            details={"error_code": exc.code},
        )
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/files", response_model=list[ImportFileResponse])
def files(
    db: DbSession,
    tenant: CurrentTenant,
    limit: Limit = 50,
    offset: Offset = 0,
    file_status: ImportFileStatus | None = None,
) -> list[ImportFile]:
    statement = select(ImportFile).where(
        ImportFile.tenant_id == tenant.tenant_id,
        ImportFile.athlete_id == tenant.athlete_id,
    )
    if file_status:
        statement = statement.where(ImportFile.status == file_status)
    return list(
        db.scalars(statement.order_by(ImportFile.uploaded_at.desc()).limit(limit).offset(offset))
    )


@router.get("/files/{import_file_id}", response_model=ImportFileResponse)
def get_file(import_file_id: int, db: DbSession, tenant: CurrentTenant) -> ImportFile:
    return owned_import(import_file_id, db, tenant)


@router.get("/files/{import_file_id}/records", response_model=list[ImportRecordResponse])
def records(
    import_file_id: int,
    db: DbSession,
    tenant: CurrentTenant,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[ImportRecord]:
    owned_import(import_file_id, db, tenant)
    return list(
        db.scalars(
            select(ImportRecord)
            .where(
                ImportRecord.import_file_id == import_file_id,
                ImportRecord.tenant_id == tenant.tenant_id,
                ImportRecord.athlete_id == tenant.athlete_id,
            )
            .order_by(ImportRecord.id)
            .limit(limit)
            .offset(offset)
        )
    )


@router.post(
    "/files/{import_file_id}/process",
    response_model=ProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def process_file(import_file_id: int, db: DbSession, tenant: CurrentTenant) -> ProcessResponse:
    imported = owned_import(import_file_id, db, tenant)
    service = ImportService(
        db, local_storage(settings.storage_root, settings.max_upload_size_bytes)
    )
    try:
        service.queue(imported)
    except StorageValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    get_job_dispatcher().import_file(imported.id)
    db.refresh(imported)
    return ProcessResponse(
        id=imported.id,
        status=imported.status,
        correlation_id=imported.correlation_id,
        message=(
            "Import completed" if imported.status == ImportFileStatus.SUCCEEDED else "Import queued"
        ),
    )
