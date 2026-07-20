"""Add daily performance metrics.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_performance_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("daily_tss", sa.Numeric(14, 6), nullable=False),
        sa.Column("ctl", sa.Numeric(14, 6), nullable=False),
        sa.Column("atl", sa.Numeric(14, 6), nullable=False),
        sa.Column("tsb", sa.Numeric(14, 6), nullable=False),
        sa.Column("seven_day_tss", sa.Numeric(14, 6), nullable=False),
        sa.Column("twenty_eight_day_tss", sa.Numeric(14, 6), nullable=False),
        sa.Column("seven_day_training_hours", sa.Numeric(14, 6), nullable=False),
        sa.Column("twenty_eight_day_training_hours", sa.Numeric(14, 6), nullable=False),
        sa.Column("ramp_rate", sa.Numeric(14, 6), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "metric_date", name="uq_performance_user_date"),
    )
    op.create_index(
        "ix_performance_user_date", "daily_performance_metrics", ["user_id", "metric_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_performance_user_date", table_name="daily_performance_metrics")
    op.drop_table("daily_performance_metrics")
