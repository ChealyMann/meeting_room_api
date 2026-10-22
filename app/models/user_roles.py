from sqlalchemy import Column, ForeignKey, Table

from app.models.base import MYSQL_TABLE, Base, UnsignedInt

# Which users have which roles. The composite primary key stops a role being given twice.
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        UnsignedInt,
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
    ),
    Column(
        "role_id",
        UnsignedInt,
        ForeignKey("roles.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
        index=True,
    ),
    **MYSQL_TABLE,
)
