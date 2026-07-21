from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Date, DateTime, Enum, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlanningStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class GoalType(StrEnum):
    SEASON = "season"
    COMPETITION = "competition"
    TRAINING = "training"
    PHYSIOLOGICAL = "physiological"
    TECHNICAL = "technical"
    RECOVERY = "recovery"
    HEAT_ADAPTATION = "heat_adaptation"
    NUTRITION = "nutrition"
    BODY_COMPOSITION = "body_composition"
    CUSTOM = "custom"


class GoalPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RacePriority(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        Index("ix_season_tenant_athlete_dates", "tenant_id", "athlete_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[PlanningStatus] = mapped_column(
        Enum(PlanningStatus, native_enum=False, length=30), default=PlanningStatus.DRAFT
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index("ix_goal_tenant_athlete_target", "tenant_id", "athlete_id", "target_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    season_id: Mapped[int | None] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    parent_goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    goal_type: Mapped[GoalType] = mapped_column(Enum(GoalType, native_enum=False, length=40))
    priority: Mapped[GoalPriority] = mapped_column(
        Enum(GoalPriority, native_enum=False, length=20), default=GoalPriority.MEDIUM
    )
    target_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[PlanningStatus] = mapped_column(
        Enum(PlanningStatus, native_enum=False, length=30), default=PlanningStatus.DRAFT
    )
    measurable_target: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Competition(Base):
    __tablename__ = "competitions"
    __table_args__ = (
        Index("ix_competition_tenant_athlete_start", "tenant_id", "athlete_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"))
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(240))
    discipline: Mapped[str | None] = mapped_column(String(80))
    distance_km: Mapped[float | None] = mapped_column(Float)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)
    race_priority: Mapped[RacePriority] = mapped_column(
        Enum(RacePriority, native_enum=False, length=1)
    )
    status: Mapped[PlanningStatus] = mapped_column(
        Enum(PlanningStatus, native_enum=False, length=30), default=PlanningStatus.DRAFT
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
