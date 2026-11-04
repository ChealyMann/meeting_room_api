"""record who cancelled a booking, and Admin reviews and rejections (B-35)

Revision ID: f1c3a7b9d2e4
Revises: e4b7c2a9f310
Create Date: 2026-11-04 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "f1c3a7b9d2e4"
down_revision: str | Sequence[str] | None = "e4b7c2a9f310"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """`cancelled_by`: who cancelled (null: the system, or a cancel before this column).
    `by_admin`: the Admin acted as a backup reviewer (B-34). Existing rows are not Admin."""
    op.add_column(
        "bookings",
        sa.Column("cancelled_by", mysql.INTEGER(unsigned=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_bookings_cancelled_by_users"),
        "bookings",
        "users",
        ["cancelled_by"],
        ["id"],
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    for table in ("booking_reviews", "booking_rejections"):
        op.add_column(
            table,
            sa.Column("by_admin", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        )


def downgrade() -> None:
    for table in ("booking_rejections", "booking_reviews"):
        op.drop_column(table, "by_admin")
    op.drop_constraint(op.f("fk_bookings_cancelled_by_users"), "bookings", type_="foreignkey")
    op.drop_column("bookings", "cancelled_by")
