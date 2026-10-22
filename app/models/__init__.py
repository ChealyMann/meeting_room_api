"""All tables, one per file. Importing this package registers every model on `Base.metadata`."""

from app.models.base import Base, utcnow
from app.models.building import Building
from app.models.category import Category
from app.models.department import Department
from app.models.division import Division
from app.models.equipment import Equipment
from app.models.floor import Floor
from app.models.location import Location
from app.models.position import Position
from app.models.role import Role
from app.models.room import Room
from app.models.room_equipment import room_equipment
from app.models.room_photo import RoomPhoto
from app.models.user import User
from app.models.user_roles import user_roles

__all__ = [
    "Base",
    "Building",
    "Category",
    "Department",
    "Division",
    "Equipment",
    "Floor",
    "Location",
    "Position",
    "Role",
    "Room",
    "RoomPhoto",
    "User",
    "room_equipment",
    "user_roles",
    "utcnow",
]
