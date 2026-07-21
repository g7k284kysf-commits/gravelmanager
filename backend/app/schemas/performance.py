from datetime import date as Date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

ChartRange = Literal["28d", "90d", "180d", "365d"]


class RoundedMetricModel(BaseModel):
    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value: object) -> object:
        if isinstance(value, Decimal):
            return float(round(value, 2))
        return value


class PerformanceSummary(RoundedMetricModel):
    ctl: Decimal
    atl: Decimal
    tsb: Decimal
    seven_day_tss: Decimal
    twenty_eight_day_tss: Decimal
    seven_day_training_hours: Decimal
    twenty_eight_day_training_hours: Decimal
    ramp_rate: Decimal
    twenty_eight_day_ctl_change: Decimal


class PerformanceChartPoint(RoundedMetricModel):
    model_config = ConfigDict(from_attributes=True)
    date: Date = Field(validation_alias="metric_date")
    daily_tss: Decimal
    ctl: Decimal
    atl: Decimal
    tsb: Decimal
    ramp_rate: Decimal


class PerformanceChartResponse(BaseModel):
    range: ChartRange
    start_date: Date
    end_date: Date
    points: list[PerformanceChartPoint]


class RecalculationRequest(BaseModel):
    start_date: Date | None = Field(
        default=None,
        description=(
            "Recalculate stored metrics from this date onward while preserving earlier rows."
        ),
        examples=["2026-01-01"],
    )


class RecalculationResponse(BaseModel):
    recalculated_from: Date | None
    recalculated_through: Date | None
    rows_written: Annotated[int, Field(ge=0)]
