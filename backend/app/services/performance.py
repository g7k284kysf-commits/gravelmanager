import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.core.config import settings
from app.domain.performance import CalculatedMetric, calculate_timeline
from app.models import DailyPerformanceMetric
from app.repositories.performance import PerformanceMetricsRepository
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class RecalculationResult:
    recalculated_from: date | None
    recalculated_through: date | None
    rows_written: int


class PerformanceCalculationService:
    """Coordinates deterministic metric calculation and idempotent persistence."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = PerformanceMetricsRepository(session)

    def recalculate(
        self, tenant_id: int, user_id: int, start_date: date | None = None
    ) -> RecalculationResult:
        first_training, last_training = self.repository.training_bounds(tenant_id, user_id)
        if first_training is None or last_training is None:
            self.repository.delete_all(tenant_id, user_id)
            logger.info("Cleared performance metrics for user %s with no training history", user_id)
            return RecalculationResult(None, None, 0)

        self.repository.delete_before(tenant_id, user_id, first_training)
        timeline_end = max(date.today(), last_training)
        loads = self.repository.daily_loads(tenant_id, user_id, first_training, timeline_end)
        calculated = calculate_timeline(
            loads,
            first_training,
            timeline_end,
            ctl_days=settings.ctl_time_constant_days,
            atl_days=settings.atl_time_constant_days,
        )
        effective_start = max(first_training, start_date) if start_date else first_training
        metrics_to_write = [
            metric for metric in calculated if metric.metric_date >= effective_start
        ]
        existing = self.repository.existing_from(tenant_id, user_id, effective_start)
        for metric in metrics_to_write:
            row = existing.get(metric.metric_date)
            if row is None:
                row = DailyPerformanceMetric(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    metric_date=metric.metric_date,
                )
                self.session.add(row)
            self._copy_values(row, metric)

        logger.info(
            "Recalculated %s performance rows for user %s from %s through %s",
            len(metrics_to_write),
            user_id,
            effective_start,
            timeline_end,
        )
        return RecalculationResult(effective_start, timeline_end, len(metrics_to_write))

    @staticmethod
    def _copy_values(row: DailyPerformanceMetric, metric: CalculatedMetric) -> None:
        row.daily_tss = metric.daily_tss
        row.ctl = metric.ctl
        row.atl = metric.atl
        row.tsb = metric.tsb
        row.seven_day_tss = metric.seven_day_tss
        row.twenty_eight_day_tss = metric.twenty_eight_day_tss
        row.seven_day_training_hours = metric.seven_day_training_hours
        row.twenty_eight_day_training_hours = metric.twenty_eight_day_training_hours
        row.ramp_rate = metric.ramp_rate


def twenty_eight_day_ctl_change(
    repository: PerformanceMetricsRepository,
    tenant_id: int,
    user_id: int,
    current: DailyPerformanceMetric,
) -> Decimal:
    prior = repository.at_date(tenant_id, user_id, current.metric_date - timedelta(days=28))
    return current.ctl - prior.ctl if prior else ZERO
