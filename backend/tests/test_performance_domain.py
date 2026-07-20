from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.domain.performance import DailyLoad, calculate_timeline


def test_exponential_load_formulas_and_previous_day_tsb() -> None:
    first_day = date(2026, 1, 1)
    metrics = calculate_timeline(
        {first_day: DailyLoad(first_day, Decimal("100"), Decimal("2"))},
        first_day,
        first_day + timedelta(days=1),
    )

    first, rest_day = metrics
    assert first.ctl == Decimal("100") / Decimal("42")
    assert first.atl == Decimal("100") / Decimal("7")
    assert first.tsb == Decimal("0")
    assert rest_day.daily_tss == Decimal("0")
    assert rest_day.ctl == first.ctl + (Decimal("0") - first.ctl) / Decimal("42")
    assert rest_day.atl == first.atl + (Decimal("0") - first.atl) / Decimal("7")
    assert rest_day.tsb == first.ctl - first.atl


def test_rolling_totals_and_ramp_rate_use_continuous_calendar_days() -> None:
    first_day = date(2026, 2, 1)
    loads = {
        first_day: DailyLoad(first_day, Decimal("70"), Decimal("1.5")),
        first_day + timedelta(days=7): DailyLoad(
            first_day + timedelta(days=7), Decimal("140"), Decimal("3")
        ),
    }
    metrics = calculate_timeline(loads, first_day, first_day + timedelta(days=7))

    assert len(metrics) == 8
    assert metrics[-1].seven_day_tss == Decimal("140")
    assert metrics[-1].twenty_eight_day_tss == Decimal("210")
    assert metrics[-1].seven_day_training_hours == Decimal("3")
    assert metrics[-1].ramp_rate == metrics[-1].ctl - metrics[0].ctl


def test_calculation_is_decimal_deterministic_and_unrounded() -> None:
    first_day = date(2026, 3, 1)
    loads = {first_day: DailyLoad(first_day, Decimal("1"), Decimal("0.1"))}

    first_run = calculate_timeline(loads, first_day, first_day + timedelta(days=30))
    second_run = calculate_timeline(loads, first_day, first_day + timedelta(days=30))

    assert first_run == second_run
    assert first_run[0].ctl == Decimal("1") / Decimal("42")
    assert len(first_run[0].ctl.as_tuple().digits) > 6


def test_calculation_rejects_invalid_boundaries_and_constants() -> None:
    day = date(2026, 1, 1)
    with pytest.raises(ValueError, match="end_date"):
        calculate_timeline({}, day, day - timedelta(days=1))
    with pytest.raises(ValueError, match="time constants"):
        calculate_timeline({}, day, day, ctl_days=0)
