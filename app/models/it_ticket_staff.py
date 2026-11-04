from sqlalchemy import Column, ForeignKey, Table

from app.models.base import MYSQL_TABLE, Base, UnsignedInt

# Which IT Staff users are assigned to which ticket. The composite primary key stops a user
# being assigned twice.
it_ticket_staff = Table(
    "it_ticket_staff",
    Base.metadata,
    Column(
        "ticket_id",
        UnsignedInt,
        ForeignKey("it_tickets.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
    ),
    Column(
        "user_id",
        UnsignedInt,
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
        index=True,
    ),
    **MYSQL_TABLE,
)
