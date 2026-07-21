import json
import logging

from app.models.integration import EventSeverity, IntegrationEvent
from sqlalchemy.orm import Session

logger = logging.getLogger("gravel_manager.integrations")


class IntegrationAuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        tenant_id: int,
        athlete_id: int | None,
        provider_key: str,
        event_type: str,
        message: str,
        correlation_id: str,
        severity: EventSeverity = EventSeverity.INFO,
        connection_id: int | None = None,
        sync_id: int | None = None,
        import_file_id: int | None = None,
        details: dict[str, object] | None = None,
    ) -> IntegrationEvent:
        safe_details = details or {}
        event = IntegrationEvent(
            tenant_id=tenant_id,
            athlete_id=athlete_id,
            provider_key=provider_key,
            event_type=event_type,
            severity=severity,
            connection_id=connection_id,
            sync_id=sync_id,
            import_file_id=import_file_id,
            correlation_id=correlation_id,
            message=message,
            details=safe_details,
        )
        self.db.add(event)
        logger.info(
            json.dumps(
                {
                    "event": event_type,
                    "tenant_id": tenant_id,
                    "provider_key": provider_key,
                    "correlation_id": correlation_id,
                    "severity": severity.value,
                    "details": safe_details,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return event
