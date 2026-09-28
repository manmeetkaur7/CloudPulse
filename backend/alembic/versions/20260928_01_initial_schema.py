"""Create the CloudPulse persistence schema.

Revision ID: 20260928_01
Revises:
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260928_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "services",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("environment", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_services_project_id", "services", ["project_id"])
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("service_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.CheckConstraint("event_type IN ('request', 'error')", name="telemetry_events_event_type_check"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="telemetry_events_duration_ms_check"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telemetry_events_project_id", "telemetry_events", ["project_id"])
    op.create_index("ix_telemetry_events_service_id", "telemetry_events", ["service_id"])
    op.create_index("ix_telemetry_events_project_timestamp", "telemetry_events", ["project_id", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_telemetry_events_project_timestamp", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_service_id", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_project_id", table_name="telemetry_events")
    op.drop_table("telemetry_events")
    op.drop_index("ix_services_project_id", table_name="services")
    op.drop_table("services")
    op.drop_table("projects")
