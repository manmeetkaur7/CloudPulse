"""Add OpenTelemetry-compatible telemetry context fields.

Revision ID: 20261005_01
Revises: 20260928_01
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20261005_01"
down_revision = "20260928_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("telemetry_events", sa.Column("trace_id", sa.String(length=32), nullable=True))
    op.add_column("telemetry_events", sa.Column("span_id", sa.String(length=16), nullable=True))
    op.add_column("telemetry_events", sa.Column("http_method", sa.String(length=10), nullable=True))
    op.add_column("telemetry_events", sa.Column("http_route", sa.String(length=500), nullable=True))
    op.create_index("ix_telemetry_events_trace_id", "telemetry_events", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_telemetry_events_trace_id", table_name="telemetry_events")
    op.drop_column("telemetry_events", "http_route")
    op.drop_column("telemetry_events", "http_method")
    op.drop_column("telemetry_events", "span_id")
    op.drop_column("telemetry_events", "trace_id")
