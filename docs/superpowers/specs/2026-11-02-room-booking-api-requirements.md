# Room Booking API: Requirements

Nov 2, 2026 · @MannChealy

## 1. Purpose and scope

This version adds room booking to the existing NBC Meeting Room API: staff book rooms, Pitika and room owners approve, IT prepares the room, and the booker gets a door pass. It is built on the rooms, places, organisation and users that already exist.

The rules come from three sources: the booking ERD (Booking (4).drawio), the clickable mockup (frontend_mockup) and the old full spec (Testing_Claude/docs/REQUIREMENTS.md). The decisions were reviewed with the boss on 2 Nov 2026 (doc "Room Booking: Decisions for Review"). Where this spec and the old spec differ, this spec wins.

**In this version**

- Bookings with 1 to 20 sessions, and a clash check on every session.
- Four booking routes, decided by the system when a booking is sent (section 4).
- Pitika review, room owner review, and expiry.
- Food (catering) and IT support requests, approved with the booking.
- IT tickets: the IT Lead assigns IT Staff and presses Ready.
- Door pass, calendar file (.ics), cancel, and small edits.
- Admin lists for public holidays, catering packages and IT services.

**Not in this version**

- Screens. The booker, Pitika, owner and IT screens get their own spec later.
- Notifications: no bell, no email, no Telegram. People see changes when they open a booking.
- Prices and billing. Rooms, food and IT are free.
- Office closures and room repair dates. Only public holidays, and they only warn.
- A backup approver for room owners.
- Changing the room, date, time, food or IT of a sent booking. The booker cancels and books again.
- Cancelling another person's booking, except by the Admin (changed Nov 4, 2026: see the build spec, B-33 and B-34).
- Reports, charts and an audit log.

## 2. Glossary

| Word | Meaning |
|---|---|
| Booking | One request to use one room. It has a title, attendees and 1 to 20 sessions. |
| Session | One date with a start and end time inside a booking. |
| Booker | The user who sends the booking. Also called the requester. |
| Route | The approval path the system picks when the booking is sent: R1 to R4 (section 4). |
| Shared room | A room that is not private. |
| Private room | A room marked private. It always has a room owner. |
| Room owner | The user set as owner of a room. Reviews bookings in their private rooms. |
| Pitika | A user with the Pitika role. Reviews bookings for rooms in the province of their division. |
| Extras | Food (catering) and IT support asked for in a booking. |
| IT ticket | The IT work for one booking. The IT Lead assigns IT Staff to it. |
| Door pass | A code ("NBC-" and 5 digits) to open the room, shown once the booking is confirmed. |
| Reference code | A short code ("NBC-" and 5 digits) to name a booking on the phone or on paper. It is not the door pass. |
| Blocking | A session that holds its time in the room. Every session blocks unless its booking is rejected or cancelled. |

## 3. Roles and permissions

The six roles already exist. A user can hold several. Every check runs on the server; hiding a button is not enough.

| Role | In booking |
|---|---|
| Staff | Books rooms; sees, edits and cancels their own bookings. |
| Room owner | Reviews bookings in the private rooms they own. Books their own room with no review. |
| Pitika | Reviews bookings for rooms in their province. Sees the food orders there. |
| IT Lead | Sees every IT ticket, assigns IT Staff and presses Ready. |
| IT Staff | Sees the IT tickets they are assigned to. |
| Admin | Sees every booking and keeps the holidays, catering packages and IT services lists. |

"Their province" for a Pitika = the province of the office of their division. "Own rooms" for a room owner = rooms where they are the owner.

| Action | Staff | Room owner | Pitika | IT Lead | IT Staff | Admin |
|---|---|---|---|---|---|---|
| See rooms and their schedule | Yes | Yes | Yes | Yes | Yes | Yes |
| Send a booking; see, edit and cancel own bookings | Yes | Yes | Yes | Yes | Yes | Yes |
| See any booking's details | - | Own rooms | Their province | Bookings with IT | Assigned tickets | All |
| See the title of another person's private-room booking | - | Own rooms | Their province | Bookings with IT | Assigned tickets | All |
| Approve or reject step 1 | - | - | Their province | - | - | - |
| Approve or reject step 2 | - | Own private rooms | - | - | - | - |
| Assign IT Staff, press Ready | - | - | - | Yes | - | - |
| See the door pass | Own, when confirmed | Own rooms | Their province | - | - | All |
| See food orders | - | - | Their province | - | - | All |
| Keep holidays, catering packages, IT services | - | - | - | - | - | Yes |

Every active user may send a booking, whatever their role (D-26). Only the booker cancels; reviewers reject instead (D-27).

## 4. Booking routes and flows

The system picks the route when the booking is sent, from two facts: the room and the booker, and whether food or IT was asked for. The booker never chooses it.

| Route | Booking | Extras | First status | Reviews |
|---|---|---|---|---|
| R1 | Shared room | Any | PENDING_PITIKA | Pitika |
| R2 | Someone else's private room | Any | PENDING_PITIKA | Pitika, then room owner |
| R3 | Owner's own private room | None | CONFIRMED | None |
| R4 | Owner's own private room | Food and/or IT | PENDING_PITIKA | Pitika checks food and IT only |

After the last review: if IT was asked, the booking becomes SETUP_IN_PROGRESS and the IT ticket goes to the IT Lead. Otherwise it becomes CONFIRMED. Food never holds a booking in setup.

**Pitika reviews every booking, except an owner's own room with no extras.**

- **R1 · Shared room:** Pitika (booking and food) → IT setup (only if IT asked) → Confirmed (door pass made)
- **R2 · Someone else's private room:** Pitika (step 1 of 2) → Room owner (step 2 of 2) → IT setup (only if IT asked) → Confirmed (door pass made)
- **R3 · Owner's own private room, no food or IT:** no review needed → Confirmed at once
- **R4 · Owner's own private room, with food or IT:** Pitika (food and IT only) → IT setup (only if IT asked) → Confirmed (door pass made)

At each review step the reviewer can reject, always with a reason. A booking still waiting when its first session starts is rejected by the system. A booking still in IT setup when its first session starts is confirmed by the system. The booker can cancel until the last session ends.

## 5. Statuses and transitions

A booking is always in one of six statuses. Only the moves in the transition table are allowed; any other move is refused with `409 INVALID_TRANSITION`.

| Code | Shown as | Holds its time? | Final? |
|---|---|---|---|
| PENDING_PITIKA | Waiting for Pitika | Yes | No |
| PENDING_OWNER | Waiting for the room owner | Yes | No |
| SETUP_IN_PROGRESS | Setting up | Yes | No |
| CONFIRMED | Confirmed | Yes | No |
| REJECTED | Rejected | No | Yes |
| CANCELLED | Cancelled | No | Yes |

After the door pass ends (end of the last session), a confirmed booking is shown as **Completed**. This is worked out when read, never saved, and a completed booking can no longer be edited or cancelled.

| # | From | Event | Who | Must be true | To | Also happens |
|---|---|---|---|---|---|---|
| T1 | (new) | Send, route R1, R2 or R4 | Booker | Rules in 7.1 to 7.3 pass | PENDING_PITIKA | IT ticket made (not yet forwarded) |
| T2 | (new) | Send, route R3 | Booker = owner | Rules pass, no extras | CONFIRMED | Door pass made; Pitika review saved as NOT_REQUIRED |
| T3 | PENDING_PITIKA | Pitika approves | Pitika | Route R2; first session not started | PENDING_OWNER | Food approved |
| T4 | PENDING_PITIKA | Pitika approves | Pitika | Route R1 or R4; IT asked; first session not started | SETUP_IN_PROGRESS | Food approved; IT ticket forwarded |
| T5 | PENDING_PITIKA | Pitika approves | Pitika | Route R1 or R4; no IT; first session not started | CONFIRMED | Food approved; door pass made |
| T6 | PENDING_PITIKA | Pitika rejects | Pitika | Reason given | REJECTED | Sessions stop blocking |
| T7 | PENDING_OWNER | Owner approves | Room owner | IT asked | SETUP_IN_PROGRESS | IT ticket forwarded |
| T8 | PENDING_OWNER | Owner approves | Room owner | No IT | CONFIRMED | Door pass made |
| T9 | PENDING_OWNER | Owner rejects | Room owner | Reason given | REJECTED | Sessions stop blocking |
| T10 | SETUP_IN_PROGRESS | Assign staff | IT Lead | At least 1 active IT Staff | (same) | Ticket status ASSIGNED |
| T11 | SETUP_IN_PROGRESS | Press Ready | IT Lead | Staff assigned | CONFIRMED | Ticket status READY; door pass made |
| T12 | Any not final | Cancel | Booker | Last session not ended | CANCELLED | Sessions stop blocking; finished sessions stay in history; IT ticket and food dropped |
| T13 | Any not final | Small edit | Booker | First session not started | (same) | Only the small fields change |
| T15 | PENDING_PITIKA or PENDING_OWNER | Expire | System | First session has started | REJECTED | Rejected by SYSTEM: "Expired: not approved before the meeting time." |
| T17 | SETUP_IN_PROGRESS | IT not ready in time | System | First session has started | CONFIRMED | Door pass made; IT ticket stays as it is |

T14 (big edit) is removed: the room, sessions, food and IT cannot be edited (BR-EDT-03). T16 (cancel by Pitika or Admin) is removed: only the booker cancels (BR-CAN-01).

**Two people at once.** Every move checks the `version` number in the same database transaction: `UPDATE bookings SET status = …, version = version + 1 WHERE id = … AND version = …`. If no row changes, the answer is `409 STALE_VERSION` ("This booking changed. Reload it."). Two reviewers can never both succeed.

## 6. Data model

The tables follow the booking ERD. `users` and `rooms` already exist. Rows marked **(added)** were not in Booking (3).drawio; they are confirmed in D-28 and D-29 and added in Booking (4).drawio.

### 6.1 Enums

| Enum | Values |
|---|---|
| BookingStatus | PENDING_PITIKA, PENDING_OWNER, SETUP_IN_PROGRESS, CONFIRMED, REJECTED, CANCELLED |
| MeetingType | INTERNAL, EXTERNAL, INTERNAL_WITH_GOVERNOR, EXTERNAL_WITH_GOVERNOR |
| ReviewStage | PITIKA, OWNER |
| ReviewDecision | APPROVED, REJECTED, NOT_REQUIRED |
| RejectedBy | PITIKA, OWNER, SYSTEM |
| ITStatus | RECEIVED, ASSIGNED, READY |
| BookingRoute | R1, R2, R3, R4 |

### 6.2 bookings

| Field | Type | Notes |
|---|---|---|
| id | int | Auto increment |
| reference_code | text(20), unique | "NBC-" and 5 random digits, retried on a clash |
| requester_id | FK users | The booker |
| room_id | FK rooms | |
| requester_info | JSON | Copy at send time: name_en, name_kh, staff_id, position, division, department, office, email, phone |
| meeting_title | text(200) | Required, 3 to 200 letters |
| meeting_type | MeetingType | Required |
| meeting_purpose | text(1000), optional | Agenda or notes |
| attendees | int | 1 to 100 |
| private_justification | text(1000), optional | Required for route R2 only |
| route | BookingRoute **(added)** | Set at send |
| status | BookingStatus | |
| cancelled_at | datetime, optional | |
| cancel_reason | text(500), optional | The booker's reason, if given |
| version | int, default 1 | Raised on every change (section 5) |
| created_at, updated_at | datetime | |

### 6.3 booking_sessions

| Field | Type | Notes |
|---|---|---|
| id | int | |
| booking_id | FK bookings | 1 to 20 per booking |
| date | date | |
| start_time, end_time | time | Inside the room's opening hours |
| is_blocking | bool | True unless the booking is rejected or cancelled. Index (room, date, is_blocking) for clash checks. |

The booking's shown date and time = its first session (by date, then start time).

### 6.4 Review and access

| Table | Fields | Notes |
|---|---|---|
| booking_reviews | booking_id, stage, decision, reviewer_id, notes(1000), reviewed_at | One row per review. R3 saves one PITIKA row as NOT_REQUIRED. |
| booking_rejections | booking_id (unique), rejected_by, actor_user_id, reason(1000), decided_at | One per rejected booking. actor_user_id is empty for SYSTEM, so it must allow NULL. |
| booking_door_passes | booking_id (unique), passcode, expires_at | Made when the booking becomes CONFIRMED. |
| booking_participants | booking_id, email | Lowercase, unique per booking, at most 50. |

### 6.5 Services

| Table | Fields | Notes |
|---|---|---|
| catering_orders | booking_id (unique), packages JSON, remarks(1000), approver_notes(1000), decided_by, decided_at | packages = copy of [{id, name}] at send time. Servings = attendees; delivery = first session start. decided_by = the Pitika who approved the booking. |
| it_tickets | booking_id (unique), requested_items JSON, special_requirements(1000), status, technician_notes(1000), forwarded_at, assigned_at, ready_at | requested_items = copy of [{id, name}]. forwarded_at is set at final approval; IT sees only forwarded tickets. |
| it_ticket_staff | ticket_id, user_id | Unique pair. The user must be an active IT Staff. |

### 6.6 Catalogs

| Table | Fields | Notes |
|---|---|---|
| catering_packages | name(200), description(1000), sort_order, is_active, version, timestamps | Admin list. Inactive ones cannot be picked for new bookings. |
| it_services | name(200), description(1000), sort_order, is_active, version, timestamps | Admin list, same rules. |
| public_holidays | holiday_date (unique), name_km(255), name_en(255), remarks, timestamps | Admin list. Only gives a warning (7.10). |

## 7. Business rules

Each rule has an ID so code, tests and questions can point at it. The numbers (15 minutes, 20 sessions, 90 days, 100 attendees) are API settings with these defaults, not fixed in code.

### 7.1 Scheduling

| ID | Rule |
|---|---|
| BR-SCH-01 | Every session fits inside the room's own opening and closing time. Message: "This room is open from 08:00 to 17:00." |
| BR-SCH-02 | End is after start, and a session is at least 15 minutes. |
| BR-SCH-03 | No session in the past. Today: the start is at or after the current time (Phnom Penh time). |
| BR-SCH-04 | A session clashes with another in the same room and date when new start < other end AND new end > other start. Back-to-back sessions (one ends 10:00, next starts 10:00) are allowed. |
| BR-SCH-05 | Only blocking sessions count: every booking that is not rejected or cancelled, including waiting ones. |
| BR-SCH-06 | Sessions inside one booking must not overlap each other. |
| BR-SCH-07 | All sessions are checked together. If one fails, nothing is saved, and the error names that session. |
| BR-SCH-08 | Clash, past-time and holiday checks run on the server when the booking is saved, in one transaction that locks the room row (`SELECT … FOR UPDATE`). |
| BR-SCH-09 | Only bookable rooms: the room, its floor, building and office are all active. |
| BR-SCH-10 | At most 20 sessions per booking, and no session more than 90 days ahead. |
| BR-SCH-11 | Weekends are allowed. |
| BR-SCH-12 | A session on a public holiday is allowed, with a warning (7.10). |
| BR-SCH-13 | Routes R1, R2 and R4 are refused when the room's province has no active Pitika: "No reviewer for this office yet." R3 needs no Pitika and is allowed. |

### 7.2 Privacy

| ID | Rule |
|---|---|
| BR-PRV-01 | In a room's schedule, a booking in a private room is shown as "Reserved (Private Session)" to users who may not see it (section 3). Title, booker and purpose are hidden. |
| BR-PRV-02 | Clash messages follow the same rule: "This room is already booked from 08:30 to 10:00 for Reserved (Private Session)." |
| BR-PRV-03 | The door pass is never sent before the booking is confirmed, and only to the users in section 3. |

### 7.3 Booking form

| ID | Rule |
|---|---|
| BR-FRM-01 | At least one session. |
| BR-FRM-02 | Meeting title (3 to 200 letters) and meeting type are required. |
| BR-FRM-03 | Attendees: a whole number from 1 to 100, and at least the number of participants plus 1 (the booker). |
| BR-FRM-04 | More attendees than room seats is allowed, with a warning: "This room has 12 seats. You entered 20 attendees." |
| BR-FRM-05 | Participant emails: valid, saved lowercase, no repeats, at most 50. |
| BR-FRM-06 | requester_info is copied from the booker's profile when the booking is sent, so later profile changes do not change old bookings. |
| BR-FRM-07 | Route R2 (another person's private room) needs a private justification. |
| BR-FRM-08 | Food: at least one active catering package, plus optional remarks (for example "2 vegetarian, no pork"). IT: at least one active IT service, plus optional special requirements. |

### 7.4 Pitika review

| ID | Rule |
|---|---|
| BR-APR-01 | A Pitika acts only on PENDING_PITIKA bookings for rooms in their province. Several Pitika share that queue; the first to act decides. |
| BR-APR-02 | Rejecting always needs a reason. |
| BR-APR-03 | A booking whose first session has started cannot be approved; it can still be rejected. Expiry (T15) rejects it anyway. |
| BR-APR-04 | A Pitika can never skip the room owner on route R2: approving moves it to PENDING_OWNER. |
| BR-APR-05 | On route R4 (owner's own room with extras), the Pitika checks only the food and IT. |
| BR-APR-06 | One Pitika approval also approves the food: catering_orders.decided_by and decided_at are set at the same moment. |
| BR-APR-07 | Optional approval notes are kept and shown to the next step (owner, IT Lead) and as kitchen notes on the food order. |

### 7.5 Room owner review

| ID | Rule |
|---|---|
| BR-OWN-01 | The owner acts only on PENDING_OWNER bookings in their own private rooms. They approve or reject the whole booking and cannot change its times. |
| BR-OWN-04 | There is no backup approver. If the owner does not act, the booking expires (T15). |
| BR-OWN-05 | Waiting bookings follow the room: when the Admin sets a new owner, the new owner sees them at once. |

### 7.6 IT support

| ID | Rule |
|---|---|
| BR-IT-01 | The IT ticket is made when the booking is sent, but IT sees it only after the final approval (forwarded_at is set) and while the booking is not rejected or cancelled. |
| BR-IT-02 | The IT Lead assigns one or more active IT Staff and can change them later. |
| BR-IT-03 | Only the IT Lead presses Ready, and only after staff are assigned. This confirms the booking (T11). |
| BR-IT-04 | IT Staff see the tickets they are assigned to; they cannot change them. |
| BR-IT-05 | Setup is planned 30 minutes before the first session (shown as information). |
| BR-IT-06 | If IT has not pressed Ready when the first session starts, the system confirms the booking anyway (T17). The meeting can happen without IT. |

### 7.7 Door pass

| ID | Rule |
|---|---|
| BR-DP-01 | Format "NBC-" and 5 digits (10000 to 99999), from a secure random source, unique among active door passes, and never equal to the reference code. |
| BR-DP-02 | Made when the booking becomes CONFIRMED. It ends at the end of the last session. |
| BR-DP-03 | After it ends, the API still returns it with `"expired": true`. |
| BR-DP-05 | It is not linked to a real door lock, and it is not emailed in this version. |

### 7.8 Cancel

| ID | Rule |
|---|---|
| BR-CAN-01 | Only the booker can cancel. They can cancel any booking that is not final, until the last session ends. Finished sessions stay in history; later sessions are freed. A Pitika or room owner who does not want a booking rejects it instead. |
| BR-CAN-03 | Cancelling frees the time at once and drops the food order and IT ticket. |

### 7.9 Edit

| ID | Rule |
|---|---|
| BR-EDT-01 | Only the booker edits, only while the booking is not final, and only before the first session starts. |
| BR-EDT-02 | **Small fields** keep the approval: title, meeting type, purpose, attendees, participants, food remarks, IT special requirements. |
| BR-EDT-03 | Room, sessions, food and IT can't be edited. Cancel and book again. |

### 7.10 Public holidays

| ID | Rule |
|---|---|
| BR-HOL-01 | The Admin keeps the list: one row per date, Khmer name required, English name optional. |
| BR-HOL-02 | Booking on a holiday is allowed. The check and the save answers carry a warning: `{"code": "PUBLIC_HOLIDAY", "date": "2026-11-09", "name": "Independence Day"}`. |
| BR-HOL-03 | Adding a holiday changes no existing booking. |

### 7.11 Field limits

| Field | Limit |
|---|---|
| Meeting title | 3 to 200 letters |
| Purpose, justification, notes, remarks, requirements | At most 1000 letters |
| Reject reason | 5 to 1000 letters |
| Cancel reason | Optional; 5 to 500 letters when given |
| Participant emails | At most 50 per booking |
| Catering package and IT service names | 2 to 200 letters |

Text is trimmed before checks. HTML is never accepted; text is saved as plain text.

## 8. API endpoints

Same style as the current API: base path `/api/v1`, JSON in snake_case, sign-in with the existing access token, lists with `page` (default 1) and `size` (default 20, at most 100) that answer `{"items": […], "page": 1, "size": 20, "total": 240}`. Every request that changes a booking sends its `version`.

### 8.1 Booker

| Method | Path | What it does |
|---|---|---|
| GET | /rooms/{id}/schedule?from=&to= | Blocking sessions of one room between two dates, private ones masked (BR-PRV-01). At most 31 days. |
| POST | /bookings/check | Body: room_id, sessions, has_catering, has_it. Answers the route (R1 to R4), the steps the booking will go through, the first problem found, and any warnings. Saves nothing. |
| POST | /bookings | Sends a booking (T1 or T2). Answers 201 with the full booking, its route, status and warnings. |
| GET | /bookings/mine?status=&q= | The booker's own bookings, newest first. |
| GET | /bookings/{id} | One booking, for the users allowed in section 3. |
| PATCH | /bookings/{id} | Small edit (T13). Body: the small fields (meeting_title, meeting_type, meeting_purpose, attendees, participant_emails, catering.remarks, it.special_requirements) plus version. Sending room_id, sessions, catering.package_ids or it.service_ids is refused with 422 FIELD_NOT_EDITABLE. Answers the full booking. |
| POST | /bookings/{id}/cancel | Booker only. Body: reason (optional), version. T12. |
| GET | /bookings/{id}/door-pass | The door pass, its end time and "expired". Only when CONFIRMED. |
| GET | /bookings/{id}/ics | A calendar file with every session. |

**POST /bookings body**

```json
{
  "room_id": 4,
  "sessions": [
    {"date": "2026-11-10", "start_time": "09:00", "end_time": "10:30"},
    {"date": "2026-11-11", "start_time": "14:00", "end_time": "15:00"}
  ],
  "meeting_title": "Q4 budget review",
  "meeting_type": "INTERNAL",
  "meeting_purpose": "Check the budget plan for 2027",
  "attendees": 12,
  "participant_emails": ["sok.dara@nbc.gov.kh"],
  "private_justification": null,
  "catering": {"package_ids": [1, 2], "remarks": "2 vegetarian"},
  "it": {"service_ids": [1], "special_requirements": "Need a Mac HDMI adapter"}
}
```

`catering` and `it` are `null` when not asked for. The server picks the route; the body never sends it.

### 8.2 Pitika

| Method | Path | What it does |
|---|---|---|
| GET | /pitika/bookings?status=&from=&to=&room_id=&q= | Bookings for rooms in the Pitika's province. from and to match any session date. |
| POST | /pitika/bookings/{id}/approve | Body: notes, version. The server picks T3, T4 or T5 from the route. |
| POST | /pitika/bookings/{id}/reject | Body: reason, version. T6. |
| GET | /pitika/catering?date= | Food orders of approved bookings on one day: packages, servings, room, delivery time, remarks. |

### 8.3 Room owner

| Method | Path | What it does |
|---|---|---|
| GET | /owner/bookings?status=&room_id=&q= | Bookings in the owner's private rooms. |
| POST | /owner/bookings/{id}/approve | Body: notes, version. T7 or T8. |
| POST | /owner/bookings/{id}/reject | Body: reason, version. T9. |

### 8.4 IT

| Method | Path | What it does |
|---|---|---|
| GET | /it/tickets?status=&q= | IT Lead: every forwarded ticket. IT Staff: only tickets they are assigned to. |
| PUT | /it/tickets/{id}/staff | IT Lead. Body: user_ids, technician_notes, version. T10. |
| POST | /it/tickets/{id}/ready | IT Lead. Body: version. T11. |

### 8.5 Catalogs and holidays

Every signed-in user can read these lists (the booking form needs them). Only the Admin changes them.

| Method | Path | What it does |
|---|---|---|
| GET, POST | /catering-packages | List; add one |
| PATCH | /catering-packages/{id} | Edit, make active or inactive |
| GET, POST | /it-services | List; add one |
| PATCH | /it-services/{id} | Edit, make active or inactive |
| GET, POST | /public-holidays?year= | List; add one |
| PATCH, DELETE | /public-holidays/{id} | Edit; delete (no booking points at a holiday) |

### 8.6 Expiry job

A job runs every minute. It rejects (T15) every PENDING_PITIKA or PENDING_OWNER booking whose first session has started, and confirms (T17) every SETUP_IN_PROGRESS booking whose first session has started. It runs in one process only.

## 9. Errors

Errors keep the current shape: `{"error": {"code": "SCHEDULE_CONFLICT", "message": "…", "fields": {…}}}`. The existing codes stay (VALIDATION_ERROR 422, FORBIDDEN 403, NOT_FOUND 404, INACTIVE_REFERENCE and others). Booking adds these:

| Code | HTTP | When | Example message |
|---|---|---|---|
| SCHEDULE_CONFLICT | 409 | A session clashes with another booking | "This room is already booked from 08:30 to 10:00 for Reserved (Private Session)." |
| TIME_PASSED | 409 | A session is in the past, or a review comes after the first session started | "This session starts at 09:00, which has passed." |
| OUTSIDE_ROOM_HOURS | 422 | A session is outside the room's opening hours | "This room is open from 08:00 to 17:00." |
| ROOM_NOT_BOOKABLE | 409 | The room, its floor, building or office is inactive | "This room cannot be booked right now." |
| NO_REVIEWER | 409 | The room's province has no active Pitika (BR-SCH-13) | "No reviewer for this office yet." |
| INVALID_TRANSITION | 409 | A move not in the transition table | "This booking is already confirmed." |
| STALE_VERSION | 409 | Someone changed the booking first | "This booking changed. Reload it." |
| FIELD_NOT_EDITABLE | 422 | An edit tries to change the room, sessions, food or IT (BR-EDT-03) | "To change the room, date or time, cancel and book again." |
| OWNER_REQUIRED | 422 | A private room is saved with no owner (section 10) | "A private room needs an owner." |
| OWNER_HAS_PRIVATE_ROOMS | 409 | Making a room owner inactive, or removing the role, while they own a private room | "Assign a new owner for 2 private rooms first." |
| HAS_FUTURE_BOOKINGS | 409 | Making a room, floor, building or office inactive while it has future bookings (section 10) | "This room has 3 future bookings. Ask the bookers to cancel first." |

Limits on sessions, attendees, emails and text lengths use VALIDATION_ERROR with `fields`, for example `{"sessions.2.end_time": "A session is at least 15 minutes."}`.

Warnings are not errors. The check and save answers carry a list such as `"warnings": [{"code": "PUBLIC_HOLIDAY", …}, {"code": "OVER_CAPACITY", "seats": 12, "attendees": 20}]`.

## 10. Changes to the current API

These rules change things that are already built and used by the admin dashboard. The dashboard must show the new messages.

| Where | Today | After |
|---|---|---|
| Create or edit a room | A private room can have no owner. | Refused with OWNER_REQUIRED. |
| Make a user inactive, or remove their Room owner role | Their rooms lose their owner. | Refused with OWNER_HAS_PRIVATE_ROOMS while they own a private room. Shared rooms still lose their owner, as today. |
| Change a room's owner | Only the room changes. | Waiting bookings follow the room: the new owner sees them (BR-OWN-05). |
| Change a private room to shared | Allowed. | Refused while the room has PENDING_OWNER bookings: "Resolve 3 bookings waiting for the room owner first." |
| Lower a room's seats | Allowed. | Still allowed; existing bookings are not changed. |
| Change a room's opening hours | Allowed. | Still allowed; existing bookings are not checked again. |
| Make a room, floor, building or office inactive | Allowed; it stops being bookable. | Refused while the room (or any room inside it) has future bookings, with HAS_FUTURE_BOOKINGS. The Admin asks the bookers to cancel, or waits until the meetings are over. |

## 11. Decisions log

Every place where the sources disagreed or said nothing has one decision here. "Boss review" = decided in the review of 2 Nov 2026. "Writer's call" = chosen while writing this spec; change it with a comment. "Spec review" = decided while reviewing this spec on 2 Nov 2026.

| ID | Topic | Decision | Source | Where |
|---|---|---|---|---|
| D-01 | Catering approval | One Pitika approval approves the booking and its food | Boss review | BR-APR-06 |
| D-02 | IT roles | IT Lead assigns IT Staff and presses Ready | Boss review (changed) | BR-IT-02, BR-IT-03 |
| D-03 | Booking hours | Each room's own opening hours | Boss review | BR-SCH-01 |
| D-04 | Holidays | Public holidays only; allowed with a warning | Boss review | 7.10 |
| D-05 | Owner step | A private room must have an owner, who reviews after Pitika | Boss review | Route R2, section 10 |
| D-06 | Backup approver | None; the booking expires | Boss review | BR-OWN-04 |
| D-07 | Pitika queue | One queue per province | Boss review (changed) | BR-APR-01 |
| D-08 | No Pitika in a province | New bookings needing Pitika are refused | Boss review | BR-SCH-13 |
| D-09 | Meeting type | 4 values, label only | Boss review (note) | 6.1 |
| D-10 | Notifications | None in this version | Boss review | Section 1 |
| D-11 | Scope | Booking API only | Boss review | Section 1 |
| D-12 | Owner leaves | Refused while owning a private room | Boss review | Section 10 |
| D-13 | Routes, statuses, transitions | As the old spec, "Manager" renamed Pitika | Old spec | Sections 4, 5 |
| D-14 | Time limits | 15 minutes, 20 sessions, 90 days, weekends allowed | Old spec | 7.1 |
| D-15 | Edit and cancel | Small edits only; room, sessions, food and IT need cancel and book again; one cancel cut-off for the booker (end of the last session) | Old spec (changed) | 7.8, 7.9 |
| D-16 | Expiry | System rejects at first session start | Old spec | T15 |
| D-17 | Door pass | Made at confirm, not emailed, not linked to a lock | Old spec, changed by D-10 | 7.7 |
| D-18 | Pending bookings block | Waiting bookings hold their time | Old spec and mockup | BR-SCH-05 |
| D-19 | Food after approval | Food never holds a booking in setup; only IT does | Old spec | T4, T5 |
| D-21 | Private justification | Required for route R2 only | Writer's call | BR-FRM-07 |
| D-22 | Food list | Pitika sees the day's food orders for their province and prepares the food. No kitchen role in this version. | Spec review | 8.2 |
| D-23 | Session grid | The API takes any minute; a 30-minute grid is for screens | Writer's call | 7.1 |
| D-24 | Owner times | The owner approves or rejects the whole booking and cannot shorten times | Spec review | BR-OWN-01 |
| D-25 | Inactive place with bookings | Refused until the bookers cancel or the meetings are over | Spec review | Section 10 |
| D-26 | Who can book | Every active user, whatever their role | Spec review | Section 3 |
| D-27 | Who can cancel | Only the booker; Pitika and room owner reject instead | Spec review | BR-CAN-01 |
| D-28 | Saved route | bookings.route is saved at send, so a later owner change does not change the route of old bookings | Spec review | 6.2 |
| D-29 | System rejection | booking_rejections.actor_user_id allows NULL; expiry is rejected by SYSTEM with no user | Spec review | 6.4, T15 |
| D-30 | Cancel a long booking | The booker can cancel until the last session ends, so a stopped series frees its later sessions | Spec review | BR-CAN-01, T12 |
| D-31 | IT not ready in time | At first session start the system confirms the booking anyway | Spec review | BR-IT-06, T17 |

## 12. Tests and open questions

### 12.1 Tests that must pass

Each item is at least one API test (pytest).

- [ ] Each route R1 to R4 from send to CONFIRMED, with and without IT.
- [ ] Each transition T1 to T17 (T14 and T16 are removed), and one move that is not allowed (INVALID_TRANSITION).
- [ ] Clash: overlap refused, back-to-back allowed, a rejected or cancelled booking does not block, a waiting one does.
- [ ] Two sessions in one booking that overlap are refused; one bad session saves nothing.
- [ ] Room hours, 15-minute minimum, past time, 20 sessions, 90 days.
- [ ] Two Pitika approve the same booking at once: one wins, one gets STALE_VERSION.
- [ ] A Pitika cannot see or act on a room in another province; NO_REVIEWER when a province has no Pitika; R3 still works.
- [ ] Expiry job rejects a waiting booking after its first session starts, and confirms a booking still in IT setup (with a door pass).
- [ ] Door pass: hidden before confirm, shown after, "expired" after the last session.
- [ ] Private booking shown as "Reserved (Private Session)" to others, in the schedule and in clash messages.
- [ ] Small edit keeps the status; changing the room, sessions, food or IT is refused with FIELD_NOT_EDITABLE.
- [ ] The booker can cancel until the last session ends; finished sessions stay in history; a Pitika, room owner or Admin cannot cancel (FORBIDDEN).
- [ ] Holiday and over-capacity warnings.
- [ ] Section 10: private room without owner refused; owner leaving refused; waiting bookings follow a new owner; making a room inactive with future bookings refused.

### 12.2 Open questions

None. All questions are answered in the decisions log (D-22, D-25 to D-31).
