from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.routers.common import AppSettings, DbSession, IdPath, PageParams, SearchQuery
from app.schemas.common import Page
from app.schemas.it_ticket import AssignStaffBody, ITSummary, ITTicketItem, ReadyBody
from app.security import ITLeadUser, ITUser
from app.services import it_ticket

router = APIRouter(prefix="/it/tickets", tags=["IT"])


@router.get("", response_model=Page[ITTicketItem], summary="List IT tickets")
def list_tickets(
    current: ITUser,
    session: DbSession,
    settings: AppSettings,
    paging: Annotated[PageParams, Depends()],
    status: Annotated[str | None, Query(description="RECEIVED, ASSIGNED or READY")] = None,
    q: SearchQuery = None,
    state: Annotated[
        Literal["to_assign", "in_progress", "done"] | None,
        Query(description="A dashboard tab: to_assign, in_progress or done (Ready or missed)"),
    ] = None,
    mine: Annotated[bool, Query(description="Only the tickets I am assigned to")] = False,
    date_from: Annotated[
        date | None, Query(alias="from", description="Setup (first session) on or after this day")
    ] = None,
    date_to: Annotated[
        date | None, Query(alias="to", description="Setup (first session) on or before this day")
    ] = None,
) -> Page[ITTicketItem]:
    """Tickets sent to IT, earliest first start first. The IT Lead sees all of them; IT Staff
    see the tickets they are assigned to. Rejected and cancelled bookings are left out. `q`
    matches the meeting title or the reference code. A ticket is `missed` when it is not
    Ready and its meeting has started: it leaves to_assign / in_progress for done, which is
    sorted newest first."""
    result = it_ticket.list_tickets(
        session, current, paging.page, paging.size, status, q, state, mine, date_from, date_to
    )
    items = it_ticket.build_ticket_items(result["items"], settings)
    return Page[ITTicketItem](**{**result, "items": items})


@router.get("/summary", response_model=ITSummary, summary="See the IT day in numbers")
def ticket_summary(current: ITLeadUser, session: DbSession) -> ITSummary:
    """IT Lead only. To assign and in progress now (missed left out), made ready today, and
    today's setups (Phnom Penh day) with how many are ready."""
    return ITSummary(**it_ticket.ticket_summary(session, current))


@router.put("/{ticket_id}/staff", response_model=ITTicketItem, summary="Assign IT Staff")
def assign_staff(
    ticket_id: IdPath,
    body: AssignStaffBody,
    current: ITLeadUser,
    session: DbSession,
    settings: AppSettings,
) -> ITTicketItem:
    """T10. IT Lead only. `version` is the booking's. The booking must be in IT setup and the
    ticket not Ready (409 INVALID_TRANSITION). Every user must be active IT Staff (409
    INACTIVE_REFERENCE). The list replaces the earlier one."""
    ticket = it_ticket.assign_staff(
        session, current, ticket_id, body.user_ids, body.technician_notes, body.version
    )
    return it_ticket.build_ticket_items([ticket], settings)[0]


@router.post("/{ticket_id}/ready", response_model=ITTicketItem, summary="Mark the setup ready")
def mark_ready(
    ticket_id: IdPath,
    body: ReadyBody,
    current: ITLeadUser,
    session: DbSession,
    settings: AppSettings,
) -> ITTicketItem:
    """T11. IT Lead only. `version` is the booking's. Needs at least one active assigned IT
    Staff (409 INVALID_TRANSITION). The booking becomes CONFIRMED with a door pass."""
    ticket = it_ticket.mark_ready(session, current, ticket_id, body.version)
    return it_ticket.build_ticket_items([ticket], settings)[0]
