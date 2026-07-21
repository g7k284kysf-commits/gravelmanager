from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest
from app.core.config import Settings
from app.domain.integrations import IntegrationCapability, NormalizedImportRecord
from app.integrations.credentials import CredentialEncryptionService
from app.integrations.exceptions import (
    CredentialConfigurationError,
    ImportParseError,
    ProviderOperationNotSupported,
    StorageValidationError,
)
from app.integrations.parsers import CsvFileParser, FitFileParser, GpxFileParser, TcxFileParser
from app.integrations.providers import (
    IntegrationProvider,
    ManualUploadProvider,
    ProviderRegistry,
    ProviderSyncResult,
    build_provider_registry,
)
from app.integrations.storage import LocalObjectStorage, sanitize_filename
from cryptography.fernet import Fernet
from pydantic import ValidationError


def test_provider_registry_metadata_capabilities_and_duplicates() -> None:
    registry = build_provider_registry()
    providers = registry.list()

    assert [provider.provider_key for provider in providers] == [
        "core",
        "garmin",
        "manual_upload",
        "trainingpeaks",
    ]
    manual = registry.get("manual_upload")
    assert manual.supports(IntegrationCapability.FILE_IMPORT)
    assert manual.metadata().availability == "manual_import_only"
    assert manual.metadata().operational is True
    assert all(
        provider.operational is False
        for provider in providers
        if provider.provider_key != "manual_upload"
    )
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ManualUploadProvider())
    with pytest.raises(ProviderOperationNotSupported):
        manual.start_sync()


def test_credential_encryption_round_trip_and_invalid_keys() -> None:
    service = CredentialEncryptionService("MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    encrypted = service.encrypt({"access_token": "secret", "refresh_token": "private"})

    assert "secret" not in encrypted
    assert service.decrypt(encrypted) == {
        "access_token": "secret",
        "refresh_token": "private",
    }
    with pytest.raises(CredentialConfigurationError):
        CredentialEncryptionService("not-a-key")
    with pytest.raises(CredentialConfigurationError):
        service.decrypt("v1:tampered")


def test_local_storage_validates_type_size_and_path_safety(
    tmp_path: Path,
) -> None:
    storage = LocalObjectStorage(tmp_path, max_size_bytes=20)
    stored = storage.save(
        4,
        8,
        "../unsafe route.gpx",
        "application/gpx+xml",
        BytesIO(b"<gpx></gpx>"),
    )

    assert stored.original_filename == "unsafe route.gpx"
    assert stored.storage_key.startswith("4/8/")
    with storage.open(stored.storage_key) as uploaded:
        assert uploaded.read() == b"<gpx></gpx>"
    assert sanitize_filename("../../ride.csv") == "ride.csv"
    with pytest.raises(StorageValidationError, match="Invalid storage key"):
        storage.open("../../outside.csv")
    with pytest.raises(StorageValidationError, match="does not match"):
        storage.save(4, 8, "ride.csv", "image/png", BytesIO(b"a,b\n1,2"))
    with pytest.raises(StorageValidationError, match="upload limit"):
        storage.save(4, 8, "ride.csv", "text/csv", BytesIO(b"a" * 21))


def test_local_storage_rejects_spoofed_content_and_cleans_partial_files(
    tmp_path: Path,
) -> None:
    storage = LocalObjectStorage(tmp_path, max_size_bytes=1024)
    with pytest.raises(StorageValidationError, match="GPX format"):
        storage.save(
            4,
            8,
            "../../apparently-safe.gpx",
            "application/octet-stream",
            BytesIO(b"date,tss\n2026-01-01,80\n"),
        )
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_csv_parser_detects_delimiter_and_preserves_columns() -> None:
    records = CsvFileParser().parse(BytesIO(b"date;tss\n2026-01-01;80\n"))
    assert records[0].normalized_payload["columns"] == ["date", "tss"]
    assert records[0].normalized_payload["values"] == {
        "date": "2026-01-01",
        "tss": "80",
    }
    with pytest.raises(ImportParseError):
        CsvFileParser().parse(BytesIO(b"only-one-column\nvalue\n"))


def test_gpx_parser_extracts_safe_trackpoints_and_rejects_entities() -> None:
    gpx = b"""<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
    <trk><trkseg><trkpt lat="52.1" lon="5.1"><ele>12.3</ele>
    <time>2026-01-01T08:00:00Z</time></trkpt></trkseg></trk></gpx>"""
    record = GpxFileParser().parse(BytesIO(gpx))[0]
    point = record.normalized_payload["trackpoints"][0]
    assert point["latitude"] == 52.1
    assert point["time"].endswith("+00:00")
    malicious = b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><gpx>&xxe;</gpx>'
    with pytest.raises(ImportParseError, match="GPX XML is malformed"):
        GpxFileParser().parse(BytesIO(malicious))
    with pytest.raises(ImportParseError, match="invalid trackpoint"):
        GpxFileParser().parse(BytesIO(b"<gpx><trkpt lon='5.1'/></gpx>"))


def test_tcx_parser_extracts_activity_and_trackpoint() -> None:
    tcx = b"""<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
    <Activities><Activity Sport="Biking"><Id>2026-01-01T08:00:00Z</Id><Lap>
    <Track><Trackpoint><Time>2026-01-01T08:00:00Z</Time>
    <DistanceMeters>1234</DistanceMeters></Trackpoint></Track></Lap></Activity></Activities>
    </TrainingCenterDatabase>"""
    record = TcxFileParser().parse(BytesIO(tcx))[0]
    assert record.normalized_payload["sport"] == "Biking"
    assert record.normalized_payload["trackpoints"][0]["DistanceMeters"] == 1234


def test_fit_parser_rejects_malformed_content() -> None:
    with pytest.raises(ImportParseError, match="could not be decoded"):
        FitFileParser().parse(BytesIO(b"not-a-fit-file"))


def test_production_settings_require_real_secrets_and_async_jobs() -> None:
    with pytest.raises(ValidationError, match="CREDENTIAL_ENCRYPTION_KEY"):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret="production-jwt-secret-that-is-long-enough",
            job_backend="dramatiq",
        )
    with pytest.raises(ValidationError, match="JOB_BACKEND"):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret="production-jwt-secret-that-is-long-enough",
            credential_encryption_key=Fernet.generate_key().decode(),
            job_backend="sync",
        )


class DeterministicProvider(IntegrationProvider):
    provider_key = "deterministic"
    display_name = "Deterministic test provider"
    capabilities = frozenset({IntegrationCapability.POLLING, IntegrationCapability.ACTIVITY_IMPORT})
    operational = True

    def start_sync(self, cursor: str | None = None) -> ProviderSyncResult:
        return ProviderSyncResult(
            records=(
                NormalizedImportRecord(
                    record_type="activity",
                    normalized_payload={"started_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat()},
                ),
            ),
            cursor="next-cursor",
            records_created=1,
        )


def deterministic_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(DeterministicProvider())
    return registry
