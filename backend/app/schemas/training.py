from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TrainingInput(BaseModel):
    date: date
    sport: str = Field(min_length=2, max_length=40)
    duration_minutes: int = Field(gt=0, le=1440)
    distance_km: float | None = Field(default=None, ge=0)
    elevation_m: float | None = Field(default=None, ge=0)
    average_power: int | None = Field(default=None, ge=0)
    normalized_power: int | None = Field(default=None, ge=0)
    average_hr: int | None = Field(default=None, ge=0, le=250)
    max_hr: int | None = Field(default=None, ge=0, le=250)
    tss: float | None = Field(default=None, ge=0)
    intensity_factor: float | None = Field(default=None, ge=0, le=3)
    calories: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=5000)


class TrainingResponse(TrainingInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
