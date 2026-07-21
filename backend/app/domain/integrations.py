from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class IntegrationCapability(StrEnum):
    OAUTH = "oauth"
    FILE_IMPORT = "file_import"
    ACTIVITY_IMPORT = "activity_import"
    PLANNED_WORKOUT_IMPORT = "planned_workout_import"
    PLANNED_WORKOUT_EXPORT = "planned_workout_export"
    WELLNESS_IMPORT = "wellness_import"
    HEALTH_METRICS_IMPORT = "health_metrics_import"
    ROUTE_IMPORT = "route_import"
    WEBHOOK = "webhook"
    POLLING = "polling"


class NormalizedActivity(BaseModel):
    external_id: str | None = None
    source_provider: str
    activity_type: str
    name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int = Field(ge=0)
    moving_time_seconds: int | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    elevation_gain_meters: float | None = Field(default=None, ge=0)
    average_power_watts: float | None = Field(default=None, ge=0)
    normalized_power_watts: float | None = Field(default=None, ge=0)
    max_power_watts: float | None = Field(default=None, ge=0)
    average_heart_rate: float | None = Field(default=None, ge=0)
    max_heart_rate: float | None = Field(default=None, ge=0)
    average_cadence: float | None = Field(default=None, ge=0)
    energy_kj: float | None = Field(default=None, ge=0)
    calories: float | None = Field(default=None, ge=0)
    training_stress_score: float | None = Field(default=None, ge=0)
    intensity_factor: float | None = Field(default=None, ge=0)
    raw_source_reference: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_times(self) -> "NormalizedActivity":
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("Activity timestamps must be timezone-aware")
        if self.end_time < self.start_time:
            raise ValueError("Activity end_time cannot be before start_time")
        return self


class NormalizedWellnessMetric(BaseModel):
    metric_type: str
    measured_at: datetime
    value: float
    unit: str
    source_provider: str
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timestamp(self) -> "NormalizedWellnessMetric":
        if self.measured_at.tzinfo is None:
            raise ValueError("Wellness timestamps must be timezone-aware")
        return self


class NormalizedPlannedWorkout(BaseModel):
    external_id: str | None = None
    title: str
    scheduled_date: date
    sport: str
    duration_seconds: int | None = Field(default=None, ge=0)
    description: str | None = None
    workout_steps: list[dict[str, object]] = Field(default_factory=list)
    source_provider: str
    metadata: dict[str, object] = Field(default_factory=dict)


class NormalizedImportRecord(BaseModel):
    record_type: str
    external_id: str | None = None
    source_payload: dict[str, object] | None = None
    normalized_payload: dict[str, object]
