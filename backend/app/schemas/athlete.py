from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AthleteProfileInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    date_of_birth: date | None = None
    height_cm: float | None = Field(default=None, gt=0, le=260)
    weight_kg: float | None = Field(default=None, gt=0, le=400)
    ftp: int | None = Field(default=None, gt=0, le=1000)
    max_hr: int | None = Field(default=None, gt=0, le=250)
    threshold_hr: int | None = Field(default=None, gt=0, le=250)

    @model_validator(mode="after")
    def validate_heart_rates(self) -> "AthleteProfileInput":
        if self.max_hr and self.threshold_hr and self.threshold_hr > self.max_hr:
            raise ValueError("Threshold HR cannot exceed max HR")
        return self


class AthleteProfileResponse(AthleteProfileInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    tenant_id: int
