from typing import Protocol

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import settings
from app.core.database import SessionLocal
from app.integrations.exceptions import IntegrationError
from app.integrations.providers import provider_registry
from app.models import ImportFile, IntegrationSync
from app.services.imports import ImportService, local_storage
from app.services.synchronization import SynchronizationService


class JobDispatcher(Protocol):
    def import_file(self, import_file_id: int) -> None: ...

    def integration_sync(self, sync_id: int) -> None: ...


def process_import_file(import_file_id: int) -> None:
    with SessionLocal() as db:
        import_file = db.get(ImportFile, import_file_id)
        if import_file is None:
            return
        service = ImportService(
            db, local_storage(settings.storage_root, settings.max_upload_size_bytes)
        )
        service.process(import_file)
        db.commit()


def execute_integration_sync(sync_id: int) -> None:
    with SessionLocal() as db:
        sync = db.get(IntegrationSync, sync_id)
        if sync is None:
            return
        try:
            SynchronizationService(db, provider_registry).execute(sync)
            db.commit()
        except IntegrationError as exc:
            if exc.retryable:
                db.commit()
            raise


if settings.job_backend == "dramatiq":
    dramatiq.set_broker(RedisBroker(url=settings.redis_url))  # type: ignore[no-untyped-call]


@dramatiq.actor(max_retries=settings.job_max_retries, min_backoff=1000, max_backoff=30000)
def process_import_file_job(import_file_id: int) -> None:
    process_import_file(import_file_id)


@dramatiq.actor(max_retries=settings.job_max_retries, min_backoff=1000, max_backoff=30000)
def execute_integration_sync_job(sync_id: int) -> None:
    execute_integration_sync(sync_id)


class SynchronousJobDispatcher:
    def import_file(self, import_file_id: int) -> None:
        process_import_file(import_file_id)

    def integration_sync(self, sync_id: int) -> None:
        execute_integration_sync(sync_id)


class DramatiqJobDispatcher:
    def import_file(self, import_file_id: int) -> None:
        process_import_file_job.send(import_file_id)

    def integration_sync(self, sync_id: int) -> None:
        execute_integration_sync_job.send(sync_id)


def get_job_dispatcher() -> JobDispatcher:
    if settings.job_backend == "dramatiq":
        return DramatiqJobDispatcher()
    return SynchronousJobDispatcher()
