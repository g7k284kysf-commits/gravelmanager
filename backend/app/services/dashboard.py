from datetime import date, timedelta

from app.models import AthleteProfile, Training
from app.schemas.dashboard import DashboardResponse
from sqlalchemy import select
from sqlalchemy.orm import Session


def calculate_dashboard(db: Session, user_id: int) -> DashboardResponse:
    today = date.today()
    history_start = today - timedelta(days=90)
    trainings = list(
        db.scalars(
            select(Training)
            .where(Training.user_id == user_id, Training.date >= history_start)
            .order_by(Training.date)
        )
    )
    daily_tss = {history_start + timedelta(days=i): 0.0 for i in range(91)}
    for training in trainings:
        daily_tss[training.date] = daily_tss.get(training.date, 0.0) + (training.tss or 0.0)
    ctl = atl = 0.0
    for day in sorted(daily_tss):
        load = daily_tss[day]
        ctl += (load - ctl) / 42
        atl += (load - atl) / 7
    week_start = today - timedelta(days=today.weekday())
    weekly = [training for training in trainings if training.date >= week_start]
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user_id))
    return DashboardResponse(
        ftp=profile.ftp if profile else None,
        ctl=round(ctl, 1),
        atl=round(atl, 1),
        tsb=round(ctl - atl, 1),
        weekly_hours=round(sum(item.duration_minutes for item in weekly) / 60, 1),
        weekly_tss=round(sum(item.tss or 0 for item in weekly), 1),
    )
