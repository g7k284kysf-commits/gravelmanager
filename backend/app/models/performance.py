from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class DailyPerformanceMetric(Base):
    __tablename__ = "daily_performance_metrics"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "metric_date", name="uq_performance_tenant_user_date"
        ),
        Index("ix_performance_tenant_user_date", "tenant_id", "user_id", "metric_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    metric_date: Mapped[date] = mapped_column(Date)
    daily_tss: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    ctl: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    atl: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    tsb: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    seven_day_tss: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    twenty_eight_day_tss: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    seven_day_training_hours: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    twenty_eight_day_training_hours: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    ramp_rate: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="performance_metrics")
