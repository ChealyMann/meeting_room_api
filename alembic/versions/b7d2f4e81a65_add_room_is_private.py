"""add rooms.is_private

Revision ID: b7d2f4e81a65
Revises: 9c4e1a7b2d30
Create Date: 2026-10-23 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d2f4e81a65"
down_revision: str | Sequence[str] | None = "9c4e1a7b2d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Private or public label for a room. Existing rooms become public."""
    op.add_column(
        "rooms",
        sa.Column("is_private", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("rooms", "is_private")
