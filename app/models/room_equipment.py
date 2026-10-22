from sqlalchemy import Column, ForeignKey, Table

from app.models.base import MYSQL_TABLE, Base, UnsignedInt

# Which rooms have which equipment. No quantity and no timestamps.
room_equipment = Table(
    "room_equipment",
    Base.metadata,
    Column(
        "room_id",
        UnsignedInt,
        ForeignKey("rooms.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
    ),
    Column(
        "equipment_id",
        UnsignedInt,
        ForeignKey("equipment.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        primary_key=True,
        index=True,
    ),
    **MYSQL_TABLE,
)
