from abc import ABC
from dataclasses import dataclass

from app.domain.integrations import IntegrationCapability, NormalizedImportRecord
from app.integrations.exceptions import ProviderNotFoundError, ProviderOperationNotSupported


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    provider_key: str
    display_name: str
    capabilities: tuple[IntegrationCapability, ...]
    availability: str
    description: str
    operational: bool


@dataclass(frozen=True, slots=True)
class ProviderSyncResult:
    records: tuple[NormalizedImportRecord, ...]
    cursor: str | None
    records_created: int
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0

    def __post_init__(self) -> None:
        counts = (
            self.records_created,
            self.records_updated,
            self.records_skipped,
            self.records_failed,
        )
        if any(count < 0 for count in counts):
            raise ValueError("Provider sync counters cannot be negative")
        if self.records_created + self.records_updated > len(self.records):
            raise ValueError("Successful sync counters exceed normalized records")

    @property
    def records_discovered(self) -> int:
        return sum(
            (
                self.records_created,
                self.records_updated,
                self.records_skipped,
                self.records_failed,
            )
        )


class IntegrationProvider(ABC):
    provider_key: str
    display_name: str
    capabilities: frozenset[IntegrationCapability] = frozenset()
    availability = "coming_soon"
    description = "Provider foundation is available; live connectivity is not enabled."
    operational = False

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_key=self.provider_key,
            display_name=self.display_name,
            capabilities=tuple(sorted(self.capabilities, key=str)),
            availability=self.availability,
            description=self.description,
            operational=self.operational,
        )

    def supports(self, capability: IntegrationCapability) -> bool:
        return capability in self.capabilities

    def validate_configuration(self, configuration: dict[str, object]) -> None:
        if not isinstance(configuration, dict):
            raise ValueError("Provider configuration must be an object")

    def authorize(self, credentials: dict[str, object]) -> dict[str, object]:
        raise ProviderOperationNotSupported("Authorization is not available for this provider")

    def refresh_authorization(self, credentials: dict[str, object]) -> dict[str, object]:
        raise ProviderOperationNotSupported("Authorization refresh is not available")

    def revoke_authorization(self) -> None:
        return None

    def test_connection(self) -> bool:
        raise ProviderOperationNotSupported("Connection testing is not available")

    def start_sync(self, cursor: str | None = None) -> ProviderSyncResult:
        raise ProviderOperationNotSupported("Synchronization is not available")

    def import_file(self, storage_key: str) -> list[NormalizedImportRecord]:
        raise ProviderOperationNotSupported("File import is not available")


class PlaceholderProvider(IntegrationProvider):
    def __init__(
        self,
        provider_key: str,
        display_name: str,
        capabilities: frozenset[IntegrationCapability],
    ) -> None:
        self.provider_key = provider_key
        self.display_name = display_name
        self.capabilities = capabilities


class ManualUploadProvider(PlaceholderProvider):
    availability = "manual_import_only"
    description = "Upload FIT, TCX, GPX, or CSV files manually."
    operational = True

    def __init__(self) -> None:
        super().__init__(
            "manual_upload",
            "Manual upload",
            frozenset(
                {
                    IntegrationCapability.FILE_IMPORT,
                    IntegrationCapability.ACTIVITY_IMPORT,
                    IntegrationCapability.ROUTE_IMPORT,
                }
            ),
        )

    def test_connection(self) -> bool:
        return True


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, IntegrationProvider] = {}

    def register(self, provider: IntegrationProvider) -> None:
        if provider.provider_key in self._providers:
            raise ValueError(f"Provider key already registered: {provider.provider_key}")
        self._providers[provider.provider_key] = provider

    def get(self, provider_key: str) -> IntegrationProvider:
        try:
            return self._providers[provider_key]
        except KeyError as exc:
            raise ProviderNotFoundError("Unknown integration provider") from exc

    def list(self) -> list[ProviderMetadata]:
        return [self._providers[key].metadata() for key in sorted(self._providers)]


def build_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(ManualUploadProvider())
    registry.register(
        PlaceholderProvider(
            "garmin",
            "Garmin Connect",
            frozenset(
                {
                    IntegrationCapability.OAUTH,
                    IntegrationCapability.ACTIVITY_IMPORT,
                    IntegrationCapability.WELLNESS_IMPORT,
                    IntegrationCapability.POLLING,
                }
            ),
        )
    )
    registry.register(
        PlaceholderProvider(
            "trainingpeaks",
            "TrainingPeaks",
            frozenset(
                {
                    IntegrationCapability.OAUTH,
                    IntegrationCapability.ACTIVITY_IMPORT,
                    IntegrationCapability.PLANNED_WORKOUT_IMPORT,
                    IntegrationCapability.PLANNED_WORKOUT_EXPORT,
                }
            ),
        )
    )
    registry.register(
        PlaceholderProvider(
            "core",
            "CORE",
            frozenset(
                {
                    IntegrationCapability.OAUTH,
                    IntegrationCapability.HEALTH_METRICS_IMPORT,
                    IntegrationCapability.POLLING,
                }
            ),
        )
    )
    return registry


provider_registry = build_provider_registry()
