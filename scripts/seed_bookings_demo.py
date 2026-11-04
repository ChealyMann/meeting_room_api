"""Demo bookings for development: users for each role, three more rooms, catering packages,
IT services, a public holiday, and about a dozen bookings in every status, dated around today.

NOT for production. Run it by hand on a dev database, after `python -m scripts.seed`:

    python -m scripts.seed_bookings_demo

It needs one active office with a floor and a division (any). Demo users sign in with the
password DEMO_PASSWORD. Safe to run many times: users, rooms and catalog rows are matched by
email or name and only added when missing; the bookings are added only when no demo user has
one yet. Rows are written directly (no booking rules run), like the test factories.
"""

import sys
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants.booking import (
    EXPIRY_REASON,
    BookingRoute,
    BookingStatus,
    ITStatus,
    MeetingType,
    RejectedBy,
    ReviewDecision,
    ReviewStage,
)
from app.constants.roles import RoleCode
from app.db import create_db_engine
from app.models import (
    Booking,
    BookingDoorPass,
    BookingParticipant,
    BookingRejection,
    BookingReview,
    BookingSession,
    Category,
    CateringOrder,
    CateringPackage,
    Division,
    Floor,
    ITService,
    ITTicket,
    Position,
    PublicHoliday,
    Role,
    Room,
    User,
    user_roles,
)
from app.security import hash_password
from app.services import booking_codes, clock
from app.services.booking import requester_info

DEMO_PASSWORD = "Demo@12345"

DEMO_USERS = [
    ("demo.pitika@example.com", "Chan Sophea", "ចាន់ សុភា", RoleCode.PITIKA),
    ("demo.owner@example.com", "Keo Vanna", "កែវ វណ្ណា", RoleCode.ROOM_OWNER),
    ("demo.itlead@example.com", "Lim Dara", "លឹម ដារា", RoleCode.IT_LEAD),
    ("demo.itstaff@example.com", "Sok Pisey", "សុខ ពិសី", RoleCode.IT_STAFF),
    ("demo.staff1@example.com", "Heng Rathana", "ហេង រតនា", RoleCode.STAFF),
    ("demo.staff2@example.com", "Meas Sreyneang", "មាស ស្រីនាង", RoleCode.STAFF),
    ("demo.staff3@example.com", "Touch Bunthoeun", "ទូច ប៊ុនធឿន", RoleCode.STAFF),
]

# name_en, name_kh, seats, private (owner = the demo room owner)
DEMO_ROOMS = [
    ("Tonle Sap Room", "បន្ទប់ទន្លេសាប", 20, False),
    ("Angkor Hall", "សាលអង្គរ", 80, False),
    ("Governor Room", "បន្ទប់ទេសាភិបាល", 12, True),
]

DEMO_PACKAGES = [
    ("Coffee break", "Coffee, tea, water and pastries"),
    ("Lunch box", "Rice, one main dish, fruit and water"),
    ("Fruit and water", "Seasonal fruit and bottled water"),
]
DEMO_SERVICES = [
    ("Projector setup", "Projector, screen and HDMI cable"),
    ("Video call", "Zoom or Teams on the room PC, camera and speaker"),
    ("Microphones", "Two wireless microphones and the room speakers"),
]
DEMO_HOLIDAYS = [(date(2026, 11, 9), "ទិវាបុណ្យឯករាជ្យជាតិ", "Independence Day")]


def _one(session: Session, model, **where):
    return session.scalars(select(model).filter_by(**where)).first()


def _users(session: Session, division: Division, position: Position) -> dict[str, User]:
    role_ids = {r.code: r.id for r in session.scalars(select(Role))}
    users: dict[str, User] = {}
    for n, (email, name_en, name_kh, role) in enumerate(DEMO_USERS, start=1):
        user = _one(session, User, email=email)
        if user is None:
            user = User(
                staff_id=f"DEMO-{n:03d}",
                name_en=name_en,
                name_kh=name_kh,
                email=email,
                phone=f"012 000 {n:03d}",
                password_hash=hash_password(DEMO_PASSWORD),
                must_change_password=False,
                division_id=division.id,
                position_id=position.id,
            )
            session.add(user)
            session.flush()
            session.execute(user_roles.insert().values(user_id=user.id, role_id=role_ids[role]))
            print(f"  user {email} ({role})")
        users[role if role != RoleCode.STAFF else email] = user
    return users


def _rooms(session: Session, floor: Floor, category: Category, owner: User) -> dict[str, Room]:
    rooms: dict[str, Room] = {}
    for name_en, name_kh, seats, private in DEMO_ROOMS:
        room = _one(session, Room, name_en=name_en, floor_id=floor.id)
        if room is None:
            room = Room(
                name_en=name_en,
                name_kh=name_kh,
                floor_id=floor.id,
                category_id=category.id,
                capacity=seats,
                start_time=time(7, 30),
                end_time=time(18, 0),
                is_private=private,
                room_owner_id=owner.id if private else None,
                short_desc=f"Demo room, {seats} seats",
            )
            session.add(room)
            session.flush()
            print(f"  room {name_en}")
        rooms[name_en] = room
    return rooms


def _catalog(session: Session, model, rows) -> list:
    found = []
    for i, (name, description) in enumerate(rows):
        record = _one(session, model, name=name)
        if record is None:
            record = model(name=name, description=description, sort_order=i)
            session.add(record)
            session.flush()
            print(f"  {model.__tablename__} {name}")
        found.append(record)
    return found


def _holidays(session: Session) -> None:
    for day, name_km, name_en in DEMO_HOLIDAYS:
        if _one(session, PublicHoliday, holiday_date=day) is None:
            session.add(PublicHoliday(holiday_date=day, name_km=name_km, name_en=name_en))
            print(f"  holiday {day} {name_en}")


class _Booker:
    """Adds one booking with its rows, the way the API would have left them."""

    def __init__(self, session: Session, pitika: User, owner: User, it_staff: User):
        self.session = session
        self.pitika = pitika
        self.owner = owner
        self.it_staff = it_staff
        self.now = clock.now_utc()

    def add(
        self,
        room: Room,
        booker: User,
        title: str,
        sessions,
        status: BookingStatus,
        route: BookingRoute = BookingRoute.R1,
        *,
        attendees: int = 8,
        meeting_type: MeetingType = MeetingType.INTERNAL,
        purpose: str | None = None,
        why_private: str | None = None,
        food=None,
        it=None,
        it_status: ITStatus | None = None,
        reviews=(),
        rejected_by: RejectedBy | None = None,
        reason: str | None = None,
        cancelled: str | None = None,
        emails=(),
    ) -> Booking:
        s = self.session
        booking = Booking(
            reference_code=booking_codes.new_reference_code(s, clock.now_local()),
            requester_id=booker.id,
            room_id=room.id,
            requester_info=requester_info(booker),
            meeting_title=title,
            meeting_type=meeting_type,
            meeting_purpose=purpose,
            attendees=attendees,
            private_justification=why_private,
            route=route,
            status=status,
            cancelled_at=self.now if cancelled else None,
            cancel_reason=cancelled,
        )
        s.add(booking)
        s.flush()
        blocking = status not in (BookingStatus.REJECTED, BookingStatus.CANCELLED)
        for day, start, end in sessions:
            s.add(
                BookingSession(
                    booking_id=booking.id,
                    room_id=room.id,
                    date=day,
                    start_time=start,
                    end_time=end,
                    is_blocking=blocking,
                )
            )
        for email in emails:
            s.add(BookingParticipant(booking_id=booking.id, email=email))
        for stage, decision in reviews:
            reviewer = (
                None
                if decision == ReviewDecision.NOT_REQUIRED
                else (self.pitika if stage == ReviewStage.PITIKA else self.owner)
            )
            s.add(
                BookingReview(
                    booking_id=booking.id,
                    stage=stage,
                    decision=decision,
                    reviewer_id=reviewer.id if reviewer else None,
                    notes="Looks fine." if reviewer else None,
                    reviewed_at=self.now,
                )
            )
        approved_food = any(
            st == ReviewStage.PITIKA and d == ReviewDecision.APPROVED for st, d in reviews
        )
        if food:
            s.add(
                CateringOrder(
                    booking_id=booking.id,
                    packages=[{"id": p.id, "name": p.name} for p in food],
                    remarks="Two vegetarian meals, please.",
                    approver_notes="Looks fine." if approved_food else None,
                    decided_by=self.pitika.id if approved_food else None,
                    decided_at=self.now if approved_food else None,
                )
            )
        if it:
            ticket = ITTicket(
                booking_id=booking.id,
                requested_items=[{"id": x.id, "name": x.name} for x in it],
                special_requirements="Test the video call 30 minutes before.",
                status=it_status or ITStatus.RECEIVED,
                forwarded_at=self.now
                if status == BookingStatus.SETUP_IN_PROGRESS or it_status
                else None,
                assigned_at=self.now if it_status in (ITStatus.ASSIGNED, ITStatus.READY) else None,
                ready_at=self.now if it_status == ITStatus.READY else None,
            )
            s.add(ticket)
            s.flush()
            if it_status in (ITStatus.ASSIGNED, ITStatus.READY):
                ticket.staff.append(self.it_staff)
        if rejected_by:
            actor = {RejectedBy.PITIKA: self.pitika, RejectedBy.OWNER: self.owner}.get(rejected_by)
            s.add(
                BookingRejection(
                    booking_id=booking.id,
                    rejected_by=rejected_by,
                    actor_user_id=actor.id if actor else None,
                    reason=reason,
                    decided_at=self.now,
                )
            )
            if actor:
                stage = (
                    ReviewStage.PITIKA if rejected_by == RejectedBy.PITIKA else ReviewStage.OWNER
                )
                s.add(
                    BookingReview(
                        booking_id=booking.id,
                        stage=stage,
                        decision=ReviewDecision.REJECTED,
                        reviewer_id=actor.id,
                        notes=reason,
                        reviewed_at=self.now,
                    )
                )
        if status == BookingStatus.CONFIRMED:
            last_end = max(datetime.combine(day, end) for day, _start, end in sessions)
            s.add(
                BookingDoorPass(
                    booking_id=booking.id,
                    passcode=booking_codes.new_door_pass_code(s, booking.reference_code),
                    expires_at=clock.local_to_utc(last_end),
                )
            )
        s.flush()
        return booking


def _bookings(
    session: Session, users: dict[str, User], rooms: dict[str, Room], packages, services
) -> int:
    staff = [users[e] for e, *_ in DEMO_USERS if e.startswith("demo.staff")]
    demo_ids = [u.id for u in users.values()]
    if session.scalars(select(Booking.id).where(Booking.requester_id.in_(demo_ids))).first():
        print("  bookings: demo users already have bookings; skipped")
        return 0
    mekong = session.scalars(
        select(Room).where(Room.name_en.notin_([r[0] for r in DEMO_ROOMS]))
    ).first()
    tonle, angkor, governor = rooms["Tonle Sap Room"], rooms["Angkor Hall"], rooms["Governor Room"]
    big = mekong or angkor
    today = clock.now_local().date()

    def day(n: int) -> date:
        return today + timedelta(days=n)

    pitika_ok = [(ReviewStage.PITIKA, ReviewDecision.APPROVED)]
    owner_ok = pitika_ok + [(ReviewStage.OWNER, ReviewDecision.APPROVED)]
    b = _Booker(
        session, users[RoleCode.PITIKA], users[RoleCode.ROOM_OWNER], users[RoleCode.IT_STAFF]
    )

    b.add(
        tonle,
        staff[0],
        "Monthly budget review",
        [(day(1), time(9), time(10, 30))],
        BookingStatus.PENDING_PITIKA,
        attendees=12,
        purpose="Review October spending and plan December.",
        food=packages[:1],
        it=services[:1],
        emails=["finance.team@example.com"],
    )
    b.add(
        angkor,
        staff[1],
        "New staff training",
        [(day(2), time(14), time(16)), (day(3), time(14), time(16))],
        BookingStatus.PENDING_PITIKA,
        attendees=40,
        purpose="Two afternoons of training for new staff.",
    )
    b.add(
        governor,
        staff[2],
        "Meeting with the Governor's office",
        [(day(3), time(10), time(11))],
        BookingStatus.PENDING_OWNER,
        BookingRoute.R2,
        attendees=6,
        meeting_type=MeetingType.INTERNAL_WITH_GOVERNOR,
        why_private="The Governor's team asked for a private room.",
        reviews=pitika_ok,
    )
    b.add(
        tonle,
        staff[1],
        "Video call with the IMF team",
        [(day(1), time(14), time(15))],
        BookingStatus.SETUP_IN_PROGRESS,
        attendees=8,
        meeting_type=MeetingType.EXTERNAL,
        food=packages[:1],
        it=services[1:2],
        reviews=pitika_ok,
    )
    b.add(
        big,
        staff[0],
        "Payment systems workshop",
        [(day(2), time(9), time(12))],
        BookingStatus.SETUP_IN_PROGRESS,
        attendees=60,
        food=packages[:2],
        it=services,
        it_status=ITStatus.ASSIGNED,
        reviews=pitika_ok,
    )
    b.add(
        big,
        staff[2],
        "Department lunch meeting",
        [(day(0), time(16), time(17))],
        BookingStatus.CONFIRMED,
        attendees=25,
        food=packages[1:],
        reviews=pitika_ok,
    )
    b.add(
        governor,
        users[RoleCode.ROOM_OWNER],
        "Owner's planning session",
        [(day(4), time(9), time(10))],
        BookingStatus.CONFIRMED,
        BookingRoute.R3,
        attendees=4,
        reviews=[(ReviewStage.PITIKA, ReviewDecision.NOT_REQUIRED)],
    )
    b.add(
        tonle,
        staff[0],
        "Weekly team sync",
        [(day(-2), time(10), time(11))],
        BookingStatus.CONFIRMED,
        attendees=10,
        reviews=pitika_ok,
    )
    b.add(
        governor,
        staff[1],
        "Bank partners dinner planning",
        [(day(5), time(15), time(16))],
        BookingStatus.CONFIRMED,
        BookingRoute.R2,
        attendees=8,
        meeting_type=MeetingType.EXTERNAL_WITH_GOVERNOR,
        why_private="Guests from partner banks.",
        reviews=owner_ok,
    )
    b.add(
        angkor,
        staff[2],
        "Football club meeting",
        [(day(5), time(10), time(11))],
        BookingStatus.REJECTED,
        attendees=30,
        rejected_by=RejectedBy.PITIKA,
        reason="Not a work meeting. Please use the canteen.",
    )
    b.add(
        big,
        staff[1],
        "Quarterly report rehearsal",
        [(day(6), time(13), time(15))],
        BookingStatus.CANCELLED,
        attendees=15,
        cancelled="The report date moved to next month.",
    )
    b.add(
        tonle,
        staff[2],
        "Audit kick-off",
        [(day(-1), time(9), time(10))],
        BookingStatus.REJECTED,
        attendees=7,
        rejected_by=RejectedBy.SYSTEM,
        reason=EXPIRY_REASON,
    )
    return 12


def seed_bookings_demo(session: Session) -> None:
    division = session.scalars(select(Division).where(Division.is_active)).first()
    floor = session.scalars(select(Floor).where(Floor.is_active)).first()
    category = session.scalars(select(Category).where(Category.is_active)).first()
    position = session.scalars(select(Position).where(Position.is_active)).first()
    missing = [
        n
        for n, v in [
            ("division", division),
            ("floor", floor),
            ("room type", category),
            ("position", position),
        ]
        if v is None
    ]
    if missing:
        raise SystemExit(
            f"Add an active {', '.join(missing)} first (dashboard or scripts.seed_demo)."
        )
    users = _users(session, division, position)
    rooms = _rooms(session, floor, category, users[RoleCode.ROOM_OWNER])
    packages = _catalog(session, CateringPackage, DEMO_PACKAGES)
    services = _catalog(session, ITService, DEMO_SERVICES)
    _holidays(session)
    session.flush()
    added = _bookings(session, users, rooms, packages, services)
    print(f"  bookings added: {added}")


def main() -> int:
    engine = create_db_engine(get_settings().database_url)
    with Session(engine) as session, session.begin():
        seed_bookings_demo(session)
    print(f"Done. Demo users sign in with the password {DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
