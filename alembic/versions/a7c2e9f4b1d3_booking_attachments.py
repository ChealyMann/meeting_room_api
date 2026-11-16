"""booking_attachments: documents the booker adds to a booking

Revision ID: a7c2e9f4b1d3
Revises: e8f1a3c5d7b9
Create Date: 2026-11-16 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "a7c2e9f4b1d3"
down_revision: str | Sequence[str] | None = "e8f1a3c5d7b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UINT = mysql.INTEGER(unsigned=True)


def upgrade() -> None:
    op.create_table(
        "booking_attachments",
        sa.Column("id", UINT, autoincrement=True, nullable=False),
        sa.Column("booking_id", UINT, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", UINT, nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("uploaded_by", UINT, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name=op.f("fk_booking_attachments_booking_id_bookings"),
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            name=op.f("fk_booking_attachments_uploaded_by_users"),
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_attachments")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_booking_attachments_booking_id"), "booking_attachments", ["booking_id"]
    )
    op.create_index(
        op.f("ix_booking_attachments_uploaded_by"), "booking_attachments", ["uploaded_by"]
    )


def downgrade() -> None:
    op.drop_table("booking_attachments")
