from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import AthleteProfile, Training, User
from app.services.performance import PerformanceCalculationService

WEEK_VARIATION = (0.82, 1.0, 1.12, 0.92)
SESSION_PLAN: dict[int, tuple[str, int, float, float, int, str]] = {
    0: ("Recovery", 45, 22.0, 120.0, 28, "Easy recovery ride"),
    1: ("Threshold", 75, 34.0, 320.0, 88, "Sustained threshold intervals"),
    2: ("Endurance", 105, 47.0, 410.0, 72, "Aerobic endurance ride"),
    3: ("VO2max", 70, 30.0, 260.0, 96, "VO2max hill repeats"),
    5: ("Gravel", 240, 98.0, 1450.0, 205, "Long progressive gravel session"),
    6: ("Endurance", 120, 52.0, 520.0, 84, "Steady endurance ride"),
}


def generated_training(user_id: int, training_date: date, day_index: int) -> Training | None:
    if training_date.weekday() == 4:
        return None
    if training_date.weekday() == 6 and (day_index // 7) % 4 == 3:
        return None
    sport, duration, distance, elevation, base_tss, notes = SESSION_PLAN[training_date.weekday()]
    factor = WEEK_VARIATION[(day_index // 7) % len(WEEK_VARIATION)]
    tss = round(base_tss * factor, 1)
    intensity = min(1.05, round((tss / max(duration, 1)) ** 0.5, 2))
    return Training(
        user_id=user_id,
        date=training_date,
        sport=sport,
        duration_minutes=duration,
        distance_km=round(distance * factor, 1),
        elevation_m=round(elevation * factor, 1),
        average_power=round(185 + base_tss * 0.35),
        normalized_power=round(205 + base_tss * 0.42),
        average_hr=round(128 + base_tss * 0.18),
        max_hr=round(155 + base_tss * 0.14),
        tss=tss,
        intensity_factor=intensity,
        calories=round(duration * 10.5),
        notes=notes,
    )


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
        first_day = date.today() - timedelta(days=139)
        trainings = [
            training
            for day_index in range(140)
            if (
                training := generated_training(
                    user.id, first_day + timedelta(days=day_index), day_index
                )
            )
        ]
        db.add_all(trainings)
        db.flush()
        PerformanceCalculationService(db).recalculate(user.id)
        db.commit()


if __name__ == "__main__":
    seed()
