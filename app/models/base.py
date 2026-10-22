from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, MetaData, text
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Every table: InnoDB, utf8mb4, case- and accent-insensitive comparisons (spec section 6).
MYSQL_TABLE = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}

UnsignedInt = INTEGER(unsigned=True)


def utcnow() -> datetime:
    """Current UTC time, naive, whole seconds: what a MySQL DATETIME column stores."""
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class IdMixin:
    id: Mapped[int] = mapped_column(
        UnsignedInt, primary_key=True, autoincrement=True, sort_order=-100
    )


class TimestampMixin:
    # Set by the app in UTC. `onupdate` fires only when an UPDATE is sent, which SQLAlchemy
    # does only when a value really changed, so `updated_at` stays put on no-op changes.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, sort_order=100)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, sort_order=100
    )


class ActiveMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))


class SortOrderMixin:
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
