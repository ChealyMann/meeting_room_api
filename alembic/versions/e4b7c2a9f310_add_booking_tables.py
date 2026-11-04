"""add the room booking tables

Revision ID: e4b7c2a9f310
Revises: d5a8c3e17f42
Create Date: 2026-11-03 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "e4b7c2a9f310"
down_revision: str | Sequence[str] | None = "d5a8c3e17f42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
    "mysql_engine": "InnoDB",
}


def _id() -> sa.Column:
    return sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False)


def _ref(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, mysql.INTEGER(unsigned=True), nullable=nullable)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def _fk(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column],
        [f"{target}.id"],
        name=op.f(f"fk_{table}_{column}_{target}"),
        onupdate="RESTRICT",
        ondelete="RESTRICT",
    )


def _check_in(table: str, column: str, values: list[str]) -> sa.CheckConstraint:
    listed = ", ".join(f"'{value}'" for value in values)
    return sa.CheckConstraint(f"{column} IN ({listed})", name=op.f(f"ck_{table}_{column}_values"))


def _catalog(table: str) -> None:
    op.create_table(
        table,
        _id(),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        sa.UniqueConstraint("name", name=op.f(f"uq_{table}_name")),
        **TABLE_OPTIONS,
    )


def upgrade() -> None:
    """Twelve tables for room bookings (spec section 7). No data changes."""
    _catalog("catering_packages")
    _catalog("it_services")
    op.create_table(
        "public_holidays",
        _id(),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name_km", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("remarks", sa.String(length=1000), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_public_holidays")),
        sa.UniqueConstraint("holiday_date", name=op.f("uq_public_holidays_holiday_date")),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "bookings",
        _id(),
        sa.Column("reference_code", sa.String(length=20), nullable=False),
        _ref("requester_id"),
        _ref("room_id"),
        sa.Column("requester_info", sa.JSON(), nullable=False),
        sa.Column("meeting_title", sa.String(length=200), nullable=False),
        sa.Column("meeting_type", sa.String(length=30), nullable=False),
        sa.Column("meeting_purpose", sa.String(length=1000), nullable=True),
        sa.Column("attendees", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("private_justification", sa.String(length=1000), nullable=True),
        sa.Column("route", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.Column("version", mysql.INTEGER(unsigned=True), nullable=False),
        *_timestamps(),
        _check_in(
            "bookings",
            "meeting_type",
            ["INTERNAL", "EXTERNAL", "INTERNAL_WITH_GOVERNOR", "EXTERNAL_WITH_GOVERNOR"],
        ),
        _check_in("bookings", "route", ["R1", "R2", "R3", "R4"]),
        _check_in(
            "bookings",
            "status",
            [
                "PENDING_PITIKA",
                "PENDING_OWNER",
                "SETUP_IN_PROGRESS",
                "CONFIRMED",
                "REJECTED",
                "CANCELLED",
            ],
        ),
        sa.CheckConstraint("attendees >= 1", name=op.f("ck_bookings_attendees_min")),
        _fk("bookings", "requester_id", "users"),
        _fk("bookings", "room_id", "rooms"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
        sa.UniqueConstraint("reference_code", name=op.f("uq_bookings_reference_code")),
        **TABLE_OPTIONS,
    )
    op.create_index(op.f("ix_bookings_requester_id"), "bookings", ["requester_id"], unique=False)
    op.create_index(op.f("ix_bookings_room_id"), "bookings", ["room_id"], unique=False)
    op.create_index(op.f("ix_bookings_status"), "bookings", ["status"], unique=False)

    op.create_table(
        "booking_sessions",
        _id(),
        _ref("booking_id"),
        _ref("room_id"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_blocking", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("start_time < end_time", name=op.f("ck_booking_sessions_time_order")),
        _fk("booking_sessions", "booking_id", "bookings"),
        _fk("booking_sessions", "room_id", "rooms"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_sessions")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_booking_sessions_booking_id"), "booking_sessions", ["booking_id"], unique=False
    )
    op.create_index(
        op.f("ix_booking_sessions_room_id_date_is_blocking"),
        "booking_sessions",
        ["room_id", "date", "is_blocking"],
        unique=False,
    )

    op.create_table(
        "booking_reviews",
        _id(),
        _ref("booking_id"),
        sa.Column("stage", sa.String(length=10), nullable=False),
        sa.Column("decision", sa.String(length=15), nullable=False),
        _ref("reviewer_id", nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        _check_in("booking_reviews", "stage", ["PITIKA", "OWNER"]),
        _check_in("booking_reviews", "decision", ["APPROVED", "REJECTED", "NOT_REQUIRED"]),
        _fk("booking_reviews", "booking_id", "bookings"),
        _fk("booking_reviews", "reviewer_id", "users"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_reviews")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_booking_reviews_booking_id"), "booking_reviews", ["booking_id"], unique=False
    )

    op.create_table(
        "booking_rejections",
        _id(),
        _ref("booking_id"),
        sa.Column("rejected_by", sa.String(length=10), nullable=False),
        _ref("actor_user_id", nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        _check_in("booking_rejections", "rejected_by", ["PITIKA", "OWNER", "SYSTEM"]),
        _fk("booking_rejections", "booking_id", "bookings"),
        _fk("booking_rejections", "actor_user_id", "users"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_rejections")),
        sa.UniqueConstraint("booking_id", name=op.f("uq_booking_rejections_booking_id")),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "booking_door_passes",
        _id(),
        _ref("booking_id"),
        sa.Column("passcode", sa.String(length=10), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        _fk("booking_door_passes", "booking_id", "bookings"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_door_passes")),
        sa.UniqueConstraint("booking_id", name=op.f("uq_booking_door_passes_booking_id")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_booking_door_passes_passcode"), "booking_door_passes", ["passcode"], unique=False
    )

    op.create_table(
        "booking_participants",
        _id(),
        _ref("booking_id"),
        sa.Column("email", sa.String(length=254), nullable=False),
        _fk("booking_participants", "booking_id", "bookings"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_participants")),
        sa.UniqueConstraint(
            "booking_id", "email", name=op.f("uq_booking_participants_booking_id_email")
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "catering_orders",
        _id(),
        _ref("booking_id"),
        sa.Column("packages", sa.JSON(), nullable=False),
        sa.Column("remarks", sa.String(length=1000), nullable=True),
        sa.Column("approver_notes", sa.String(length=1000), nullable=True),
        _ref("decided_by", nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        _fk("catering_orders", "booking_id", "bookings"),
        _fk("catering_orders", "decided_by", "users"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catering_orders")),
        sa.UniqueConstraint("booking_id", name=op.f("uq_catering_orders_booking_id")),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "it_tickets",
        _id(),
        _ref("booking_id"),
        sa.Column("requested_items", sa.JSON(), nullable=False),
        sa.Column("special_requirements", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("technician_notes", sa.String(length=1000), nullable=True),
        sa.Column("forwarded_at", sa.DateTime(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("ready_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        _check_in("it_tickets", "status", ["RECEIVED", "ASSIGNED", "READY"]),
        _fk("it_tickets", "booking_id", "bookings"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_it_tickets")),
        sa.UniqueConstraint("booking_id", name=op.f("uq_it_tickets_booking_id")),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "it_ticket_staff",
        _ref("ticket_id"),
        _ref("user_id"),
        _fk("it_ticket_staff", "ticket_id", "it_tickets"),
        _fk("it_ticket_staff", "user_id", "users"),
        sa.PrimaryKeyConstraint("ticket_id", "user_id", name=op.f("pk_it_ticket_staff")),
        **TABLE_OPTIONS,
    )
    op.create_index(
        op.f("ix_it_ticket_staff_user_id"), "it_ticket_staff", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Drop the twelve tables, children first."""
    for table in (
        "it_ticket_staff",
        "it_tickets",
        "catering_orders",
        "booking_participants",
        "booking_door_passes",
        "booking_rejections",
        "booking_reviews",
        "booking_sessions",
        "bookings",
        "public_holidays",
        "it_services",
        "catering_packages",
    ):
        op.drop_table(table)
