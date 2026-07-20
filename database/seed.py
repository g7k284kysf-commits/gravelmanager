from datetime import date, timedelta

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import AthleteProfile, Training, User
from sqlalchemy import select


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == "demo@gravelmanager.app")):
            return
        user = User(email="demo@gravelmanager.app", password_hash=hash_password("GravelDemo!2026"))
        db.add(user)
        db.flush()
        db.add(
            AthleteProfile(
                user_id=user.id,
                name="Alex Rider",
                date_of_birth=date(1990, 6, 15),
                height_cm=178,
                weight_kg=72,
                ftp=285,
                max_hr=192,
                threshold_hr=174,
            )
        )
        db.add_all(
            [
                Training(
                    user_id=user.id,
                    date=date.today() - timedelta(days=2),
                    sport="Gravel",
                    duration_minutes=120,
                    distance_km=52.4,
                    elevation_m=730,
                    average_power=212,
                    normalized_power=238,
                    average_hr=149,
                    max_hr=181,
                    tss=141,
                    intensity_factor=0.84,
                    calories=1340,
                    notes="Steady endurance ride with threshold climbs.",
                ),
                Training(
                    user_id=user.id,
                    date=date.today(),
                    sport="Cycling",
                    duration_minutes=60,
                    distance_km=28.1,
                    elevation_m=180,
                    average_power=198,
                    normalized_power=221,
                    average_hr=142,
                    max_hr=173,
                    tss=72,
                    intensity_factor=0.78,
                    calories=690,
                    notes="Aerobic recovery spin.",
                ),
            ]
        )
        db.commit()


if __name__ == "__main__":
    seed()
