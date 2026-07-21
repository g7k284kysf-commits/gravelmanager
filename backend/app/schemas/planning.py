from datetime import date, datetime

from app.models.planning import (
    GoalPriority,
    GoalType,
    PlanningStatus,
    RacePriority,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SeasonInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    start_date: date
    end_date: date
    status: PlanningStatus = PlanningStatus.DRAFT
    description: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_dates(self) -> "SeasonInput":
        if self.end_date < self.start_date:
            raise ValueError("Season end_date cannot be before start_date")
        return self


class SeasonResponse(SeasonInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    athlete_id: int
    created_at: datetime
    updated_at: datetime


class GoalInput(BaseModel):
    season_id: int | None = None
    parent_goal_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    goal_type: GoalType
    priority: GoalPriority = GoalPriority.MEDIUM
    target_date: date | None = None
    status: PlanningStatus = PlanningStatus.DRAFT
    measurable_target: dict[str, object] | None = None


class GoalResponse(GoalInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    athlete_id: int
    created_at: datetime
    updated_at: datetime


class CompetitionInput(BaseModel):
    season_id: int
    goal_id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    location: str | None = Field(default=None, max_length=240)
    discipline: str | None = Field(default=None, max_length=80)
    distance_km: float | None = Field(default=None, ge=0)
    elevation_gain_m: float | None = Field(default=None, ge=0)
    race_priority: RacePriority
    status: PlanningStatus = PlanningStatus.DRAFT
    description: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_dates(self) -> "CompetitionInput":
        if self.end_date < self.start_date:
            raise ValueError("Competition end_date cannot be before start_date")
        return self


class CompetitionResponse(CompetitionInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    athlete_id: int
    created_at: datetime
    updated_at: datetime
