"""replace users.avatar_url with users.user_avatar

Revision ID: d5a8c3e17f42
Revises: b7d2f4e81a65
Create Date: 2026-10-27 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5a8c3e17f42"
down_revision: str | Sequence[str] | None = "b7d2f4e81a65"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Photos are uploaded now (rule R20): the path inside AVATAR_DIR, or NULL.
    Old photo links are dropped; they pointed at files this API never stored."""
    op.add_column("users", sa.Column("user_avatar", sa.String(length=3000), nullable=True))
    op.drop_column("users", "avatar_url")


def downgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=3000), nullable=True))
    op.drop_column("users", "user_avatar")
