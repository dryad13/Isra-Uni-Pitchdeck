"""Add roster_sync_mode to exam_programs.

Revision ID: 003_roster_sync_mode
Revises: 002_phase1_phase2
Create Date: 2026-06-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_roster_sync_mode"
down_revision: Union[str, None] = "002_phase1_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("exam_programs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "roster_sync_mode",
                sa.String(length=16),
                nullable=False,
                server_default="auto",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("exam_programs") as batch_op:
        batch_op.drop_column("roster_sync_mode")
