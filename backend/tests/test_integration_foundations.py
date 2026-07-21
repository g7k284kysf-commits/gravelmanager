from datetime import UTC, datetime
from io import BytesIO

import pytest
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
    build_provider_registry,
)
from app.integrations.storage import LocalObjectStorage, sanitize_filename


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
    tmp_path: pytest.TempPathFactory,
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


class DeterministicProvider(IntegrationProvider):
    provider_key = "deterministic"
    display_name = "Deterministic test provider"
    capabilities = frozenset({IntegrationCapability.POLLING, IntegrationCapability.ACTIVITY_IMPORT})

    def start_sync(
        self, cursor: str | None = None
    ) -> tuple[list[NormalizedImportRecord], str | None]:
        return [
            NormalizedImportRecord(
                record_type="activity",
                normalized_payload={"started_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat()},
            )
        ], "next-cursor"


def deterministic_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(DeterministicProvider())
    return registry
