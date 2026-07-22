"""Baseline schema (pre Phase 1/2).

Revision ID: 001_baseline
Revises:
Create Date: 2026-06-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exam_programs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("planned_max_questions", sa.Integer(), nullable=True),
        sa.Column("key_coverage_end", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "path_layouts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_family", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("max_questions", sa.Integer(), nullable=False),
        sa.Column("columns_json", sa.Text(), nullable=True),
        sa.Column("roll_number_json", sa.Text(), nullable=True),
        sa.Column("anchor_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exam_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("template_family", sa.String(length=16), nullable=False),
        sa.Column("session_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("path_layout_id", sa.Integer(), nullable=True),
        sa.Column("sheet_question_count", sa.Integer(), nullable=False),
        sa.Column("global_q_start", sa.Integer(), nullable=False),
        sa.Column("global_q_end", sa.Integer(), nullable=False),
        sa.Column("key_complete", sa.Boolean(), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("batch_name", sa.String(length=255), nullable=True),
        sa.Column("export_mode", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["path_layout_id"], ["path_layouts.id"]),
        sa.ForeignKeyConstraint(["program_id"], ["exam_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "answer_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("question_no", sa.Integer(), nullable=False),
        sa.Column("correct_option", sa.String(length=8), nullable=False),
        sa.Column("added_via_session_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["added_via_session_id"], ["exam_sessions.id"]),
        sa.ForeignKeyConstraint(["program_id"], ["exam_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "question_no", name="uq_answer_key_program_question"),
    )
    op.create_table(
        "answer_key_audit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("question_no", sa.Integer(), nullable=False),
        sa.Column("old_value", sa.String(length=8), nullable=True),
        sa.Column("new_value", sa.String(length=8), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["exam_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "subject_splits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("subject_name", sa.String(length=255), nullable=False),
        sa.Column("q_start", sa.Integer(), nullable=False),
        sa.Column("q_end", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["exam_programs.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scan_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress_pct", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sheet_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("roll_no", sa.String(length=32), nullable=True),
        sa.Column("answers_json", sa.Text(), nullable=True),
        sa.Column("counts_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["scan_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "verification_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("global_question_no", sa.Integer(), nullable=False),
        sa.Column("anomaly_type", sa.String(length=32), nullable=False),
        sa.Column("crop_path", sa.String(length=512), nullable=True),
        sa.Column("detected_values", sa.Text(), nullable=True),
        sa.Column("resolved_value", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["sheet_id"], ["sheet_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ingested_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_hash"),
    )


def downgrade() -> None:
    op.drop_table("ingested_files")
    op.drop_table("verification_queue")
    op.drop_table("sheet_results")
    op.drop_table("scan_batches")
    op.drop_table("subject_splits")
    op.drop_table("answer_key_audit")
    op.drop_table("answer_keys")
    op.drop_table("exam_sessions")
    op.drop_table("path_layouts")
    op.drop_table("exam_programs")
