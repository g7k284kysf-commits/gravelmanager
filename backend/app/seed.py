from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import AthleteProfile, Competition, Goal, Season, Training, User
from app.models.planning import GoalPriority, GoalType, PlanningStatus, RacePriority
from app.services.performance import PerformanceCalculationService
from app.services.tenancy import create_personal_tenant

WEEK_VARIATION = (0.82, 1.0, 1.12, 0.92)
SESSION_PLAN: dict[int, tuple[str, int, float, float, int, str]] = {
    0: ("Recovery", 45, 22.0, 120.0, 28, "Easy recovery ride"),
    1: ("Threshold", 75, 34.0, 320.0, 88, "Sustained threshold intervals"),
    2: ("Endurance", 105, 47.0, 410.0, 72, "Aerobic endurance ride"),
    3: ("VO2max", 70, 30.0, 260.0, 96, "VO2max hill repeats"),
    5: ("Gravel", 240, 98.0, 1450.0, 205, "Long progressive gravel session"),
    6: ("Endurance", 120, 52.0, 520.0, 84, "Steady endurance ride"),
}


def generated_training(
    tenant_id: int, user_id: int, training_date: date, day_index: int
) -> Training | None:
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
        tenant_id=tenant_id,
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
        membership = create_personal_tenant(db, user)
        db.add(
            AthleteProfile(
                user_id=user.id,
                tenant_id=membership.tenant_id,
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
                    membership.tenant_id,
                    user.id,
                    first_day + timedelta(days=day_index),
                    day_index,
                )
            )
        ]
        db.add_all(trainings)
        season_start = date.today() - timedelta(days=30)
        season = Season(
            tenant_id=membership.tenant_id,
            athlete_id=user.id,
            name="2026 Gravel campaign",
            start_date=season_start,
            end_date=season_start + timedelta(days=240),
            status=PlanningStatus.ACTIVE,
            description="Build durable endurance and race-specific gravel skills.",
        )
        db.add(season)
        db.flush()
        season_goal = Goal(
            tenant_id=membership.tenant_id,
            athlete_id=user.id,
            season_id=season.id,
            title="Complete the A race strongly",
            description="Arrive healthy and execute pacing and nutrition.",
            goal_type=GoalType.SEASON,
            priority=GoalPriority.HIGH,
            target_date=season_start + timedelta(days=180),
            status=PlanningStatus.ACTIVE,
            measurable_target={"finish": True},
        )
        db.add(season_goal)
        db.flush()
        db.add(
            Goal(
                tenant_id=membership.tenant_id,
                athlete_id=user.id,
                season_id=season.id,
                parent_goal_id=season_goal.id,
                title="Practice race nutrition",
                description="Complete three long rides with the race nutrition plan.",
                goal_type=GoalType.NUTRITION,
                priority=GoalPriority.MEDIUM,
                target_date=season_start + timedelta(days=120),
                status=PlanningStatus.ACTIVE,
                measurable_target={"successful_sessions": 3},
            )
        )
        for offset, name, priority, distance in (
            (75, "Spring gravel opener", RacePriority.C, 95.0),
            (125, "Highland gravel rehearsal", RacePriority.B, 145.0),
            (180, "Gravel championship", RacePriority.A, 200.0),
        ):
            race_day = season_start + timedelta(days=offset)
            db.add(
                Competition(
                    tenant_id=membership.tenant_id,
                    athlete_id=user.id,
                    season_id=season.id,
                    goal_id=season_goal.id,
                    name=name,
                    start_date=race_day,
                    end_date=race_day,
                    location="Veluwe, NL",
                    discipline="Gravel",
                    distance_km=distance,
                    elevation_gain_m=distance * 9,
                    race_priority=priority,
                    status=PlanningStatus.ACTIVE,
                    description="Seeded planning example; no external provider connection.",
                )
            )
        PerformanceCalculationService(db).recalculate(membership.tenant_id, user.id)
        db.commit()


if __name__ == "__main__":
    seed()
