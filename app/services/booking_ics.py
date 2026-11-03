"""The calendar file of a booking (spec 9.10, B-18): hand-written iCalendar text.

One VEVENT per session, times in UTC with `Z`, lines end with CRLF. The door pass is never
written to the file."""

from app.constants.booking import BookingStatus
from app.models import Booking
from app.services.clock import local_to_utc, now_utc, session_end, session_start

LINE_END = "\r\n"
MAX_LINE_BYTES = 75
TIME_FORMAT = "%Y%m%dT%H%M%SZ"

_STATUS = {
    BookingStatus.PENDING_PITIKA: "TENTATIVE",
    BookingStatus.PENDING_OWNER: "TENTATIVE",
    BookingStatus.SETUP_IN_PROGRESS: "TENTATIVE",
    BookingStatus.CONFIRMED: "CONFIRMED",
    BookingStatus.REJECTED: "CANCELLED",
    BookingStatus.CANCELLED: "CANCELLED",
}


def escape_text(value: str) -> str:
    """Escape `\\`, `;`, `,` and new lines (RFC 5545 TEXT)."""
    value = value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return value.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")


def fold_line(line: str) -> str:
    """Split a line longer than 75 bytes (UTF-8). Each next part starts with one space and
    so holds 74 bytes. A multi-byte character is never cut."""
    parts: list[str] = []
    current = ""
    size = 0
    limit = MAX_LINE_BYTES
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > limit:
            parts.append(current)
            current, size, limit = "", 1, MAX_LINE_BYTES  # the leading space counts
        current += char
        size += width
    parts.append(current)
    return (LINE_END + " ").join(parts)


def _stamp(value) -> str:
    return value.strftime(TIME_FORMAT)


def _location(booking: Booking) -> str:
    room = booking.room
    building = room.floor.building
    return ", ".join([room.name_en, building.name_en, building.location.name_en])


def build_ics(booking: Booking) -> str:
    """The calendar text of a booking. The caller has checked that the user can see it."""
    stamp = _stamp(now_utc())
    status = _STATUS[BookingStatus(booking.status)]
    title = escape_text(booking.meeting_title)
    place = escape_text(_location(booking))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NBC//Room Booking//EN", "METHOD:PUBLISH"]
    for item in sorted(booking.sessions, key=lambda s: (s.date, s.start_time, s.id)):
        lines += [
            "BEGIN:VEVENT",
            f"UID:booking-{booking.id}-session-{item.id}@nbc-room-booking",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{_stamp(local_to_utc(session_start(item)))}",
            f"DTEND:{_stamp(local_to_utc(session_end(item)))}",
            f"SUMMARY:{title}",
            f"LOCATION:{place}",
            f"DESCRIPTION:Reference {escape_text(booking.reference_code)}",
            f"STATUS:{status}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "".join(fold_line(line) + LINE_END for line in lines)
