"""How a booking is shown: the list item and the detail answers (spec 9.1).

`booking_load_options()` preloads what a list item reads, so a page of bookings costs a
fixed number of queries. The Pitika, owner and IT lists reuse it.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.models import Booking, Building, Floor, Room, User
from app.schemas.booking import (
    BookingDetail,
    BookingListItem,
    BookingRoomRef,
    CateringOut,
    ITOut,
    LocalMoment,
    PersonRef,
    RejectionOut,
    ReviewOut,
    SessionOut,
)
from app.schemas.refs import NamedRef, ProvinceRef
from app.services import booking_transitions as transitions


def booking_load_options() -> tuple:
    """Loader options for a list of bookings: everything a `BookingListItem` reads.
    Use as `select(Booking).options(*booking_load_options())`."""
    return (
        selectinload(Booking.sessions),
        selectinload(Booking.catering_order),
        selectinload(Booking.it_ticket),
        selectinload(Booking.requester),
        selectinload(Booking.room)
        .selectinload(Room.floor)
        .selectinload(Floor.building)
        .selectinload(Building.location),
    )


def room_ref(room: Room) -> BookingRoomRef:
    location = room.floor.building.location
    return BookingRoomRef(
        id=room.id,
        name_en=room.name_en,
        name_kh=room.name_kh,
        is_private=room.is_private,
        location=NamedRef.model_validate(location),
        province=ProvinceRef.from_code(location.province),
    )


def _person(user: User | None) -> PersonRef | None:
    return PersonRef.model_validate(user) if user else None


def _list_item_fields(booking: Booking) -> dict[str, Any]:
    return {
        "id": booking.id,
        "reference_code": booking.reference_code,
        "room": room_ref(booking.room),
        "meeting_title": booking.meeting_title,
        "meeting_type": booking.meeting_type,
        "route": booking.route,
        "status": booking.status,
        "display_status": transitions.display_status(booking),
        "requester": NamedRef.model_validate(booking.requester),
        "first_session": SessionOut.model_validate(booking.sessions[0]),
        "session_count": len(booking.sessions),
        "attendees": booking.attendees,
        "has_catering": booking.catering_order is not None,
        "has_it": booking.it_ticket is not None,
        "created_at": booking.created_at,
        "version": booking.version,
    }


def build_booking_list_items(session: Session, bookings: list[Booking]) -> list[BookingListItem]:
    return [BookingListItem(**_list_item_fields(booking)) for booking in bookings]


def _catering_out(booking: Booking) -> CateringOut | None:
    order = booking.catering_order
    if order is None:
        return None
    delivery = transitions.first_start(booking)
    return CateringOut(
        packages=order.packages,
        remarks=order.remarks,
        servings=booking.attendees,  # B-25: always the current attendees
        delivery_date=delivery.date(),
        delivery_time=delivery.time(),
        approver_notes=order.approver_notes,
        decided_by=_person(order.decider),
        decided_at=order.decided_at,
    )


def _it_out(booking: Booking, settings: Settings) -> ITOut | None:
    ticket = booking.it_ticket
    if ticket is None:
        return None
    setup = transitions.setup_start(booking, settings.it_setup_lead_minutes)
    return ITOut(
        ticket_id=ticket.id,
        items=ticket.requested_items,
        special_requirements=ticket.special_requirements,
        status=ticket.status,
        technician_notes=ticket.technician_notes,
        staff=[NamedRef.model_validate(user) for user in ticket.staff],
        setup_date=setup.date(),
        setup_time=setup.time(),
        forwarded_at=ticket.forwarded_at,
        assigned_at=ticket.assigned_at,
        ready_at=ticket.ready_at,
    )


def _users_by_id(session: Session, ids: set[int | None]) -> dict[int, User]:
    ids = {user_id for user_id in ids if user_id is not None}
    if not ids:
        return {}
    return {user.id: user for user in session.scalars(select(User).where(User.id.in_(ids)))}


def build_booking_detail(session: Session, booking: Booking, settings: Settings) -> BookingDetail:
    rejection = booking.rejection
    users = _users_by_id(
        session,
        {review.reviewer_id for review in booking.reviews}
        | {rejection.actor_user_id if rejection else None},
    )
    end = transitions.last_end(booking)
    return BookingDetail(
        **_list_item_fields(booking),
        requester_info=booking.requester_info,
        meeting_purpose=booking.meeting_purpose,
        private_justification=booking.private_justification,
        participant_emails=[p.email for p in sorted(booking.participants, key=lambda p: p.id)],
        sessions=[SessionOut.model_validate(s) for s in booking.sessions],
        last_end=LocalMoment(date=end.date(), time=end.time()),
        catering=_catering_out(booking),
        it=_it_out(booking, settings),
        reviews=[
            ReviewOut(
                stage=review.stage,
                decision=review.decision,
                reviewer=_person(users.get(review.reviewer_id)),
                notes=review.notes,
                reviewed_at=review.reviewed_at,
            )
            for review in booking.reviews
        ],
        rejection=RejectionOut(
            rejected_by=rejection.rejected_by,
            actor=_person(users.get(rejection.actor_user_id)),
            reason=rejection.reason,
            decided_at=rejection.decided_at,
        )
        if rejection
        else None,
        cancelled_at=booking.cancelled_at,
        cancel_reason=booking.cancel_reason,
        updated_at=booking.updated_at,
    )
