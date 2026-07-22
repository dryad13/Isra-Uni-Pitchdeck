"""Batch recovery — durable file queue and ingestion state.

Revision ID: 005_batch_recovery
Revises: 004_scan_template_family
Create Date: 2026-06-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_batch_recovery"
down_revision: Union[str, None] = "004_scan_template_family"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "batch_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("source_path", sa.String(length=1024), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("sheet_result_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["scan_batches.id"]),
        sa.ForeignKeyConstraint(["sheet_result_id"], ["sheet_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_files_batch_id", "batch_files", ["batch_id"])

    op.create_table(
        "ingestion_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("active_session_id", sa.Integer(), nullable=True),
        sa.Column("expected_count", sa.Integer(), nullable=True),
        sa.Column("watching", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["active_session_id"], ["exam_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("scan_batches", schema=None) as batch_op:
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("file_manifest_version", sa.Integer(), nullable=False, server_default="1")
        )


def downgrade() -> None:
    with op.batch_alter_table("scan_batches", schema=None) as batch_op:
        batch_op.drop_column("file_manifest_version")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("completed_at")

    op.drop_table("ingestion_state")
    op.drop_index("ix_batch_files_batch_id", table_name="batch_files")
    op.drop_table("batch_files")
