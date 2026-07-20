"""Initial application schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "athlete_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("height_cm", sa.Float()),
        sa.Column("weight_kg", sa.Float()),
        sa.Column("ftp", sa.Integer()),
        sa.Column("max_hr", sa.Integer()),
        sa.Column("threshold_hr", sa.Integer()),
    )
    op.create_table(
        "trainings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sport", sa.String(40), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float()),
        sa.Column("elevation_m", sa.Float()),
        sa.Column("average_power", sa.Integer()),
        sa.Column("normalized_power", sa.Integer()),
        sa.Column("average_hr", sa.Integer()),
        sa.Column("max_hr", sa.Integer()),
        sa.Column("tss", sa.Float()),
        sa.Column("intensity_factor", sa.Float()),
        sa.Column("calories", sa.Integer()),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_trainings_user_id", "trainings", ["user_id"])
    op.create_index("ix_trainings_date", "trainings", ["date"])


def downgrade() -> None:
    op.drop_table("trainings")
    op.drop_table("athlete_profiles")
    op.drop_table("users")
