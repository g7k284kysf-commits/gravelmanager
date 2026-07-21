import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from app.integrations.exceptions import StorageValidationError

ALLOWED_CONTENT_TYPES: dict[str, frozenset[str]] = {
    ".fit": frozenset({"application/octet-stream", "application/vnd.ant.fit"}),
    ".tcx": frozenset({"application/xml", "text/xml", "application/vnd.garmin.tcx+xml"}),
    ".gpx": frozenset({"application/gpx+xml", "application/xml", "text/xml"}),
    ".csv": frozenset({"text/csv", "application/csv", "text/plain"}),
}


@dataclass(frozen=True, slots=True)
class StoredObject:
    storage_key: str
    original_filename: str
    content_type: str
    file_extension: str
    size_bytes: int
    checksum_sha256: str


class ObjectStorage(Protocol):
    def save(
        self,
        tenant_id: int,
        athlete_id: int,
        filename: str,
        content_type: str,
        stream: BinaryIO,
    ) -> StoredObject: ...

    def open(self, storage_key: str) -> BinaryIO: ...

    def delete(self, storage_key: str) -> None: ...


def sanitize_filename(filename: str) -> str:
    basename = Path(filename.replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", basename).strip(" .")
    if not cleaned:
        raise StorageValidationError("Filename is empty after sanitization")
    return cleaned[:255]


class LocalObjectStorage:
    def __init__(self, root: str | Path, max_size_bytes: int) -> None:
        self.root = Path(root).expanduser().resolve()
        self.max_size_bytes = max_size_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        tenant_id: int,
        athlete_id: int,
        filename: str,
        content_type: str,
        stream: BinaryIO,
    ) -> StoredObject:
        safe_name = sanitize_filename(filename)
        extension = Path(safe_name).suffix.lower()
        if extension not in ALLOWED_CONTENT_TYPES:
            raise StorageValidationError("Supported file types are FIT, TCX, GPX, and CSV")
        if content_type.lower() not in ALLOWED_CONTENT_TYPES[extension]:
            raise StorageValidationError(
                f"Content type {content_type!r} does not match {extension}"
            )

        storage_key = f"{tenant_id}/{athlete_id}/{uuid4().hex}{extension}"
        destination = self._resolve_key(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        try:
            with destination.open("xb") as output:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_size_bytes:
                        raise StorageValidationError(
                            f"File exceeds the {self.max_size_bytes}-byte upload limit"
                        )
                    digest.update(chunk)
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        if size == 0:
            destination.unlink(missing_ok=True)
            raise StorageValidationError("Uploaded file is empty")
        return StoredObject(
            storage_key=storage_key,
            original_filename=safe_name,
            content_type=content_type.lower(),
            file_extension=extension.removeprefix("."),
            size_bytes=size,
            checksum_sha256=digest.hexdigest(),
        )

    def open(self, storage_key: str) -> BinaryIO:
        return self._resolve_key(storage_key).open("rb")

    def delete(self, storage_key: str) -> None:
        self._resolve_key(storage_key).unlink(missing_ok=True)

    def _resolve_key(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise StorageValidationError("Invalid storage key")
        return candidate
