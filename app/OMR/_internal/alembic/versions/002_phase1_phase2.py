"""Phase 1/2 schema additions.

Revision ID: 002_phase1_phase2
Revises: 001_baseline
Create Date: 2026-06-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_phase1_phase2"
down_revision: Union[str, None] = "001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("roll_no", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("class_section", sa.String(length=128), nullable=True),
        sa.Column("batch_label", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["program_id"], ["exam_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "roll_no", name="uq_student_program_roll"),
    )
    with op.batch_alter_table("verification_queue", schema=None) as batch_op:
        batch_op.add_column(sa.Column("resolved_by", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("resolved_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("scan_batches", schema=None) as batch_op:
        batch_op.add_column(sa.Column("expected_count", sa.Integer(), nullable=True))
    with op.batch_alter_table("exam_sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("negative_marking_ratio", sa.Float(), nullable=False, server_default="0.0")
        )


def downgrade() -> None:
    with op.batch_alter_table("exam_sessions", schema=None) as batch_op:
        batch_op.drop_column("negative_marking_ratio")
    with op.batch_alter_table("scan_batches", schema=None) as batch_op:
        batch_op.drop_column("expected_count")
    with op.batch_alter_table("verification_queue", schema=None) as batch_op:
        batch_op.drop_column("resolved_at")
        batch_op.drop_column("resolved_by")
    op.drop_table("students")
