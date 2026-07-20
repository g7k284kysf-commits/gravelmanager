from collections import deque
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class DailyLoad:
    metric_date: date
    tss: Decimal = ZERO
    training_hours: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class CalculatedMetric:
    metric_date: date
    daily_tss: Decimal
    ctl: Decimal
    atl: Decimal
    tsb: Decimal
    seven_day_tss: Decimal
    twenty_eight_day_tss: Decimal
    seven_day_training_hours: Decimal
    twenty_eight_day_training_hours: Decimal
    ramp_rate: Decimal


def calculate_timeline(
    loads: dict[date, DailyLoad],
    start_date: date,
    end_date: date,
    ctl_days: int = 42,
    atl_days: int = 7,
) -> list[CalculatedMetric]:
    """Calculate an unrounded, continuous daily training-load timeline."""
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    if ctl_days <= 0 or atl_days <= 0:
        raise ValueError("time constants must be positive")

    ctl_divisor = Decimal(ctl_days)
    atl_divisor = Decimal(atl_days)
    previous_ctl = ZERO
    previous_atl = ZERO
    tss_window: deque[Decimal] = deque(maxlen=28)
    hours_window: deque[Decimal] = deque(maxlen=28)
    ctl_history: deque[Decimal] = deque(maxlen=29)
    results: list[CalculatedMetric] = []
    current_date = start_date

    while current_date <= end_date:
        load = loads.get(current_date, DailyLoad(current_date))
        tsb = previous_ctl - previous_atl
        ctl = previous_ctl + (load.tss - previous_ctl) / ctl_divisor
        atl = previous_atl + (load.tss - previous_atl) / atl_divisor
        tss_window.append(load.tss)
        hours_window.append(load.training_hours)
        ctl_history.append(ctl)
        ramp_rate = ctl - ctl_history[-8] if len(ctl_history) >= 8 else ZERO
        results.append(
            CalculatedMetric(
                metric_date=current_date,
                daily_tss=load.tss,
                ctl=ctl,
                atl=atl,
                tsb=tsb,
                seven_day_tss=sum(list(tss_window)[-7:], ZERO),
                twenty_eight_day_tss=sum(tss_window, ZERO),
                seven_day_training_hours=sum(list(hours_window)[-7:], ZERO),
                twenty_eight_day_training_hours=sum(hours_window, ZERO),
                ramp_rate=ramp_rate,
            )
        )
        previous_ctl, previous_atl = ctl, atl
        current_date += timedelta(days=1)

    return results
