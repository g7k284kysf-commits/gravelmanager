from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import settings
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).parents[1]


def alembic_config(database_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    return config


def test_0003_preserves_multiple_sprint_2_users_and_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "migration.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    config = alembic_config(database_path)
    command.upgrade(config, "0002")
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        for user_id in (1, 2):
            connection.execute(
                text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, 'hashed')"),
                {"id": user_id, "email": f"rider{user_id}@example.com"},
            )
            connection.execute(
                text(
                    "INSERT INTO athlete_profiles (id, user_id, name) VALUES (:id, :user_id, :name)"
                ),
                {"id": user_id, "user_id": user_id, "name": f"Rider {user_id}"},
            )
            connection.execute(
                text(
                    "INSERT INTO trainings "
                    "(id, user_id, date, sport, duration_minutes) "
                    "VALUES (:id, :user_id, '2026-01-01', 'Gravel', 60)"
                ),
                {"id": user_id, "user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO daily_performance_metrics "
                    "(id, user_id, metric_date, daily_tss, ctl, atl, tsb, "
                    "seven_day_tss, twenty_eight_day_tss, seven_day_training_hours, "
                    "twenty_eight_day_training_hours, ramp_rate) VALUES "
                    "(:id, :user_id, '2026-01-01', 50, 10, 12, -2, 50, 50, 1, 1, 0)"
                ),
                {"id": user_id, "user_id": user_id},
            )

    command.upgrade(config, "0003")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM tenants")) == 2
        assert connection.scalar(text("SELECT count(*) FROM tenant_memberships")) == 2
        for table_name in ("athlete_profiles", "trainings", "daily_performance_metrics"):
            mismatches = connection.scalar(
                text(
                    f"SELECT count(*) FROM {table_name} AS record "
                    "JOIN tenant_memberships AS membership "
                    "ON membership.user_id = record.user_id "
                    "WHERE record.tenant_id != membership.tenant_id"
                )
            )
            assert mismatches == 0

    command.downgrade(config, "0002")
    assert "tenants" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM users")) == 2
        assert connection.scalar(text("SELECT count(*) FROM trainings")) == 2

    command.upgrade(config, "0003")
    assert "integration_syncs" in inspect(engine).get_table_names()
    engine.dispose()
