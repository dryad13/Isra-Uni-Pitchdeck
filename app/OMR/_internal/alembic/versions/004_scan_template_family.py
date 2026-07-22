"""Add scan_template_family to exam_sessions.

Revision ID: 004_scan_template_family
Revises: 003_roster_sync_mode
Create Date: 2026-06-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_scan_template_family"
down_revision: Union[str, None] = "003_roster_sync_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("exam_sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("scan_template_family", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("exam_sessions", schema=None) as batch_op:
        batch_op.drop_column("scan_template_family")
