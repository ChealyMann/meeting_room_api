"""All tables. Importing this package registers every model on `Base.metadata`."""

from app.models.base import Base, utcnow
from app.models.organisation import Department, Division, Position
from app.models.places import Building, Floor, Location
from app.models.rooms import Category, Equipment, Room, RoomPhoto, room_equipment
from app.models.users import Role, User, user_roles

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
