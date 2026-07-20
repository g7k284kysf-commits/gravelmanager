from datetime import date
from decimal import Decimal

from app.domain.performance import DailyLoad
from app.models import DailyPerformanceMetric, Training
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session


class PerformanceMetricsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def training_bounds(self, user_id: int) -> tuple[date | None, date | None]:
        first_training, last_training = self.session.execute(
            select(func.min(Training.date), func.max(Training.date)).where(
                Training.user_id == user_id
            )
        ).one()
        return first_training, last_training

    def daily_loads(self, user_id: int, start_date: date, end_date: date) -> dict[date, DailyLoad]:
        rows = self.session.execute(
            select(
                Training.date,
                func.coalesce(func.sum(Training.tss), 0),
                func.coalesce(func.sum(Training.duration_minutes), 0),
            )
            .where(
                Training.user_id == user_id,
                Training.date >= start_date,
                Training.date <= end_date,
            )
            .group_by(Training.date)
        )
        return {
            metric_date: DailyLoad(
                metric_date=metric_date,
                tss=Decimal(str(tss)),
                training_hours=Decimal(str(minutes)) / Decimal(60),
            )
            for metric_date, tss, minutes in rows
        }

    def metrics_between(
        self, user_id: int, start_date: date, end_date: date
    ) -> list[DailyPerformanceMetric]:
        return list(
            self.session.scalars(
                select(DailyPerformanceMetric)
                .where(
                    DailyPerformanceMetric.user_id == user_id,
                    DailyPerformanceMetric.metric_date >= start_date,
                    DailyPerformanceMetric.metric_date <= end_date,
                )
                .order_by(DailyPerformanceMetric.metric_date)
            )
        )

    def latest(self, user_id: int) -> DailyPerformanceMetric | None:
        return self.session.scalar(
            select(DailyPerformanceMetric)
            .where(DailyPerformanceMetric.user_id == user_id)
            .order_by(DailyPerformanceMetric.metric_date.desc())
            .limit(1)
        )

    def at_date(self, user_id: int, metric_date: date) -> DailyPerformanceMetric | None:
        return self.session.scalar(
            select(DailyPerformanceMetric).where(
                DailyPerformanceMetric.user_id == user_id,
                DailyPerformanceMetric.metric_date == metric_date,
            )
        )

    def existing_from(self, user_id: int, start_date: date) -> dict[date, DailyPerformanceMetric]:
        return {
            metric.metric_date: metric
            for metric in self.session.scalars(
                select(DailyPerformanceMetric).where(
                    DailyPerformanceMetric.user_id == user_id,
                    DailyPerformanceMetric.metric_date >= start_date,
                )
            )
        }

    def delete_all(self, user_id: int) -> None:
        self.session.execute(
            delete(DailyPerformanceMetric).where(DailyPerformanceMetric.user_id == user_id)
        )

    def delete_before(self, user_id: int, first_date: date) -> None:
        self.session.execute(
            delete(DailyPerformanceMetric).where(
                DailyPerformanceMetric.user_id == user_id,
                DailyPerformanceMetric.metric_date < first_date,
            )
        )
