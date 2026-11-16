"""catering packages and IT services get a group and an icon (Staff booking pages)

Revision ID: a9c4e2b7d1f3
Revises: f1c3a7b9d2e4
Create Date: 2026-11-12 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9c4e2b7d1f3"
down_revision: str | Sequence[str] | None = "f1c3a7b9d2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("catering_packages", "it_services")


def upgrade() -> None:
    """Both nullable: existing rows have no group (shown under "Other") and no icon."""
    for table in TABLES:
        op.add_column(table, sa.Column("group", sa.String(length=20), nullable=True))
        op.add_column(table, sa.Column("icon", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "icon")
        op.drop_column(table, "group")
