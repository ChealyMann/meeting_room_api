from typing import Annotated

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.constants.booking import (
    BOOKER_OFF_REASON,
    EXPIRY_REASON,
    FINAL,
    MASKED_TITLE,
    PENDING,
    REFERENCE_PREFIX,
    BookingRoute,
    BookingStatus,
    BookingStep,
    DisplayStatus,
    ITStatus,
    MeetingType,
    RejectedBy,
    ReviewDecision,
    ReviewStage,
)
from app.errors import ErrorCode
from app.schemas.common import BookingText, NoHtml, OptionalBookingText


def values(enum) -> list[str]:
    return [member.value for member in enum]


def test_booking_status_values():
    assert values(BookingStatus) == [
        "PENDING_PITIKA",
        "PENDING_OWNER",
        "SETUP_IN_PROGRESS",
        "CONFIRMED",
        "REJECTED",
        "CANCELLED",
    ]


def test_display_status_is_the_six_plus_completed():
    assert values(DisplayStatus) == values(BookingStatus) + ["COMPLETED"]


def test_other_enums():
    assert values(MeetingType) == [
        "INTERNAL",
        "EXTERNAL",
        "INTERNAL_WITH_GOVERNOR",
        "EXTERNAL_WITH_GOVERNOR",
    ]
    assert values(ReviewStage) == ["PITIKA", "OWNER"]
    assert values(ReviewDecision) == ["APPROVED", "REJECTED", "NOT_REQUIRED"]
    assert values(RejectedBy) == ["PITIKA", "OWNER", "SYSTEM"]
    assert values(ITStatus) == ["RECEIVED", "ASSIGNED", "READY"]
    assert values(BookingRoute) == ["R1", "R2", "R3", "R4"]
    assert values(BookingStep) == ["PITIKA", "OWNER", "IT_SETUP", "CONFIRMED"]


def test_final_and_pending_sets():
    assert FINAL == {BookingStatus.REJECTED, BookingStatus.CANCELLED}
    assert PENDING == {BookingStatus.PENDING_PITIKA, BookingStatus.PENDING_OWNER}


def test_texts():
    assert MASKED_TITLE == "Reserved (Private Session)"
    assert EXPIRY_REASON == "Expired: not approved before the meeting time."
    assert BOOKER_OFF_REASON == "Cancelled: the booker's account was turned off."
    assert REFERENCE_PREFIX == "NBC-"


@pytest.mark.parametrize("text", ["Budget < 5000", "ប្រជុំ", "a<5"])
def test_no_html_allows(text):
    assert TypeAdapter(Annotated[str, NoHtml]).validate_python(text) == text


@pytest.mark.parametrize("text", ["<b>hi</b>", "x </script>", "<!-- c -->"])
def test_no_html_refuses(text):
    with pytest.raises(ValidationError, match="HTML is not allowed."):
        TypeAdapter(Annotated[str, NoHtml]).validate_python(text)


class Body(BaseModel):
    title: BookingText(10)
    note: OptionalBookingText(10) = None


def test_booking_text_trims_and_keeps_text():
    assert Body(title="  Team  ").title == "Team"


@pytest.mark.parametrize("title", ["", "   ", "<b>x</b>", "x" * 11])
def test_booking_text_refuses(title):
    with pytest.raises(ValidationError):
        Body(title=title)


def test_optional_booking_text():
    assert Body(title="a", note="  ").note is None
    assert Body(title="a", note=" hi ").note == "hi"
    with pytest.raises(ValidationError):
        Body(title="a", note="<i>x</i>")
    with pytest.raises(ValidationError):
        Body(title="a", note="x" * 11)


def test_new_error_codes():
    assert {
        "SCHEDULE_CONFLICT",
        "TIME_PASSED",
        "OUTSIDE_ROOM_HOURS",
        "ROOM_NOT_BOOKABLE",
        "NO_REVIEWER",
        "INVALID_TRANSITION",
        "STALE_VERSION",
        "FIELD_NOT_EDITABLE",
        "OWNER_REQUIRED",
        "OWNER_HAS_PRIVATE_ROOMS",
        "HAS_FUTURE_BOOKINGS",
        "HAS_PENDING_OWNER_BOOKINGS",
    } <= {code.value for code in ErrorCode}
