"""The request slip's settings (one row): the Director of Cabinet and the address line."""

from sqlalchemy.orm import Session

from app.models import SlipSettings, User
from app.services.records import get_reference, save

ROW_ID = 1


def get_slip_settings(session: Session) -> SlipSettings:
    """The one row; made with the defaults on first use (the migration also adds it).

    Only flushed, never committed here: a booking's confirm reads it mid-transaction, and the
    caller that owns the transaction commits (or rolls back) everything together."""
    row = session.get(SlipSettings, ROW_ID)
    if row is None:
        row = SlipSettings(id=ROW_ID)
        session.add(row)
        session.flush()
    return row


def update_slip_settings(session: Session, data: dict) -> SlipSettings:
    if data["director_user_id"] is not None:
        get_reference(session, User, data["director_user_id"], "director_user_id", "User")
    row = get_slip_settings(session)
    row.director_user_id = data["director_user_id"]
    row.address_kh = data["address_kh"]
    save(session)
    session.refresh(row)
    return row
