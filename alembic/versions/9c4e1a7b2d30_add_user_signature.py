"""add users.user_signature

Revision ID: 9c4e1a7b2d30
Revises: 3eb53d2e63be
Create Date: 2026-10-23 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c4e1a7b2d30"
down_revision: str | Sequence[str] | None = "3eb53d2e63be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """A user's signature image (rule R19): its path inside SIGNATURE_DIR, or NULL."""
    op.add_column(
        "users",
        sa.Column("user_signature", sa.String(length=3000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "user_signature")
