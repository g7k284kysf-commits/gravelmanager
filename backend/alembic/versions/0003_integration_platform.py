"""Add tenant, planning, and integration platform foundations.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("tenant_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
    )
    op.create_index("ix_membership_user_status", "tenant_memberships", ["user_id", "status"])

    for table_name in ("athlete_profiles", "trainings", "daily_performance_metrics"):
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))

    connection = op.get_bind()
    tenants = sa.table(
        "tenants",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("tenant_type", sa.String()),
        sa.column("status", sa.String()),
    )
    user_ids = [row[0] for row in connection.execute(sa.text("SELECT id FROM users"))]
    for user_id in user_ids:
        tenant_id = connection.execute(
            sa.insert(tenants)
            .values(
                name=f"Personal tenant {user_id}",
                slug=f"personal-{user_id}",
                tenant_type="PERSONAL",
                status="ACTIVE",
            )
            .returning(tenants.c.id)
        ).scalar_one()
        connection.execute(
            sa.text(
                "INSERT INTO tenant_memberships "
                "(tenant_id, user_id, role, status) "
                "VALUES (:tenant_id, :user_id, 'OWNER', 'ACTIVE')"
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        for table_name in ("athlete_profiles", "trainings", "daily_performance_metrics"):
            connection.execute(
                sa.text(f"UPDATE {table_name} SET tenant_id = :tenant_id WHERE user_id = :user_id"),
                {"tenant_id": tenant_id, "user_id": user_id},
            )

    with op.batch_alter_table("athlete_profiles") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_athlete_tenant", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE"
        )
        batch.create_index("ix_athlete_profiles_tenant_id", ["tenant_id"])
    with op.batch_alter_table("trainings") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_training_tenant", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE"
        )
        batch.create_index("ix_trainings_tenant_id", ["tenant_id"])
    with op.batch_alter_table("daily_performance_metrics") as batch:
        batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_performance_tenant", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE"
        )
        batch.drop_index("ix_performance_user_date")
        batch.drop_constraint("uq_performance_user_date", type_="unique")
        batch.create_unique_constraint(
            "uq_performance_tenant_user_date", ["tenant_id", "user_id", "metric_date"]
        )
        batch.create_index(
            "ix_performance_tenant_user_date", ["tenant_id", "user_id", "metric_date"]
        )

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("description", sa.Text()),
        *timestamps(),
    )
    op.create_index(
        "ix_season_tenant_athlete_dates",
        "seasons",
        ["tenant_id", "athlete_id", "start_date"],
    )
    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="SET NULL")),
        sa.Column("parent_goal_id", sa.Integer(), sa.ForeignKey("goals.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("goal_type", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("target_date", sa.Date()),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("measurable_target", sa.JSON()),
        *timestamps(),
    )
    op.create_index(
        "ix_goal_tenant_athlete_target", "goals", ["tenant_id", "athlete_id", "target_date"]
    )
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("goals.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("location", sa.String(240)),
        sa.Column("discipline", sa.String(80)),
        sa.Column("distance_km", sa.Float()),
        sa.Column("elevation_gain_m", sa.Float()),
        sa.Column("race_priority", sa.String(1), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("description", sa.Text()),
        *timestamps(),
    )
    op.create_index(
        "ix_competition_tenant_athlete_start",
        "competitions",
        ["tenant_id", "athlete_id", "start_date"],
    )

    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_key", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("external_account_id", sa.String(255)),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("encrypted_credentials", sa.Text()),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(80)),
        sa.Column("last_error_message", sa.String(500)),
        *timestamps(),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "tenant_id", "athlete_id", "provider_key", name="uq_connection_provider"
        ),
    )
    op.create_index(
        "ix_connection_tenant_status", "integration_connections", ["tenant_id", "status"]
    )
    op.create_table(
        "integration_syncs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("integration_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_key", sa.String(80), nullable=False),
        sa.Column("sync_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cursor_before", sa.String(500)),
        sa.Column("cursor_after", sa.String(500)),
        sa.Column("records_discovered", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("records_skipped", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.String(500)),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "athlete_id",
            "connection_id",
            "idempotency_key",
            name="uq_sync_idempotency",
        ),
    )
    op.create_index(
        "uq_sync_connection_active",
        "integration_syncs",
        ["connection_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
        sqlite_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )
    op.create_index(
        "ix_sync_provider_status",
        "integration_syncs",
        ["tenant_id", "provider_key", "status"],
    )
    op.create_index(
        "ix_sync_connection_requested", "integration_syncs", ["connection_id", "requested_at"]
    )
    op.create_index("ix_integration_syncs_correlation_id", "integration_syncs", ["correlation_id"])

    op.create_table(
        "import_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("integration_connections.id", ondelete="SET NULL"),
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("file_extension", sa.String(12), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("detected_format", sa.String(30)),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("processing_started_at", sa.DateTime(timezone=True)),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.String(500)),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "athlete_id", "checksum_sha256", name="uq_import_checksum"
        ),
    )
    op.create_index("ix_import_tenant_uploaded", "import_files", ["tenant_id", "uploaded_at"])
    op.create_index("ix_import_status", "import_files", ["tenant_id", "status"])
    op.create_index("ix_import_files_correlation_id", "import_files", ["correlation_id"])
    op.create_table(
        "import_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "import_file_id",
            sa.Integer(),
            sa.ForeignKey("import_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(255)),
        sa.Column("record_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source_payload", sa.JSON()),
        sa.Column("normalized_payload", sa.JSON()),
        sa.Column("linked_entity_type", sa.String(80)),
        sa.Column("linked_entity_id", sa.Integer()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.String(500)),
        *timestamps(),
    )
    op.create_index("ix_import_record_file_status", "import_records", ["import_file_id", "status"])
    op.create_table(
        "integration_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("provider_key", sa.String(80), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("integration_connections.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "sync_id", sa.Integer(), sa.ForeignKey("integration_syncs.id", ondelete="SET NULL")
        ),
        sa.Column(
            "import_file_id", sa.Integer(), sa.ForeignKey("import_files.id", ondelete="SET NULL")
        ),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_event_tenant_created", "integration_events", ["tenant_id", "created_at"])
    op.create_index(
        "ix_event_provider_severity", "integration_events", ["provider_key", "severity"]
    )
    op.create_index(
        "ix_integration_events_correlation_id", "integration_events", ["correlation_id"]
    )


def downgrade() -> None:
    for table_name in (
        "integration_events",
        "import_records",
        "import_files",
        "integration_syncs",
        "integration_connections",
        "competitions",
        "goals",
        "seasons",
    ):
        op.drop_table(table_name)

    with op.batch_alter_table("daily_performance_metrics") as batch:
        batch.drop_index("ix_performance_tenant_user_date")
        batch.drop_constraint("uq_performance_tenant_user_date", type_="unique")
        batch.create_unique_constraint("uq_performance_user_date", ["user_id", "metric_date"])
        batch.create_index("ix_performance_user_date", ["user_id", "metric_date"])
        batch.drop_constraint("fk_performance_tenant", type_="foreignkey")
        batch.drop_column("tenant_id")
    with op.batch_alter_table("trainings") as batch:
        batch.drop_index("ix_trainings_tenant_id")
        batch.drop_constraint("fk_training_tenant", type_="foreignkey")
        batch.drop_column("tenant_id")
    with op.batch_alter_table("athlete_profiles") as batch:
        batch.drop_index("ix_athlete_profiles_tenant_id")
        batch.drop_constraint("fk_athlete_tenant", type_="foreignkey")
        batch.drop_column("tenant_id")
    op.drop_table("tenant_memberships")
    op.drop_table("tenants")
