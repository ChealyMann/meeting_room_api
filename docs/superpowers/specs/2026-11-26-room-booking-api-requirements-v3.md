# Room Booking API: Requirements (v3, merged)

Nov 26, 2026 · @MannChealy

This is the current requirements file. It joins the requirements of Nov 2 (edited Nov 6) with every later owner decision, the build-spec calls (B-xx) and the design notes up to Nov 20. Rule IDs (BR-…, T…, D-…, B-…) keep their old numbers, so tests and code still point to the right rule. Where this file and an older one differ, **this file wins**.

## 0. What changed since v2

| Date | Change | Where |
|---|---|---|
| Nov 3 | Reference code is `NBC-YY-NNNNN`. A person may have any number of waiting bookings. A Pitika may approve their own booking. Booker turned off → their open bookings are cancelled. | 2, 6.2, 7.8, B-20, B-27 to B-29 |
| Nov 4 | The Admin lists every booking, cancels any open booking, and approves or rejects as a backup reviewer. The booking records who cancelled and who decided. | 3, 5, 8.9, D-32 to D-40 |
| Nov 5 | Pitika, room owner and IT get their own pages: To review, decided lists, daily numbers, IT states, missed setups. | 8.2 to 8.4, 13 |
| Nov 6 | Food is served at every session. IT sets up before every session. IT staff can be assigned or changed on a confirmed booking while later sessions remain. | BR-IT-02, BR-IT-05, 6.5 |
| Nov 12 | Staff book in the dashboard. Meeting type has the "Governor attends" switch. Catering packages and IT services get a group and an icon. One call gives every room's busy times for a day. Public holidays stay a warning. | 8.1, 6.6, 13 |
| Nov 13 | Request slip (ប័ណ្ណស្នើ): a Word file made from a confirmed booking, signed by the heads at confirm. Find a room can filter by free time. | 8.8, 8.10 |
| Nov 16 | Files on a booking (PDF, Word, Excel). | 7.12, 8.7 |
| Nov 17 | **No numbers for food** anywhere. Pitika sees every decision in the province. IT lead works in their own province. Room availability page for Pitika and Admin. | BR-IT-07, 8.2, 13 |
| Nov 19 | **IT setup is an add-on.** The last approval confirms the booking at once, with its door pass. IT works beside it and cannot hold the booking. The booker's phone and email are the current ones. | 4, 5, 7.6 |

## 1. Purpose and scope

This version adds room booking to the existing NBC Meeting Room API: staff book rooms, Pitika and room owners approve, IT prepares the room, and the booker gets a door pass. It is built on the rooms, places, organisation and users that already exist.

The rules come from the booking ERD, the clickable mockup and the old full spec. The decisions were reviewed with the boss on 2 Nov 2026 and by the owner on the dates in section 0. Where this file and the old spec differ, this file wins.

**In this version**

- Bookings with 1 to 20 sessions, and a clash check on every session.
- Four booking routes, decided by the system when a booking is sent (section 4).
- Pitika review, room owner review, and expiry.
- Food (catering) and IT support requests, approved with the booking.
- IT tickets: the IT Lead assigns IT Staff and presses Ready. IT runs beside a confirmed booking.
- Door pass, calendar file (.ics), cancel, and small edits.
- Files on a booking (documents only).
- The request slip (Word file) made from a confirmed booking.
- Admin: lists for public holidays, catering packages and IT services; every booking; cancel; backup review.
- Screens in the admin dashboard for Staff, Pitika, room owner, IT and Admin (section 13).

**Not in this version**

- Notifications: no bell, no email, no Telegram. People see changes when they open a booking.
- Prices and billing. Rooms, food and IT are free.
- Office closures and room repair dates. Only public holidays, and they only warn.
- A backup approver for room owners.
- Changing the room, date, time, food or IT of a sent booking. The booker cancels and books again.
- Cancelling another person's booking, except by the Admin (B-33).
- A way for IT to refuse a setup. IT never could.
- Food numbers: servings, "× N" and food totals (BR-IT-07).
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
| IT setup | The work on the ticket. It runs beside a confirmed booking. States: sent to IT, assigned, ready, or **missed** (not marked ready before the first session started). |
| Door pass | A code ("NBC-" and 5 digits) to open the room, shown once the booking is confirmed. |
| Reference code | A code to name a booking on the phone or on paper: `NBC-YY-NNNNN`, for example `NBC-26-48213` (B-28). It is not the door pass. |
| Blocking | A session that holds its time in the room. Every session blocks unless its booking is rejected or cancelled. |
| Attachment | A document (PDF, Word, Excel) added to a booking by the booker. |
| Request slip | The Khmer ប័ណ្ណស្នើ Word file made from a confirmed booking (8.8). |
| Backup reviewer | The Admin, when they approve or reject in place of a missing Pitika or a room owner (B-34). |

## 3. Roles and permissions

The six roles already exist. A user can hold several. Every check runs on the server; hiding a button is not enough. A user who may not see a booking gets `404`, not `403` (B-08). A user who may see it but may not do the action gets `403`.

| Role | In booking |
|---|---|
| Staff | Books rooms; sees, edits and cancels their own bookings. A Staff-only user lands on Find a room. |
| Room owner | Reviews bookings in the private rooms they own. Books their own room with no review. |
| Pitika | Reviews bookings for rooms in their province. Sees the food orders there. Sees every Pitika-stage decision in the province, and who made it. |
| IT Lead | Sees every IT ticket in their own province, assigns IT Staff of that province and presses Ready. |
| IT Staff | Sees the IT tickets they are assigned to. |
| Admin | Sees every booking, cancels any open booking, reviews as a backup, and keeps the holidays, catering packages, IT services and request slip settings. |

"Their province" for a Pitika or IT Lead = the province of the office of their division or office. An IT Lead with no office sees no tickets. "Own rooms" for a room owner = rooms where they are the owner.

| Action | Staff | Room owner | Pitika | IT Lead | IT Staff | Admin |
|---|---|---|---|---|---|---|
| See rooms and their schedule | Yes | Yes | Yes | Yes | Yes | Yes |
| Send a booking; see, edit and cancel own bookings | Yes | Yes | Yes | Yes | Yes | Yes |
| See any booking's details | - | Own rooms | Their province | Their province, bookings with IT, once forwarded | Assigned tickets | All |
| See the title of another person's private-room booking | - | Own rooms | Their province | Bookings with IT | Assigned tickets | All |
| Approve or reject step 1 | - | - | Their province | - | - | Backup (B-34) |
| Approve or reject step 2 | - | Own private rooms | - | - | - | Backup (B-34) |
| Cancel a booking that is not final | Own | - | - | - | - | Any (B-33) |
| Assign IT Staff, press Ready | - | - | - | Their province | - | - |
| See the door pass | Own, when confirmed | Own rooms | Their province | - | - | All |
| Download the request slip | Own, when confirmed | - | Their province | - | - | All |
| See and open files on a booking | Own | Own rooms | Their province | Bookings with IT | Assigned tickets | All |
| Add or remove files | Own booking, until confirmed | - | - | - | - | - |
| See food orders | - | - | Their province | - | - | All |
| Keep holidays, catering packages, IT services, slip settings | - | - | - | - | - | Yes |

Every active user may send a booking, whatever their role (D-26). Pitika and room owner do not cancel; they reject instead (D-27). A Pitika may approve or reject their own booking (B-20).

## 4. Booking routes and flows

The system picks the route when the booking is sent, from two facts: the room and the booker, and whether food or IT was asked for. The booker never chooses it.

| Route | Booking | Extras | First status | Reviews |
|---|---|---|---|---|
| R1 | Shared room | Any | PENDING_PITIKA | Pitika |
| R2 | Someone else's private room | Any | PENDING_PITIKA | Pitika, then room owner |
| R3 | Owner's own private room | None | CONFIRMED | None |
| R4 | Owner's own private room | Food and/or IT | PENDING_PITIKA | Pitika checks food and IT only |

**The last review confirms the booking at once** (owner decision, 19 Nov 2026). The booking becomes CONFIRMED, the door pass is made, and the request slip signers are saved. If IT was asked, the IT ticket goes to the IT Lead at the same moment. IT then works beside the booking and can never hold it. Food never holds a booking either.

**Pitika reviews every booking, except an owner's own room with no extras.**

- **R1 · Shared room:** Pitika (booking and food) → Confirmed (door pass made) · IT setup beside it (only if IT asked)
- **R2 · Someone else's private room:** Pitika (step 1 of 2) → Room owner (step 2 of 2) → Confirmed (door pass made) · IT setup beside it (only if IT asked)
- **R3 · Owner's own private room, no food or IT:** no review needed → Confirmed at once
- **R4 · Owner's own private room, with food or IT:** Pitika (food and IT only) → Confirmed (door pass made) · IT setup beside it (only if IT asked)

At each review step the reviewer can reject, always with a reason. A booking still waiting when its first session starts is rejected by the system. The booker can cancel until the last session ends.

**What the booker sees.** The bar reads `Sent · Pitika (· Room owner) · Confirmed · IT setup`. The IT step is the fourth step after Confirmed. It is amber while IT works (Sent to IT, Setting up), green when the room is ready, and **crimson only when IT missed it**. The IT step must never look like it blocks the booking, and the booker never loses a door pass or a confirmed status because of IT.

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

`SETUP_IN_PROGRESS` stays in the list only for old rows. **Nothing new enters it** (19 Nov 2026). A one-off script, `python -m scripts.confirm_it_setup_bookings`, confirms the old rows. It only touches `SETUP_IN_PROGRESS` rows, so it is safe to run twice. Run it once after the add-on goes live.

After the door pass ends (end of the last session), a confirmed booking is shown as **Completed**. This is worked out when read, never saved, and a completed booking can no longer be edited or cancelled. List filters by status use the shown status, so `CONFIRMED` means "confirmed, not yet completed" (B-10).

| # | From | Event | Who | Must be true | To | Also happens |
|---|---|---|---|---|---|---|
| T1 | (new) | Send, route R1, R2 or R4 | Booker | Rules in 7.1 to 7.3 pass | PENDING_PITIKA | IT ticket made (not yet forwarded) |
| T2 | (new) | Send, route R3 | Booker = owner | Rules pass, no extras | CONFIRMED | Door pass made; confirm time and slip signers saved; Pitika review saved as NOT_REQUIRED |
| T3 | PENDING_PITIKA | Pitika approves | Pitika | Route R2; first session not started | PENDING_OWNER | Food approved |
| T4 | PENDING_PITIKA | Pitika approves | Pitika | Route R1 or R4; IT asked; first session not started | CONFIRMED | Food approved; door pass made; IT ticket forwarded; slip signers saved |
| T5 | PENDING_PITIKA | Pitika approves | Pitika | Route R1 or R4; no IT; first session not started | CONFIRMED | Food approved; door pass made; slip signers saved |
| T6 | PENDING_PITIKA | Pitika rejects | Pitika | Reason given | REJECTED | Sessions stop blocking |
| T7 | PENDING_OWNER | Owner approves | Room owner | IT asked; first session not started | CONFIRMED | Door pass made; IT ticket forwarded; slip signers saved |
| T8 | PENDING_OWNER | Owner approves | Room owner | No IT; first session not started | CONFIRMED | Door pass made; slip signers saved |
| T9 | PENDING_OWNER | Owner rejects | Room owner | Reason given | REJECTED | Sessions stop blocking |
| T10 | CONFIRMED | Assign staff | IT Lead | At least 1 active IT Staff of the same province; setup not Ready and first session not started, or later sessions remain | (same) | Ticket status ASSIGNED; booking version moves on |
| T11 | CONFIRMED | Press Ready | IT Lead | Staff assigned and active; first session not started | (same) | Ticket status READY, `ready_at` set; booking version moves on. The booking status and door pass do not change. |
| T12 | Any not final | Cancel | Booker, or Admin (B-33) | Last session not ended | CANCELLED | Sessions stop blocking; finished sessions stay in history; IT ticket and food dropped; who cancelled is saved (B-35) |
| T13 | Any not final | Small edit | Booker | First session not started | (same) | Only the small fields change |
| T15 | PENDING_PITIKA or PENDING_OWNER | Expire | System | First session has started | REJECTED | Rejected by SYSTEM: "Expired: not approved before the meeting time." |
| T17 | SETUP_IN_PROGRESS (old rows only) | IT not ready in time | System | First session has started | CONFIRMED | Door pass made; IT ticket stays as it is |

**Old rows.** A booking already in `SETUP_IN_PROGRESS` keeps the old way: Press Ready confirms it (door pass made), and the expiry job confirms it at the first session start (T17).

**Admin as backup (B-34).** The Admin may do T3 to T9 for a booking, with `by_admin` saved on the review or rejection, but only: for PENDING_PITIKA when the room's province has no active Pitika (else `403`, "This office has an active Pitika. Ask them to decide."), and for any PENDING_OWNER booking. The time rules are the same as for everyone. The Admin has no IT steps. A reject with no reason saves "Rejected by the Admin."

**Booker turned off (B-27).** When the Admin turns a user off, every booking of theirs that is not final and not ended becomes CANCELLED in the same transaction. The cancel reason is "Cancelled: the booker's account was turned off." Sessions stop blocking. `cancelled_by` is empty.

T14 (big edit) is removed: the room, sessions, food and IT cannot be edited (BR-EDT-03). T16 (cancel by Pitika) is removed: Pitika and room owner reject instead (BR-CAN-01).

**Two people at once.** Every move checks the `version` number in the same database transaction: `UPDATE bookings SET status = …, version = version + 1 WHERE id = … AND version = …`. Every write reads the booking row `FOR UPDATE` first (B-31). If no row changes, the answer is `409 STALE_VERSION` ("This booking changed. Reload it."). Two reviewers can never both succeed. Adding or removing a file does not change the version (7.12).

## 6. Data model

The tables follow the booking ERD. `users` and `rooms` already exist. Rows marked **(added)** were not in the first ERD.

### 6.1 Enums

| Enum | Values |
|---|---|
| BookingStatus | PENDING_PITIKA, PENDING_OWNER, SETUP_IN_PROGRESS (old rows only), CONFIRMED, REJECTED, CANCELLED |
| MeetingType | INTERNAL, EXTERNAL, INTERNAL_WITH_GOVERNOR, EXTERNAL_WITH_GOVERNOR |
| ReviewStage | PITIKA, OWNER |
| ReviewDecision | APPROVED, REJECTED, NOT_REQUIRED |
| RejectedBy | PITIKA, OWNER, SYSTEM |
| ITStatus | RECEIVED, ASSIGNED, READY |
| BookingRoute | R1, R2, R3, R4 |

Enums are saved as `VARCHAR` with a CHECK constraint (B-06). The meeting type is a label only. Screens show it as Internal / External plus a switch "The Governor attends".

### 6.2 bookings

| Field | Type | Notes |
|---|---|---|
| id | int | Auto increment |
| reference_code | text(20), unique | `NBC-YY-NNNNN`; YY = last 2 digits of the local year when sent; retried on a clash (B-28) |
| requester_id | FK users | The booker |
| room_id | FK rooms | |
| requester_info | JSON | Copy at send time: name_en, name_kh, staff_id, position, division, department, office, email, phone, and the Khmer names of the department and division (for the slip). Answers also carry the booker's **current** phone and email. |
| meeting_title | text(200) | Required, 3 to 200 letters |
| meeting_type | MeetingType | Required |
| meeting_purpose | text(1000), optional | Agenda or notes |
| attendees | int | 1 to 100 |
| private_justification | text(1000), optional | Required for route R2 only |
| route | BookingRoute **(added)** | Set at send (D-28) |
| status | BookingStatus | |
| confirmed_at | datetime, optional | Set when the booking becomes CONFIRMED (also R3, at send). The signers' date comes from it. |
| cancelled_at | datetime, optional | |
| cancelled_by | FK users, optional | The booker or the Admin. Empty for the system (B-27, B-35). |
| cancel_reason | text(500), optional | The reason, if given |
| version | int, default 1 | Raised on every change (section 5) |
| created_at, updated_at | datetime | |

### 6.3 booking_sessions

| Field | Type | Notes |
|---|---|---|
| id | int | |
| booking_id | FK bookings | 1 to 20 per booking |
| room_id | FK rooms | Copy of the booking's room, for the clash index (B-05) |
| date | date | Local Phnom Penh date (B-01) |
| start_time, end_time | time | Inside the room's opening hours |
| is_blocking | bool | True unless the booking is rejected or cancelled. Index (room_id, date, is_blocking) for clash checks. |

The booking's shown date and time = its first session (by date, then start time).

### 6.4 Review, access, slip and files

| Table | Fields | Notes |
|---|---|---|
| booking_reviews | booking_id, stage, decision, reviewer_id, by_admin, notes(1000), reviewed_at | One row per review. R3 saves one PITIKA row as NOT_REQUIRED. |
| booking_rejections | booking_id (unique), rejected_by, actor_user_id, by_admin, reason(1000), decided_at | One per rejected booking. actor_user_id is empty for SYSTEM, so it must allow NULL. |
| booking_door_passes | booking_id (unique), passcode, expires_at | Made when the booking becomes CONFIRMED. |
| booking_participants | booking_id, email | Lowercase, unique per booking, at most 50. |
| booking_signers | booking_id, role, user_id, name_kh, title, signature_path, signed_at | **(added)** The slip signers, copied at confirm (8.8). Old slips never change. |
| booking_attachments | booking_id, file_name(255), content_type(100), size_bytes, stored_path(500), uploaded_by, timestamps | **(added)** Files on a booking (7.12). Rows are really deleted on remove. |
| slip_settings | one row: director_user_id, address_kh(500) | **(added)** Who signs as Director of Cabinet, and the address printed at the foot. |

`departments` and `divisions` each get `head_user_id` (the head who signs the slip). Users keep one saved signature.

### 6.5 Services

| Table | Fields | Notes |
|---|---|---|
| catering_orders | booking_id (unique), packages JSON, remarks(1000), approver_notes(1000), decided_by, decided_at | packages = copy of [{id, name}] at send time. **No servings and no numbers** (BR-IT-07). Food is delivered at every session's start (6 Nov 2026). decided_by = the Pitika who approved the booking. |
| it_tickets | booking_id (unique), requested_items JSON, special_requirements(1000), status, technician_notes(1000), forwarded_at, assigned_at, ready_at | requested_items = copy of [{id, name}]. forwarded_at is set at the last approval, together with the confirm. IT sees only forwarded tickets. |
| it_ticket_staff | ticket_id, user_id | Unique pair. The user must be an active IT Staff of the IT Lead's province. |

### 6.6 Catalogs

| Table | Fields | Notes |
|---|---|---|
| catering_packages | name(200), description(1000), group, icon, sort_order, is_active, version, timestamps | Admin list. Group: Breakfast, Meals, Breaks & drinks, or none (= Other, shown last). Inactive ones cannot be picked for new bookings. Names are unique (B-13). |
| it_services | name(200), description(1000), group, icon, sort_order, is_active, version, timestamps | Admin list, same rules. Group: Screens & video, Sound & language, Devices & network, Support, or none. |
| public_holidays | holiday_date (unique), name_km(255), name_en(255), remarks, timestamps | Admin list. Only gives a warning (7.10). |

## 7. Business rules

Each rule has an ID so code, tests and questions can point at it. The numbers (15 minutes, 20 sessions, 90 days, 100 attendees, 3 files, 10 MB) are API settings with these defaults, not fixed in code.

### 7.1 Scheduling

| ID | Rule |
|---|---|
| BR-SCH-01 | Every session fits inside the room's own opening and closing time. Message: "This room is open from 08:00 to 17:00." |
| BR-SCH-02 | End is after start, and a session is at least 15 minutes. |
| BR-SCH-03 | No session in the past. Today: the start is at or after the current time (Phnom Penh time, UTC + 7). |
| BR-SCH-04 | A session clashes with another in the same room and date when new start < other end AND new end > other start. Back-to-back sessions (one ends 10:00, next starts 10:00) are allowed. |
| BR-SCH-05 | Only blocking sessions count: every booking that is not rejected or cancelled, including waiting ones. |
| BR-SCH-06 | Sessions inside one booking must not overlap each other. |
| BR-SCH-07 | All sessions are checked together. If one fails, nothing is saved, and the error names that session (0-based, like `sessions.0.start_time`). |
| BR-SCH-08 | Clash, past-time and holiday checks run on the server when the booking is saved, in one transaction that locks the room row (`SELECT … FOR UPDATE`). |
| BR-SCH-09 | Only bookable rooms: the room, its floor, building and office are all active. A private room with no owner is refused with `ROOM_NOT_BOOKABLE`, "This private room has no owner yet." (B-07). |
| BR-SCH-10 | At most 20 sessions per booking, and no session more than 90 days ahead. |
| BR-SCH-11 | Weekends are allowed. |
| BR-SCH-12 | A session on a public holiday is allowed, with a warning (7.10). |
| BR-SCH-13 | Routes R1, R2 and R4 are refused when the room's province has no active Pitika: "No reviewer for this office yet." R3 needs no Pitika and is allowed. |
| BR-SCH-14 | One person may book two rooms at the same time. Clash checks are per room only (B-26). There is no limit on waiting bookings per person (B-29). |

### 7.2 Privacy

| ID | Rule |
|---|---|
| BR-PRV-01 | In a room's schedule, a booking in a private room is shown as "Reserved (Private Session)" to users who may not see it (section 3). Title, booker and purpose are hidden. |
| BR-PRV-02 | Clash messages follow the same rule: "This room is already booked from 08:30 to 10:00 for Reserved (Private Session)." |
| BR-PRV-03 | The door pass is never sent before the booking is confirmed, and only to the users in section 3. |
| BR-PRV-04 | A booking counts as private when its room is private now **or** its route is not R1. So a room that turns shared does not show its old private bookings (B-30). One helper decides it everywhere. |

### 7.3 Booking form

| ID | Rule |
|---|---|
| BR-FRM-01 | At least one session. |
| BR-FRM-02 | Meeting title (3 to 200 letters) and meeting type are required. |
| BR-FRM-03 | Attendees: a whole number from 1 to 100, and at least the number of participants plus 1 (the booker). |
| BR-FRM-04 | More attendees than room seats is allowed, with a warning: "This room has 12 seats. You entered 20 attendees." |
| BR-FRM-05 | Participant emails: valid, saved lowercase, no repeats, at most 50. The booker's own email is removed from the list (B-23). |
| BR-FRM-06 | requester_info is copied from the booker's profile when the booking is sent, so later profile changes do not change old bookings. Exception: the booking answers also carry the booker's **current** phone and email, so a reviewer can reach them. |
| BR-FRM-07 | Route R2 (another person's private room) needs a private justification. |
| BR-FRM-08 | Food: at least one active catering package, plus optional remarks (for example "no pork"). IT: at least one active IT service, plus optional special requirements. |
| BR-FRM-09 | Files are optional and are added after the booking is sent (7.12). A failed upload never stops the booking. |

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
| BR-APR-08 | **Team view (17 Nov 2026).** The Approved and Rejected lists and today's numbers hold every Pitika-stage decision of the province: every Pitika, and Admin backups. Each item says who decided (`decided_by`, `by_admin`). The lists are read only: no undo, no reject after approve. |

### 7.5 Room owner review

| ID | Rule |
|---|---|
| BR-OWN-01 | The owner acts only on PENDING_OWNER bookings in their own private rooms. They approve or reject the whole booking and cannot change its times. An approval after the first session started is refused with `TIME_PASSED`; a reject is still allowed (B-09). |
| BR-OWN-04 | There is no backup approver among room owners. If the owner does not act, the booking expires (T15). The Admin may act as a backup (B-34). |
| BR-OWN-05 | Waiting bookings follow the room: when the Admin sets a new owner, the new owner sees them at once. |
| BR-OWN-06 | The owner's Approved and Rejected lists hold their own decisions, in rooms they own now. |

### 7.6 IT support

IT is an add-on to a confirmed booking (19 Nov 2026). IT has no reject.

| ID | Rule |
|---|---|
| BR-IT-01 | The IT ticket is made when the booking is sent. IT sees it only after the last approval (`forwarded_at` is set at the same moment as the confirm) and while the booking is not rejected or cancelled. |
| BR-IT-02 | The IT Lead assigns one or more active IT Staff and can change them later. This is allowed while the setup is not Ready and the first session has not started, and still while later sessions remain (6 Nov 2026). It does not change the booking's status or door pass, and a setup made ready stays Ready. |
| BR-IT-03 | Only the IT Lead presses Ready, only after active staff are assigned, and only before the first session starts. Ready marks **only the setup**. It never changes the booking's status or door pass. |
| BR-IT-04 | IT Staff see the tickets they are assigned to; they cannot change them. |
| BR-IT-05 | Setup is planned 30 minutes before every session (6 Nov 2026). Staff are assigned once; Ready is pressed once, for the first session, and later sessions are reminders with no check. Day filters, day counts and time clashes look at every session. |
| BR-IT-06 | If IT has not pressed Ready when the first session starts, the setup is **missed**. Nothing changes for the booking. The ticket can no longer be marked ready. The IT pages show it as "Missed · not marked ready", and the booker sees "Not marked ready" in crimson. (For old `SETUP_IN_PROGRESS` rows the system still confirms the booking at the start, T17.) |
| BR-IT-07 | **Food has no numbers** (17 Nov 2026). The API sends no servings. The kitchen reads the attendees. No screen shows servings, "× N" or food totals. Counting deliveries or rooms is fine. |
| BR-IT-08 | **Same province (17 Nov 2026).** An IT Lead sees only tickets of rooms in their office's province, and the staff picker lists only IT Staff of that province. Assigning staff of another province is refused with `422` on `user_ids`. |
| BR-IT-09 | Turning off an IT Staff user is not blocked. Ready needs at least one **active** assigned IT Staff, else `409 INVALID_TRANSITION`, "Assign active IT Staff first." Assigning a user who is not active IT Staff is `409 INACTIVE_REFERENCE`. Lists show inactive staff with `is_active: false` (B-22). |

### 7.7 Door pass

| ID | Rule |
|---|---|
| BR-DP-01 | Format "NBC-" and 5 digits (10000 to 99999), from a secure random source, unique among active door passes, and never equal to the reference code. |
| BR-DP-02 | Made when the booking becomes CONFIRMED, which is now the last approval, with or without IT. It ends at the end of the last session. |
| BR-DP-03 | After it ends, the API still returns it with `"expired": true`. |
| BR-DP-05 | It is not linked to a real door lock, and it is not emailed in this version. |

### 7.8 Cancel

| ID | Rule |
|---|---|
| BR-CAN-01 | The booker can cancel any booking that is not final, until the last session ends. Finished sessions stay in history; later sessions are freed. A Pitika or room owner who does not want a booking rejects it instead. |
| BR-CAN-02 | **Admin cancel (B-33).** The Admin may cancel any booking that is not final and not ended, with an optional reason and the same effects as the booker's cancel. |
| BR-CAN-03 | Cancelling frees the time at once and drops the food order and IT ticket (the rows stay for history; lists hide them by booking status, B-11). |
| BR-CAN-04 | The booking keeps who cancelled (`cancelled_by`) and who decided (`by_admin`). The booker sees an Admin action when they open the booking. There is no notification (B-35, B-36). |

### 7.9 Edit

| ID | Rule |
|---|---|
| BR-EDT-01 | Only the booker edits, only while the booking is not final, and only before the first session starts. |
| BR-EDT-02 | **Small fields** keep the approval: title, meeting type, purpose, attendees, participants, food remarks, IT special requirements. Changing attendees needs no new Pitika approval. |
| BR-EDT-03 | Room, sessions, food, IT and the private justification can't be edited. Cancel and book again. Sending `catering` when the booking has no food order (or `it` with no ticket) is refused too. A PATCH with only `version` changes nothing (B-15, B-24). |

### 7.10 Public holidays

| ID | Rule |
|---|---|
| BR-HOL-01 | The Admin keeps the list: one row per date, Khmer name required, English name optional. |
| BR-HOL-02 | Booking on a holiday is allowed (owner decision, 12 Nov 2026). The check and the save answers carry a warning: `{"code": "PUBLIC_HOLIDAY", "date": "2026-11-09", "name": "Independence Day"}`. Screens show it softly in amber; reviewers see the Khmer holiday name first in the row's tags and a line in the approve pop-up. |
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
| Files per booking | At most 3, each at most 10 MB |

Text is trimmed before checks. HTML is never accepted; text is saved as plain text.

### 7.12 Files on a booking

Owner decisions, 16 Nov 2026.

| ID | Rule |
|---|---|
| BR-ATT-01 | Files are optional. A booking with no file works exactly as before. |
| BR-ATT-02 | Documents only: PDF (`.pdf`), Word 97–2003 (`.doc`), Excel 97–2003 (`.xls`), Word (`.docx`), Excel (`.xlsx`). The type is decided by the file's **content**, never only by its name or `Content-Type`. The extension must also agree with the content. The zip of a `.docx` or `.xlsx` is only listed, never extracted. Anything else: `415 UNSUPPORTED_FILE_TYPE`, "Only PDF, Word or Excel files." |
| BR-ATT-03 | At most 10 MB per file (`413 FILE_TOO_LARGE`). An empty file is `422 VALIDATION_ERROR`. At most 3 files per booking (`409 ATTACHMENT_LIMIT_REACHED`). |
| BR-ATT-04 | Everyone who can see the booking (section 3) can list and download its files, in every status, for ever. Anyone else gets `404`. |
| BR-ATT-05 | Only the booker adds or removes files (others: `403`). It is allowed while the booking is PENDING_PITIKA, PENDING_OWNER or SETUP_IN_PROGRESS. When it is CONFIRMED, REJECTED or CANCELLED: `409 INVALID_TRANSITION`, "Files are locked once the booking is confirmed." (or "…is closed."). Because the last approval now confirms the booking, files lock then, with or without IT. The lock is by status only, not by time. |
| BR-ATT-06 | Files are saved in a private folder, never in the public `/uploads` folder. A download sends `Content-Disposition: attachment` with the cleaned name, `X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`. |
| BR-ATT-07 | Adding or removing a file does not change `bookings.version` and needs no `version`. Files are not printed on the slip and are not sent in emails or the calendar file. There is no virus scan and no preview. |

## 8. API endpoints

Same style as the current API: base path `/api/v1`, JSON in snake_case, sign-in with the existing access token, lists with `page` (default 1) and `size` (default 20, at most 100) that answer `{"items": […], "page": 1, "size": 20, "total": 240}`. Every request that changes a booking sends its `version` (files excepted). A `to` date before `from` is `422`.

### 8.1 Booker

| Method | Path | What it does |
|---|---|---|
| GET | /rooms?free_dates=&free_from=&free_to= | The room list. The three `free_*` filters (all or none) keep only rooms open and free at that time on every listed date (at most 20 dates). |
| GET | /rooms/{id}/schedule?from=&to= | Blocking sessions of one room between two dates, private ones masked (BR-PRV-01). At most 31 days. |
| GET | /room-schedule?date=&room_ids= | Every listed room's busy times for one day, with the same masking. One call feeds a whole page of room cards. |
| POST | /bookings/check | Body: room_id, sessions, has_catering, has_it. Answers the route (R1 to R4), the steps the booking will go through, the first problem found, and any warnings. Saves nothing. |
| POST | /bookings | Sends a booking (T1 or T2). Answers 201 with the full booking, its route, status and warnings. |
| GET | /bookings/mine?status=&q= | The booker's own bookings, newest first. Each item has `next_session` (the first session not ended yet). |
| GET | /bookings/{id} | One booking, for the users allowed in section 3. |
| PATCH | /bookings/{id} | Small edit (T13). Body: the small fields (meeting_title, meeting_type, meeting_purpose, attendees, participant_emails, catering.remarks, it.special_requirements) plus version. Sending room_id, sessions, catering.package_ids, it.service_ids or private_justification is refused with 422 FIELD_NOT_EDITABLE. Answers the full booking. |
| POST | /bookings/{id}/cancel | Booker only. Body: reason (optional), version. T12. |
| GET | /bookings/{id}/door-pass | The door pass, its end time and "expired". Only when CONFIRMED. |
| GET | /bookings/{id}/ics | A calendar file with every session (times in UTC with `Z`, one event per session). |
| GET | /bookings/{id}/request-slip | The request slip as a Word file (8.8). Only when CONFIRMED or COMPLETED. |

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

`catering` and `it` are `null` when not asked for. The server picks the route; the body never sends it. Local dates and times go out as `date` ("2026-11-10") and `time` ("09:00") pairs; stored UTC times go out with a `Z` (B-17).

### 8.2 Pitika

| Method | Path | What it does |
|---|---|---|
| GET | /pitika/bookings?status=&from=&to=&room_id=&q= | Bookings for rooms in the Pitika's province. from and to match any session date. |
| GET | /pitika/bookings/decided?decision=&q=&room_id=&from=&to= | Every Pitika-stage decision in the province, newest first (BR-APR-08). Each item has `decided_at`, `decision_note`, `decided_by` and `by_admin`. |
| GET | /pitika/bookings/summary | `{waiting, approved_today, rejected_today}`; the day is the Phnom Penh day. |
| POST | /pitika/bookings/{id}/approve | Body: notes, version. The server picks T3, T4 or T5 from the route. |
| POST | /pitika/bookings/{id}/reject | Body: reason, version. T6. |
| GET | /pitika/catering?date= | Food orders of CONFIRMED bookings (and old SETUP_IN_PROGRESS rows) on one day: packages, room, delivery time, session number, remarks. One delivery per session. No servings. The Admin may call it too and sees every province (B-12). |

### 8.3 Room owner

| Method | Path | What it does |
|---|---|---|
| GET | /owner/bookings?status=&room_id=&from=&to=&q= | Bookings in the owner's private rooms. |
| GET | /owner/bookings/decided?decision=… | The owner's own decisions, in rooms they own now. |
| GET | /owner/bookings/summary | `{waiting, approved_today, rejected_today}`. |
| POST | /owner/bookings/{id}/approve | Body: notes, version. T7 or T8. |
| POST | /owner/bookings/{id}/reject | Body: reason, version. T9. |

### 8.4 IT

| Method | Path | What it does |
|---|---|---|
| GET | /it/tickets?state=&mine=&from=&to=&status=&q= | IT Lead: every forwarded ticket in their province. IT Staff: only tickets they are assigned to. `state` = `to_assign`, `in_progress` or `done`. `from` and `to` are the **setup** day. `mine=true` keeps only my tickets. Each item has `missed` (BR-IT-06). |
| GET | /it/tickets/summary | IT Lead. `{to_assign, in_progress, ready_today, due_today, due_today_ready}`. |
| GET | /it/staff | IT Lead. Active IT Staff of their province: `{id, name_en, name_kh}`, with each person's other setups at the same time. |
| PUT | /it/tickets/{id}/staff | IT Lead. Body: user_ids, technician_notes, version (the booking's, B-19). T10. |
| POST | /it/tickets/{id}/ready | IT Lead. Body: version. T11. |

State rules: **To assign** = ticket RECEIVED and not missed. **In progress** = ASSIGNED and not missed, and kept while later sessions remain. **Ready** (`done`) = READY, plus missed ones, which show "Missed · not marked ready" and have no buttons.

### 8.5 Catalogs and holidays

Every signed-in user can read these lists (the booking form needs them). Non-Admins see only active rows. Only the Admin changes them.

| Method | Path | What it does |
|---|---|---|
| GET, POST | /catering-packages | List; add one (with group and icon) |
| PATCH | /catering-packages/{id} | Edit, make active or inactive; needs `version` |
| GET, POST | /it-services | List; add one (with group and icon) |
| PATCH | /it-services/{id} | Edit, make active or inactive; needs `version` |
| GET, POST | /public-holidays?year= | List; add one |
| PATCH, DELETE | /public-holidays/{id} | Edit; delete (no booking points at a holiday) |

### 8.6 Expiry job

A job runs every minute. It rejects (T15) every PENDING_PITIKA or PENDING_OWNER booking whose first session has started, and confirms (T17) any old SETUP_IN_PROGRESS booking whose first session has started. It does nothing about IT on confirmed bookings: a setup that is not ready is simply shown as missed. It runs in one process only (a MySQL lock). `python -m scripts.run_expiry` runs it once.

### 8.7 Files

All under `/bookings/{booking_id}/attachments`, signed-in users only (7.12).

| Method | Path | Who | What it does |
|---|---|---|---|
| GET | (list) | Viewers | The files: `id`, `file_name`, `content_type`, `size_bytes`, `created_at`, `url`. |
| POST | (multipart, field `file`) | Booker, open status | Adds one. Answers 201. |
| GET | /{attachment_id} | Viewers | The file. A file id from another booking is `404`. |
| DELETE | /{attachment_id} | Booker, open status | Removes it. Answers 204. |

The booking answer also carries `attachments` and `attachments_open` (the status still lets files change).

### 8.8 Request slip

The Khmer ប័ណ្ណស្នើ request slip (owner decisions, 13 to 18 Nov 2026).

- **Format and access.** A Word file (`.docx`) only. `GET /bookings/{id}/request-slip`, for the booker, the Admin and the Pitika of the province, only when CONFIRMED or COMPLETED.
- **Layout.** A4. The NBC header and the address footer are printed. It is addressed to the Director of Cabinet through the Head of Department and the Head of Office. The opinion boxes sit on the left: Director of Cabinet, Head of Department, Head of Office.
- **Filled.** The booker's name and saved signature under អ្នកធ្វើប័ណ្ណ. The department is the booker's department (Khmer name), the office is the booker's division (Khmer name); dots when none. The subject is one sentence with the times in Khmer words. From = first session, until = last, plus the number of days; a short timetable of every session is added when the times differ. The lines for what was asked (food, IT) list the real items; nothing asked → "- មិនមាន". Food has no numbers.
- **Date.** The day the booking was **sent**, with the full Khmer lunar date (day, waxing or waning, lunar month, animal year, era, Buddhist year) in Khmer numerals, then "រាជធានីភ្នំពេញ ថ្ងៃទី … ខែ … ឆ្នាំ …". The lunar calendar is checked on every day of 2026 and 2027.
- **Signers.** There is no extra approval step. When the booking becomes CONFIRMED (R3: at send), the system signs all 3 boxes at once with each person's saved signature, the confirm date and a standard comment. Heads: "សូមគោរពជូន … មេត្តាពិនិត្យ និងសម្រេចដោយអនុគ្រោះ។". Director: "ឯកភាពតាមសំណើ។". A booker who is a head signs that box too. The signers (name, title, signature, confirm time) are **copied at confirm** (`booking_signers`), and the Khmer department and division names are copied at send, so old slips never change. An empty box is filled by the head set now; a kept signature never changes.
- **Titles.** Mr. → លោក, Ms. or Mrs. → លោកស្រី, Dr. → បណ្ឌិត. Heads are written "លោក/លោកស្រីប្រធាន…".
- **Look.** All signatures print in the pen blue of the comments. Everything else is black. The top quarter stays empty for letterhead paper. The slip must stay on one page.
- **Settings (Admin).** `GET` and `PUT /slip-settings`: the Director of Cabinet and the address. The Admin also sets a head on each department and each division. Until they do, those boxes stay empty.

### 8.9 Admin

| Method | Path | What it does |
|---|---|---|
| GET | /bookings?status=&province=&from=&to=&room_id=&q= | Every booking. Read only list (B-32). |
| GET | /admin/bookings/{id}/actions | What the Admin may do now (cancel, approve, reject). |
| POST | /admin/bookings/{id}/cancel | B-33. Reason optional. |
| POST | /admin/bookings/{id}/approve | B-34, backup reviewer. |
| POST | /admin/bookings/{id}/reject | B-34, backup reviewer. |

### 8.10 Finding a room

A user can find a room that is free: the room cards, `GET /rooms` with `free_*` and `GET /room-schedule` (8.1) give every room's busy times for a day. For Pitika and Admin, the **Room availability** page uses the same day schedule: one row per room of the province (Admin: every active room), hours across. A room is free at time *t* when *t* is inside its opening hours (`start` ≤ *t* < `end`) and no block covers *t* (a block covers [start, end)). Blocks show Booked (CONFIRMED, SETUP_IN_PROGRESS), Waiting (PENDING_PITIKA, PENDING_OWNER) and Masked (private, the reader may not see it). "Now" is the Phnom Penh clock.

## 9. Errors

Errors keep the current shape: `{"error": {"code": "SCHEDULE_CONFLICT", "message": "…", "fields": {…}}}`. The existing codes stay (VALIDATION_ERROR 422, FORBIDDEN 403, NOT_FOUND 404, DUPLICATE 409, INACTIVE_REFERENCE and others). Booking adds these:

| Code | HTTP | When | Example message |
|---|---|---|---|
| SCHEDULE_CONFLICT | 409 | A session clashes with another booking | "This room is already booked from 08:30 to 10:00 for Reserved (Private Session)." |
| TIME_PASSED | 409 | A session is in the past, or a review comes after the first session started | "This session starts at 09:00, which has passed." |
| OUTSIDE_ROOM_HOURS | 422 | A session is outside the room's opening hours | "This room is open from 08:00 to 17:00." |
| ROOM_NOT_BOOKABLE | 409 | The room, its floor, building or office is inactive, or a private room has no owner | "This room cannot be booked right now." |
| NO_REVIEWER | 409 | The room's province has no active Pitika (BR-SCH-13) | "No reviewer for this office yet." |
| INVALID_TRANSITION | 409 | A move not in the transition table, files after confirm, Ready with no active staff | "This booking is already confirmed." |
| STALE_VERSION | 409 | Someone changed the booking first | "This booking changed. Reload it." |
| FIELD_NOT_EDITABLE | 422 | An edit tries to change the room, sessions, food or IT (BR-EDT-03) | "To change the room, date or time, cancel and book again." |
| OWNER_REQUIRED | 422 | A private room is saved with no owner (section 10) | "A private room needs an owner." |
| OWNER_HAS_PRIVATE_ROOMS | 409 | Making a room owner inactive, or removing the role, while they own a private room | "Assign a new owner for 2 private rooms first." |
| HAS_FUTURE_BOOKINGS | 409 | Making a room, floor, building or office inactive, or moving one to a new parent, while it has future bookings (section 10) | "This room has 3 future bookings. Ask the bookers to cancel first." |
| HAS_PENDING_OWNER_BOOKINGS | 409 | Changing a private room to shared while bookings wait for its owner (section 10) | "Resolve 3 bookings waiting for the room owner first." |
| UNSUPPORTED_FILE_TYPE | 415 | A file is not a PDF, Word or Excel document (BR-ATT-02) | "Only PDF, Word or Excel files." |
| FILE_TOO_LARGE | 413 | A file is over 10 MB | "File too big (max 10 MB)." |
| ATTACHMENT_LIMIT_REACHED | 409 | A 4th file | "Up to 3 files." |

Limits on sessions, attendees, emails and text lengths use VALIDATION_ERROR with `fields`, for example `{"sessions.2.end_time": "A session is at least 15 minutes."}`. Assigning IT Staff of another province is `422` on `user_ids` (BR-IT-08).

Warnings are not errors. The check and save answers carry a list such as `"warnings": [{"code": "PUBLIC_HOLIDAY", …}, {"code": "OVER_CAPACITY", "seats": 12, "attendees": 20}]`.

## 10. Changes to the current API

These rules change things that are already built and used by the admin dashboard. The dashboard must show the new messages.

| Where | Today | After |
|---|---|---|
| Create or edit a room | A private room can have no owner. | Refused with OWNER_REQUIRED. (Old rooms with no owner stay, but cannot be booked, B-07.) |
| Make a user inactive, or remove their Room owner role | Their rooms lose their owner. | Refused with OWNER_HAS_PRIVATE_ROOMS while they own a private room. Shared rooms still lose their owner, as today. Turning a user off also cancels their open bookings (B-27); the answer of `PATCH /users/{id}` has `bookings_cancelled: [ids]`. |
| Change a room's owner | Only the room changes. | Waiting bookings follow the room: the new owner sees them (BR-OWN-05). |
| Change a private room to shared | Allowed. | Refused while the room has PENDING_OWNER bookings, or R2 bookings still PENDING_PITIKA: HAS_PENDING_OWNER_BOOKINGS (B-14). |
| Lower a room's seats | Allowed. | Still allowed; existing bookings are not changed. |
| Change a room's opening hours | Allowed. | Still allowed; existing bookings are not checked again. |
| Make a room, floor, building or office inactive | Allowed; it stops being bookable. | Refused while the room (or any room inside it) has future bookings, with HAS_FUTURE_BOOKINGS. |
| Move a room to another floor, a floor to another building, a building to another office, or change an office's province | Allowed. | Refused while it has future bookings (HAS_FUTURE_BOOKINGS, B-21). Otherwise waiting bookings could move to another Pitika's province. |
| Catering packages and IT services | Name, description, order. | Also a group and an icon, set by the Admin. No group = Other, shown last (12 Nov 2026). |
| Departments and divisions | Names. | Each also has a head, who signs the request slip. |

## 11. Decisions log

Every place where the sources disagreed or said nothing has one decision here. "Boss review" = decided in the review of 2 Nov 2026. "Writer's call" = chosen while writing the spec. "Spec review" = decided while reviewing the spec on 2 Nov 2026. "Owner" = the owner's decision on the date shown.

| ID | Topic | Decision | Source | Where |
|---|---|---|---|---|
| D-01 | Catering approval | One Pitika approval approves the booking and its food | Boss review | BR-APR-06 |
| D-02 | IT roles | IT Lead assigns IT Staff and presses Ready | Boss review (changed) | BR-IT-02, BR-IT-03 |
| D-03 | Booking hours | Each room's own opening hours | Boss review | BR-SCH-01 |
| D-04 | Holidays | Public holidays only; allowed with a warning | Boss review; owner 12 Nov | 7.10 |
| D-05 | Owner step | A private room must have an owner, who reviews after Pitika | Boss review | Route R2, section 10 |
| D-06 | Backup approver | No backup among room owners; the booking expires. The Admin may act (D-33, D-34). | Boss review | BR-OWN-04 |
| D-07 | Pitika queue | One queue per province | Boss review (changed) | BR-APR-01 |
| D-08 | No Pitika in a province | New bookings needing Pitika are refused | Boss review | BR-SCH-13 |
| D-09 | Meeting type | 4 values, label only; screens show Internal / External plus "The Governor attends" | Boss review; owner 12 Nov | 6.1 |
| D-10 | Notifications | None in this version | Boss review | Section 1 |
| D-11 | Scope | Booking API, plus the screens in section 13 | Boss review; owner | Section 1 |
| D-12 | Owner leaves | Refused while owning a private room | Boss review | Section 10 |
| D-13 | Routes, statuses, transitions | As the old spec, "Manager" renamed Pitika; the last approval now confirms (D-41) | Old spec | Sections 4, 5 |
| D-14 | Time limits | 15 minutes, 20 sessions, 90 days, weekends allowed | Old spec | 7.1 |
| D-15 | Edit and cancel | Small edits only; room, sessions, food and IT need cancel and book again; one cancel cut-off for the booker (end of the last session) | Old spec (changed) | 7.8, 7.9 |
| D-16 | Expiry | System rejects at first session start | Old spec | T15 |
| D-17 | Door pass | Made at confirm, not emailed, not linked to a lock | Old spec, changed by D-10 | 7.7 |
| D-18 | Pending bookings block | Waiting bookings hold their time | Old spec and mockup | BR-SCH-05 |
| D-19 | Food after approval | Food never holds a booking; IT no longer does either (D-41) | Old spec | T4, T5 |
| D-21 | Private justification | Required for route R2 only | Writer's call | BR-FRM-07 |
| D-22 | Food list | Pitika sees the day's food orders for their province and prepares the food. No kitchen role in this version. | Spec review | 8.2 |
| D-23 | Session grid | The API takes any minute; a 30-minute grid is for screens | Writer's call | 7.1 |
| D-24 | Owner times | The owner approves or rejects the whole booking and cannot shorten times | Spec review | BR-OWN-01 |
| D-25 | Inactive place with bookings | Refused until the bookers cancel or the meetings are over | Spec review | Section 10 |
| D-26 | Who can book | Every active user, whatever their role | Spec review | Section 3 |
| D-27 | Who can cancel | The booker; Pitika and room owner reject instead (the Admin: D-32) | Spec review | BR-CAN-01 |
| D-28 | Saved route | bookings.route is saved at send, so a later owner change does not change the route of old bookings | Spec review | 6.2 |
| D-29 | System rejection | booking_rejections.actor_user_id allows NULL; expiry is rejected by SYSTEM with no user | Spec review | 6.4, T15 |
| D-30 | Cancel a long booking | The booker can cancel until the last session ends, so a stopped series frees its later sessions | Spec review | BR-CAN-01, T12 |
| D-31 | IT not ready in time | At first session start the system confirms the booking anyway (now only old rows; new bookings are already confirmed) | Spec review; D-41 | BR-IT-06, T17 |
| D-32 | Admin cancel | The Admin may cancel any booking that is not final and not ended | Owner 4 Nov | BR-CAN-02 |
| D-33 | Admin backup, Pitika step | Only when the province has no active Pitika | Owner 4 Nov | T3 to T9 |
| D-34 | Admin backup, owner step | Any PENDING_OWNER booking | Owner 4 Nov | T3 to T9 |
| D-35 | Admin cancel reason | Optional | Owner 4 Nov | BR-CAN-02 |
| D-36 | Who acted | Saved: cancelled_by, by_admin | Owner 4 Nov | 6.2, 6.4 |
| D-37 | Time rules | The Admin follows the same time rules as everyone | Owner 4 Nov | T3 to T9 |
| D-38 | Admin cancel effects | The same as the booker's cancel | Owner 4 Nov | BR-CAN-03 |
| D-39 | Notice | No notification; the booker sees an Admin action on opening the booking | Owner 4 Nov | BR-CAN-04 |
| D-40 | Admin IT steps | None | Owner 4 Nov | T10, T11 |
| D-41 | IT setup is an add-on | The last approval confirms the booking with its door pass; IT runs beside it, cannot reject, cannot hold it. Look F: Confirmed, then IT setup as the 4th step. Old SETUP_IN_PROGRESS rows are confirmed by a one-off script. | Owner 19 Nov | Sections 4, 5, 7.6 |
| D-42 | No food numbers | No servings, no "× N", no food totals anywhere | Owner 17 Nov | BR-IT-07 |
| D-43 | Reference code | `NBC-YY-NNNNN`; the door pass keeps `NBC-` and 5 digits | Writer's call 3 Nov | 6.2, B-28 |
| D-44 | Food at every session | One delivery per session | Owner 6 Nov | 6.5 |
| D-45 | IT before every session | Setup planned 30 minutes before each session; Ready once | Owner 6 Nov | BR-IT-05 |
| D-46 | Same-role teamwork | Pitika sees every decision of the province and who made it. IT Lead works only in their own province. | Owner 17 Nov | BR-APR-08, BR-IT-08 |
| D-47 | Files on a booking | Optional, documents only, everyone who can see the booking can open them, the booker adds or removes until confirmed | Owner 16 Nov | 7.12 |
| D-48 | Request slip | Word file; signed by the 3 heads at confirm; signers copied at confirm | Owner 13 to 18 Nov | 8.8 |
| D-49 | Booker contact | Booking answers carry the booker's current phone and email | Owner 19 Nov | BR-FRM-06 |
| D-50 | Room availability | A page for Pitika and Admin: every room's day, "Free at" in one step, no summary cards, no booking from it | Owner 17 Nov | 8.10, 13 |
| D-51 | Staff pages | Staff book inside the dashboard, with the sidebar; same login | Owner 12 Nov | 13 |

Old build-spec calls B-01 to B-36 stay in force. They are listed in `2026-11-03-room-booking-api-design.md`.

## 12. Tests and open questions

### 12.1 Tests that must pass

Each item is at least one API test (pytest). Screens have Vitest and layout checks (13).

- [ ] Each route R1 to R4 from send to CONFIRMED, with and without IT. With IT, the booking is CONFIRMED at the last approval, the door pass exists and the ticket is forwarded.
- [ ] Each transition T1 to T17 (T14 and T16 are removed), and one move that is not allowed (INVALID_TRANSITION).
- [ ] Mark ready changes only the ticket (booking status and door pass stay); it is refused after the first session starts; an old SETUP_IN_PROGRESS booking is still confirmed by it.
- [ ] Assign or change staff on a confirmed booking while the setup is not Ready; refused for staff of another province.
- [ ] The one-off confirm script confirms old SETUP_IN_PROGRESS rows and is safe to run twice.
- [ ] Clash: overlap refused, back-to-back allowed, a rejected or cancelled booking does not block, a waiting one does.
- [ ] Two sessions in one booking that overlap are refused; one bad session saves nothing.
- [ ] Room hours, 15-minute minimum, past time, 20 sessions, 90 days.
- [ ] Two Pitika approve the same booking at once: one wins, one gets STALE_VERSION.
- [ ] A Pitika cannot see or act on a room in another province; NO_REVIEWER when a province has no Pitika; R3 still works.
- [ ] The Pitika decided list holds other Pitikas' and Admin backup decisions, with `decided_by` and `by_admin`.
- [ ] Expiry job rejects a waiting booking after its first session starts, and confirms an old booking still in SETUP_IN_PROGRESS (with a door pass).
- [ ] Door pass: hidden before confirm, shown after, "expired" after the last session.
- [ ] Private booking shown as "Reserved (Private Session)" to others, in the schedule and in clash messages, also after the room turns shared.
- [ ] Small edit keeps the status; changing the room, sessions, food or IT is refused with FIELD_NOT_EDITABLE.
- [ ] The booker can cancel until the last session ends; finished sessions stay in history; a Pitika or room owner cannot cancel (FORBIDDEN); the Admin can, and `cancelled_by` is saved; turning off a booker cancels their open bookings.
- [ ] Admin backup: refused when the province has an active Pitika; allowed on PENDING_OWNER; no IT steps.
- [ ] Files: each type accepted; a renamed `.exe` or image refused (415); a `.docx` name on a PDF refused; 10 MB + 1 byte refused (413); a 4th file refused (409); every viewer role can list and download; a non-viewer gets 404; a non-booker viewer gets 403 on upload and delete; upload and delete refused when confirmed, rejected or cancelled; the file is not under `/uploads`; the download headers; a Khmer file name.
- [ ] Request slip: refused before confirm; the signers are copied at confirm and old slips do not change; the Khmer lunar date is right on every day of 2026 and 2027.
- [ ] Holiday and over-capacity warnings.
- [ ] No answer, list or screen shows food servings or "× N".
- [ ] Section 10: private room without owner refused; owner leaving refused; waiting bookings follow a new owner; making a room inactive, or moving it, with future bookings refused; private → shared refused with waiting owner bookings.

### 12.2 Open questions

- **Fixed 26 Nov: R3 slip.** An R3 booking now saves its confirm time and slip signers at send. For R3 bookings made **before** this fix, run `python -m scripts.sign_old_r3_bookings` once: it gives each confirmed R3 booking with no confirm time its send time as the confirm time, and copies the signers set now. It is safe to run twice.
- **Fixed 26 Nov: IT Lead and other provinces.** `GET /bookings/{id}` and its files now open for an IT Lead only in their own province, like the IT pages (BR-IT-08).
- **Same-role teamwork, not picked by the owner:** (3) a "someone is looking at this" mark, (4) a second owner per private room, (5) messages between Pitikas. Nothing is built for them.
- **Request slip setup:** the owner must still set the head of each department and division, the Director of Cabinet, and check the address numbers. Until then those boxes stay empty.
- **The IT add-on is merged into `main` (PR #17):** run `python -m scripts.confirm_it_setup_bookings` once on each database that still has bookings in IT setup.
- **The mockup-era rules in the old spec** (`spec.md`, `requirements.md`, Oct 21) cover only rooms and users. They are not changed here.

## 13. Screens (summary)

The screens are in `admin_dashboard/` (Vue 3). One crimson sidebar for everyone; each role sees its own menu (the owner's "dashboard with the sidebar"). The full look, tokens and demos are in `DESIGN.md` and the design notes in this folder. This section only lists the rules that change what a person can do or see.

| Role | Home | Pages | Notes file |
|---|---|---|---|
| Staff | Find a room | Find a room, Room details, Book (4 steps: Schedule, Meeting details, Food & IT, Review), My bookings | `2026-11-12-staff-booking-pages-design.md` |
| Pitika | To review | To review (Waiting, Approved, Rejected), Bookings, Food list, Room availability | `2026-11-05-pitika-review-design.md`, `…pitika-decided-design.md`, `2026-11-17-room-availability-design.md` |
| Room owner | To review (owner) | To review (labelled **My rooms** when the user is also a Pitika), Bookings | `2026-11-05-owner-and-it-pages-design.md` |
| IT Lead | IT setup | To assign, In progress, Ready | same |
| IT Staff | My tasks | My tasks (read only) | same |
| Admin | Rooms | Every admin list, Bookings with Admin actions, Request slip settings, Service catalog | `2026-10-26-admin-dashboard-requirements.md` |

Rules that hold on every screen:

- A user with none of these roles sees "No access". Staff-only users land on Find a room.
- **No food numbers** (BR-IT-07). **No status dots:** a status is always an icon and a word, never a coloured dot. "Private" always uses the person-and-lock icon (Lucide `UserLock`).
- The booker's IT step reads "Sent to IT", "Setting up", "Room ready" or "Not marked ready"; crimson only when missed (section 4).
- Approve pop-ups say what happens next: "It is confirmed, with a door pass. IT gets the setup to do." (+ "The food is approved with it."). The Mark ready pop-up says "The room is ready for the meeting. The booking is already confirmed."
- Reviewers see holidays, the booker's phone and email (click to copy), and files on the booking.
- Days and times are Phnom Penh time. Pages work in light and night theme, on phone widths, with the keyboard and with reduced motion.
- Built but not yet committed on 26 Nov 2026 (only in the working tree): the Find a room card and filters, Room details, the week-table pick pills, the My bookings folders page. Their old Vitest specs still need to be rewritten before commit.

## 14. Where the older files are

| File | Use |
|---|---|
| `2026-11-02-room-booking-api-requirements.md` and `Room Booking API Requirements v2.docx` | The v2 text this file replaces. Keep for history. |
| `2026-11-03-room-booking-api-design.md` | Build spec: files, tables, check order, tests, build order. |
| `2026-11-05-pitika-review-design.md`, `…pitika-decided-design.md`, `…owner-and-it-pages-design.md` | Page designs. |
| `2026-11-12-staff-booking-pages-design.md` | Staff pages. |
| `2026-11-16-booking-attachments-design.md` | Files, with test list. |
| `2026-11-17-room-availability-design.md` | Room availability page. |
| `2026-11-19-it-setup-addon-design.md` | IT add-on, with the dashboard changes. |
| `DESIGN.md`, `PRODUCT.md` | Look, tokens and product tone. |
