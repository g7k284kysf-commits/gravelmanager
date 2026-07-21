import csv
import io
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import fitdecode  # type: ignore[import-untyped]
from app.domain.integrations import NormalizedImportRecord
from app.integrations.exceptions import ImportParseError
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class FileParser(ABC):
    @abstractmethod
    def parse(self, stream: BinaryIO) -> list[NormalizedImportRecord]: ...


class CsvFileParser(FileParser):
    def parse(self, stream: BinaryIO) -> list[NormalizedImportRecord]:
        text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
        try:
            sample = text.read(8192)
            text.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            reader = csv.DictReader(text, dialect=dialect)
            if not reader.fieldnames or len(reader.fieldnames) < 2:
                raise ImportParseError("CSV must contain at least two named columns")
            records = [
                NormalizedImportRecord(
                    record_type="csv_row",
                    source_payload=dict(row),
                    normalized_payload={
                        "columns": list(reader.fieldnames),
                        "values": dict(row),
                    },
                )
                for row in reader
            ]
        except (csv.Error, UnicodeDecodeError) as exc:
            raise ImportParseError("CSV file is malformed or is not UTF-8 encoded") from exc
        finally:
            text.detach()
        if not records:
            raise ImportParseError("CSV file contains no data rows")
        return records


class GpxFileParser(FileParser):
    def parse(self, stream: BinaryIO) -> list[NormalizedImportRecord]:
        try:
            root = ElementTree.parse(stream).getroot()
        except (ElementTree.ParseError, DefusedXmlException) as exc:
            raise ImportParseError("GPX XML is malformed") from exc
        if root is None:
            raise ImportParseError("GPX XML is empty")
        if local_name(root.tag).lower() != "gpx":
            raise ImportParseError("File does not contain a GPX document")
        points: list[dict[str, object]] = []
        for element in root.iter():
            if local_name(element.tag) != "trkpt":
                continue
            point: dict[str, object] = {
                "latitude": float(element.attrib["lat"]),
                "longitude": float(element.attrib["lon"]),
            }
            for child in element:
                name = local_name(child.tag)
                if child.text and name == "ele":
                    point["elevation_meters"] = float(child.text)
                elif child.text and name == "time":
                    point["time"] = parse_datetime(child.text).isoformat()
            points.append(point)
        if not points:
            raise ImportParseError("GPX file contains no trackpoints")
        return [
            NormalizedImportRecord(
                record_type="route",
                normalized_payload={"format": "gpx", "trackpoints": points},
            )
        ]


class TcxFileParser(FileParser):
    def parse(self, stream: BinaryIO) -> list[NormalizedImportRecord]:
        try:
            root = ElementTree.parse(stream).getroot()
        except (ElementTree.ParseError, DefusedXmlException) as exc:
            raise ImportParseError("TCX XML is malformed") from exc
        if root is None:
            raise ImportParseError("TCX XML is empty")
        if local_name(root.tag) != "TrainingCenterDatabase":
            raise ImportParseError("File does not contain a TCX document")
        records: list[NormalizedImportRecord] = []
        for activity in (item for item in root.iter() if local_name(item.tag) == "Activity"):
            trackpoints: list[dict[str, object]] = []
            for point in (item for item in activity.iter() if local_name(item.tag) == "Trackpoint"):
                values: dict[str, object] = {}
                for child in point.iter():
                    name = local_name(child.tag)
                    if child.text and name == "Time":
                        values["time"] = parse_datetime(child.text).isoformat()
                    elif child.text and name in {"AltitudeMeters", "DistanceMeters"}:
                        values[name] = float(child.text)
                if values:
                    trackpoints.append(values)
            records.append(
                NormalizedImportRecord(
                    record_type="activity",
                    external_id=activity.attrib.get("Sport"),
                    normalized_payload={
                        "format": "tcx",
                        "sport": activity.attrib.get("Sport", "Other"),
                        "trackpoints": trackpoints,
                    },
                )
            )
        if not records:
            raise ImportParseError("TCX file contains no activities")
        return records


class FitFileParser(FileParser):
    def parse(self, stream: BinaryIO) -> list[NormalizedImportRecord]:
        sessions: list[dict[str, object]] = []
        records: list[dict[str, object]] = []
        try:
            with fitdecode.FitReader(stream) as fit:
                for frame in fit:
                    if not isinstance(frame, fitdecode.FitDataMessage):
                        continue
                    values = {
                        field.name: field.value for field in frame.fields if field.value is not None
                    }
                    if frame.name == "session":
                        sessions.append(values)
                    elif frame.name == "record":
                        records.append(values)
        except Exception as exc:
            raise ImportParseError("FIT file could not be decoded") from exc
        if not sessions and not records:
            raise ImportParseError("FIT file contains no activity data")
        return [
            NormalizedImportRecord(
                record_type="activity",
                normalized_payload={
                    "format": "fit",
                    "sessions": serialize_fit_values(sessions),
                    "records": serialize_fit_values(records),
                },
            )
        ]


def serialize_fit_values(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [{key: json_safe(value) for key, value in item.items()} for item in items]


def json_safe(value: object) -> object:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat() if value.tzinfo else value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


PARSERS: dict[str, FileParser] = {
    "csv": CsvFileParser(),
    "gpx": GpxFileParser(),
    "tcx": TcxFileParser(),
    "fit": FitFileParser(),
}


def parser_for(filename_or_extension: str) -> FileParser:
    extension = Path(filename_or_extension).suffix.lower().removeprefix(".")
    extension = extension or filename_or_extension.lower().removeprefix(".")
    try:
        return PARSERS[extension]
    except KeyError as exc:
        raise ImportParseError("No parser is registered for this file type") from exc
