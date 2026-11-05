# Pitika in the admin dashboard: design

Owner decisions, 5 Nov 2026, from a click-through demo the owner iterated on.

## Where

- Pitika, Room owner and IT work in the admin dashboard; each role sees only its own menu. Staff (booking a room) gets a separate app later. This spec covers Pitika only.
- A user with none of the dashboard roles (Admin, Pitika) still sees "No access".
- A user with both Admin and Pitika sees both menus; the Admin pages keep working as today.

## Pitika menu

Daily: **To review** (with a crimson count of bookings waiting), **Bookings** (every booking in the Pitika's province, the same list as the Admin's but from `GET /pitika/bookings`, read only), **Food list** (`GET /pitika/catering`, already province-scoped). My profile stays in the rail foot. No setup groups.

## To review

- Bookings waiting for this Pitika: `GET /pitika/bookings?status=PENDING_PITIKA`, earliest first start first. Search (`q`) and a room filter (`room_id`) in the filter row. No "Decided by me" (the API cannot filter by reviewer).
- One sheet, grouped by urgency with sticky heads: **Today** (crimson, "Decide before they start, or they expire"), **Tomorrow**, **This week**, **Later**. A group with no bookings is not shown. Days are Phnom Penh days.
- A row: the room's cover photo (168px wide, 16:10, rounded 8px; a paper tile with a door icon when the room has no photo), the mono reference ("NBC" crimson), the title, Khmer · English room name, the first session's day and times (+n more), the booker, the attendees. Under it, "what to check" labels: food package names × servings, the IT items, a crimson "Private · reason given" (or "Private · no reason") on route R2, "Food and IT only" on route R4. On the right: for Today only, a crimson "Starts in 4 h 40 min" pill (or "Started" once it has); the row bar; Reject (danger) and Approve (primary).
- **Row bar ("gap is you")**: Sent done, then a dashed amber line with no Pitika circle (the decision waiting), then the steps after Pitika: Room owner on R2, IT setup when IT help was asked (not on R3), then Confirmed.
- Clicking a row opens the side panel. A decision removes the row (it leaves the queue) and shows a toast; the count updates.
- Empty: "Nothing to review" / "New bookings in your province show here."

## The side panel

- A 188px room photo header (the cover photo; paper with a door icon when none) with the Khmer name over "English · office · building · floor" on a dark gradient, and the close button on it.
- Head: the title, "Waiting for Pitika · NBC-26-…".
- The full process bar of the booking (the History tab's bar, Pitika as the current step).
- Notes on amber wash: today's bookings "Starts in … If nobody decides before it starts, it is rejected by the system."; route R4 "The owner books their own room: you check the food and IT only."
- Meeting (when, type, attendees, purpose, route, why private, booker with division), Food (packages, servings, delivery, remarks), IT help (items, special needs).
- Foot: Close at the start; Reject and Approve at the end.

## Approve and reject

- Both open the Ledger confirm pop-up (BookingActionDialog).
- Approve: "Approve this booking?", what happens next ("It goes to the room owner next." / "It goes to IT setup next." / "It is confirmed, with a door pass."; plus " The food is approved with it." when food was ordered), "Notes (optional)" up to 1000 characters, sent as `notes`.
- Reject: "Reject this booking?", "The booking stops and the room is free again. The booker sees your reason.", "Reason" required, 5 to 1000 characters (the API's rule): the Reject button stays off until 5 characters are typed, with the hint "At least 5 characters.".
- A refusal (409 already decided, TIME_PASSED, stale version) shows in the pop-up; the queue reloads.
