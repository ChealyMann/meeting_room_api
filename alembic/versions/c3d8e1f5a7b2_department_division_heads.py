"""departments and divisions get a head (the request slip's opinion boxes)

Revision ID: c3d8e1f5a7b2
Revises: a9c4e2b7d1f3
Create Date: 2026-11-13 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "c3d8e1f5a7b2"
down_revision: str | Sequence[str] | None = "a9c4e2b7d1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("departments", "divisions")


def upgrade() -> None:
    """Nullable: no head yet means that box on the slip stays empty."""
    for table in TABLES:
        op.add_column(table, sa.Column("head_user_id", mysql.INTEGER(unsigned=True), nullable=True))
        op.create_index(op.f(f"ix_{table}_head_user_id"), table, ["head_user_id"])
        op.create_foreign_key(
            op.f(f"fk_{table}_head_user_id_users"),
            table,
            "users",
            ["head_user_id"],
            ["id"],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_constraint(op.f(f"fk_{table}_head_user_id_users"), table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_head_user_id"), table_name=table)
        op.drop_column(table, "head_user_id")
