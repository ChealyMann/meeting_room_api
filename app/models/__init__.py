"""All tables, one per file. Importing this package registers every model on `Base.metadata`."""

from app.models.base import Base, utcnow
from app.models.booking import Booking
from app.models.booking_door_pass import BookingDoorPass
from app.models.booking_participant import BookingParticipant
from app.models.booking_rejection import BookingRejection
from app.models.booking_review import BookingReview
from app.models.booking_session import BookingSession
from app.models.building import Building
from app.models.category import Category
from app.models.catering_order import CateringOrder
from app.models.catering_package import CateringPackage
from app.models.department import Department
from app.models.division import Division
from app.models.equipment import Equipment
from app.models.floor import Floor
from app.models.it_service import ITService
from app.models.it_ticket import ITTicket
from app.models.it_ticket_staff import it_ticket_staff
from app.models.location import Location
from app.models.position import Position
from app.models.public_holiday import PublicHoliday
from app.models.role import Role
from app.models.room import Room
from app.models.room_equipment import room_equipment
from app.models.room_photo import RoomPhoto
from app.models.user import User
from app.models.user_roles import user_roles

__all__ = [
    "Base",
    "Booking",
    "BookingDoorPass",
    "BookingParticipant",
    "BookingRejection",
    "BookingReview",
    "BookingSession",
    "Building",
    "CateringOrder",
    "CateringPackage",
    "Category",
    "Department",
    "Division",
    "Equipment",
    "Floor",
    "ITService",
    "ITTicket",
    "Location",
    "Position",
    "PublicHoliday",
    "Role",
    "Room",
    "RoomPhoto",
    "User",
    "it_ticket_staff",
    "room_equipment",
    "user_roles",
    "utcnow",
]
