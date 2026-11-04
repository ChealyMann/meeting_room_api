"""Fixed values for room bookings (spec section 6)."""

from enum import StrEnum


class BookingStatus(StrEnum):
    PENDING_PITIKA = "PENDING_PITIKA"
    PENDING_OWNER = "PENDING_OWNER"
    SETUP_IN_PROGRESS = "SETUP_IN_PROGRESS"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class DisplayStatus(StrEnum):
    """What a reader sees: the six statuses, plus COMPLETED for a confirmed booking that ended."""

    PENDING_PITIKA = "PENDING_PITIKA"
    PENDING_OWNER = "PENDING_OWNER"
    SETUP_IN_PROGRESS = "SETUP_IN_PROGRESS"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class MeetingType(StrEnum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"
    INTERNAL_WITH_GOVERNOR = "INTERNAL_WITH_GOVERNOR"
    EXTERNAL_WITH_GOVERNOR = "EXTERNAL_WITH_GOVERNOR"


class ReviewStage(StrEnum):
    PITIKA = "PITIKA"
    OWNER = "OWNER"


class ReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NOT_REQUIRED = "NOT_REQUIRED"


class RejectedBy(StrEnum):
    PITIKA = "PITIKA"
    OWNER = "OWNER"
    SYSTEM = "SYSTEM"


class ITStatus(StrEnum):
    RECEIVED = "RECEIVED"
    ASSIGNED = "ASSIGNED"
    READY = "READY"


class BookingRoute(StrEnum):
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"


class BookingStep(StrEnum):
    """The steps in the answer of the check endpoint."""

    PITIKA = "PITIKA"
    OWNER = "OWNER"
    IT_SETUP = "IT_SETUP"
    CONFIRMED = "CONFIRMED"


# A final booking never changes again. A pending one is still waiting for a reviewer.
FINAL = {BookingStatus.REJECTED, BookingStatus.CANCELLED}
PENDING = {BookingStatus.PENDING_PITIKA, BookingStatus.PENDING_OWNER}

MASKED_TITLE = "Reserved (Private Session)"
EXPIRY_REASON = "Expired: not approved before the meeting time."
BOOKER_OFF_REASON = "Cancelled: the booker's account was turned off."
REFERENCE_PREFIX = "NBC-"
