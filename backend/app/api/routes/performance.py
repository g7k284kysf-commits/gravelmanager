from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated

from app.api.deps import CurrentUser, DbSession
from app.repositories.performance import PerformanceMetricsRepository
from app.schemas.performance import (
    ChartRange,
    PerformanceChartPoint,
    PerformanceChartResponse,
    PerformanceSummary,
    RecalculationRequest,
    RecalculationResponse,
)
from app.services.performance import PerformanceCalculationService, twenty_eight_day_ctl_change
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/performance", tags=["Performance Manager"])
ZERO = Decimal("0")
RANGE_DAYS: dict[ChartRange, int] = {"28d": 28, "90d": 90, "180d": 180, "365d": 365}
ChartRangeQuery = Annotated[ChartRange, Query(alias="range", examples=["90d"])]
StartDateQuery = Annotated[date | None, Query(examples=["2026-01-01"])]
EndDateQuery = Annotated[date | None, Query(examples=["2026-03-31"])]


@router.get(
    "/summary",
    response_model=PerformanceSummary,
    summary="Current performance summary",
    description=(
        "Returns the authenticated athlete's latest unrounded stored training-load metrics."
    ),
)
def summary(db: DbSession, user: CurrentUser) -> PerformanceSummary:
    repository = PerformanceMetricsRepository(db)
    current = repository.latest(user.id)
    if current is None:
        return PerformanceSummary(
            ctl=ZERO,
            atl=ZERO,
            tsb=ZERO,
            seven_day_tss=ZERO,
            twenty_eight_day_tss=ZERO,
            seven_day_training_hours=ZERO,
            twenty_eight_day_training_hours=ZERO,
            ramp_rate=ZERO,
            twenty_eight_day_ctl_change=ZERO,
        )
    return PerformanceSummary(
        ctl=current.ctl,
        atl=current.atl,
        tsb=current.tsb,
        seven_day_tss=current.seven_day_tss,
        twenty_eight_day_tss=current.twenty_eight_day_tss,
        seven_day_training_hours=current.seven_day_training_hours,
        twenty_eight_day_training_hours=current.twenty_eight_day_training_hours,
        ramp_rate=current.ramp_rate,
        twenty_eight_day_ctl_change=twenty_eight_day_ctl_change(repository, user.id, current),
    )


@router.get(
    "/chart",
    response_model=PerformanceChartResponse,
    summary="Performance Management Chart data",
    description=("Returns a validated, continuous daily CTL, ATL, TSB, ramp-rate and TSS series."),
)
def chart(
    db: DbSession,
    user: CurrentUser,
    chart_range: ChartRangeQuery = "90d",
    start_date: StartDateQuery = None,
    end_date: EndDateQuery = None,
) -> PerformanceChartResponse:
    end = end_date or date.today()
    start = start_date or end - timedelta(days=RANGE_DAYS[chart_range] - 1)
    if end > date.today():
        raise HTTPException(status_code=422, detail="end_date cannot be in the future")
    if start > end:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")
    if (end - start).days > 364:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 365 days")
    metrics = PerformanceMetricsRepository(db).metrics_between(user.id, start, end)
    return PerformanceChartResponse(
        range=chart_range,
        start_date=start,
        end_date=end,
        points=[PerformanceChartPoint.model_validate(metric) for metric in metrics],
    )


@router.post(
    "/recalculate",
    response_model=RecalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalculate performance history",
    description="Idempotently recalculates metrics in the current database transaction.",
)
def recalculate(
    payload: RecalculationRequest, db: DbSession, user: CurrentUser
) -> RecalculationResponse:
    try:
        result = PerformanceCalculationService(db).recalculate(user.id, payload.start_date)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Performance recalculation failed") from exc
    return RecalculationResponse(
        recalculated_from=result.recalculated_from,
        recalculated_through=result.recalculated_through,
        rows_written=result.rows_written,
    )
