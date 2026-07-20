from app.models import AthleteProfile
from app.repositories.performance import PerformanceMetricsRepository
from app.schemas.dashboard import DashboardResponse
from sqlalchemy import select
from sqlalchemy.orm import Session


def calculate_dashboard(db: Session, user_id: int) -> DashboardResponse:
    current = PerformanceMetricsRepository(db).latest(user_id)
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user_id))
    return DashboardResponse(
        ftp=profile.ftp if profile else None,
        ctl=round(float(current.ctl), 1) if current else 0.0,
        atl=round(float(current.atl), 1) if current else 0.0,
        tsb=round(float(current.tsb), 1) if current else 0.0,
        weekly_hours=round(float(current.seven_day_training_hours), 1) if current else 0.0,
        weekly_tss=round(float(current.seven_day_tss), 1) if current else 0.0,
    )
