"""bookings get confirmed_at; booking_signers keep the request slip's signers (snapshot)

Revision ID: e8f1a3c5d7b9
Revises: d6e2a4b8c1f9
Create Date: 2026-11-13 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "e8f1a3c5d7b9"
down_revision: str | Sequence[str] | None = "d6e2a4b8c1f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UINT = mysql.INTEGER(unsigned=True)


def upgrade() -> None:
    op.add_column("bookings", sa.Column("confirmed_at", sa.DateTime(), nullable=True))
    # Confirmed before this column: IT ready time, else the last approval, else when sent.
    op.execute(
        """
        UPDATE bookings b
        SET b.confirmed_at = COALESCE(
            (SELECT t.ready_at FROM it_tickets t WHERE t.booking_id = b.id),
            (SELECT MAX(r.reviewed_at) FROM booking_reviews r
              WHERE r.booking_id = b.id AND r.decision = 'APPROVED'),
            b.created_at)
        WHERE b.status = 'CONFIRMED'
        """
    )
    op.create_table(
        "booking_signers",
        sa.Column("id", UINT, autoincrement=True, nullable=False),
        sa.Column("booking_id", UINT, nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("user_id", UINT, nullable=True),
        sa.Column("name_kh", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=20), nullable=True),
        sa.Column("signature_path", sa.String(length=3000), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name=op.f("fk_booking_signers_booking_id_bookings"),
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_booking_signers_user_id_users"),
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_signers")),
        sa.UniqueConstraint("booking_id", "role", name=op.f("uq_booking_signers_booking_id_role")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_booking_signers_user_id"), "booking_signers", ["user_id"])


def downgrade() -> None:
    op.drop_table("booking_signers")
    op.drop_column("bookings", "confirmed_at")
