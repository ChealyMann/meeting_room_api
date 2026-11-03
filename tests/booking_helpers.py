"""Shared pieces for the booking tests."""

from datetime import date, datetime

# A fixed Monday 08:00 local: "tomorrow 09:00" is always a valid time to book.
NOW = datetime(2026, 11, 9, 8, 0)
# The day after NOW.
DAY = date(2026, 11, 10)


def error(response) -> tuple[int, str]:
    """The status code and error code of an error response."""
    return response.status_code, response.json()["error"]["code"]


def fields(response) -> dict:
    """The `fields` of an error response."""
    return response.json()["error"]["fields"]


def current_for(session, user):
    """A `CurrentUser` for `user`, with the roles saved in the database."""
    from app.security import CurrentUser, load_role_codes

    return CurrentUser(user=user, role_codes=load_role_codes(session, user.id))
