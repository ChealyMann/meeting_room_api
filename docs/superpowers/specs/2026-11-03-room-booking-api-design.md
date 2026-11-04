# Room Booking API: Build Spec

Nov 3, 2026 · for the builder (Claude), from the requirements of Nov 2, 2026

## 0. How to use this spec

- **What to build** is in [2026-11-02-room-booking-api-requirements.md](2026-11-02-room-booking-api-requirements.md) (same text as `docs/Room Booking API Requirements v2.docx`). This spec calls it **"the requirements"**. Rule IDs (BR-SCH-01, T4, D-26 …) point there.
- **How to build it** is here: files, tables, functions, check order, responses, tests, and build order.
- If this spec and the requirements disagree, the requirements win. Stop and ask.
- Scope: **API only.** No admin dashboard changes (decided Nov 3, 2026). No notifications, no screens.
- Follow the house rules: one model class per file; one schema, service and router file per resource; rules live in services; routers stay thin; requirements.txt (no new packages).
- Every rule gets at least one pytest test. Write the test first.

## 1. Goals, non-goals, anti-goals

**Goals**

- Every endpoint in section 8 of the requirements, with the exact paths, bodies and error codes.
- The six statuses and the transition table (T1–T17, without T14 and T16) enforced in one place.
- No double booking, even when two requests come at the same moment.
- The changes to the current API in section 10 of the requirements.

**Non-goals**

- Admin dashboard (Vue) changes. The dashboard will show the new error messages later.
- Notifications, email, prices, reports, audit log, door locks.
- New Python packages. (No APScheduler, no icalendar, no tzdata.)

**Anti-goals (a build that does these is wrong, even if tests pass)**

- A private booking's title, booker or purpose leaks to a user who may not see it (schedule, clash message, list, detail, ics).
- The door pass is returned before CONFIRMED, or to the wrong user.
- Two blocking sessions overlap in one room.
- A status changes without the version check.
- Booking code calls `datetime.now()` directly (tests cannot freeze time).

## 2. Decisions made in this spec (builder's calls)

These are not in the requirements. They are my calls; change them with a comment.

| ID | Topic | Decision |
|---|---|---|
| B-01 | Time | Sessions are saved as **local Phnom Penh** date + time (like room hours). "Now" = UTC + 7 hours, a fixed offset. No `zoneinfo` (Windows needs the `tzdata` package for it). |
| B-02 | Clock | All booking code gets the time from `app/services/clock.py`. Tests freeze it. |
| B-03 | Expiry job | A background thread started by the app. MySQL `GET_LOCK('booking_expiry', 0)` makes sure only one process runs it. Also `python -m scripts.run_expiry` to run it once. Off in tests. |
| B-04 | Version check | Read the booking, compare `version` with the body, then `UPDATE … WHERE id = :id AND version = :v`. 0 rows → `409 STALE_VERSION`. |
| B-05 | Session room | `booking_sessions` gets a `room_id` column (copied from the booking) so the index (room_id, date, is_blocking) in the requirements can exist. |
| B-06 | Enums in the DB | Saved as `VARCHAR` with a CHECK constraint, like `locations.province` today. No MySQL `ENUM`. |
| B-07 | Private room with no owner | Old data may have one. Booking it → `409 ROOM_NOT_BOOKABLE`, "This private room has no owner yet." |
| B-08 | Cannot see → 404 | A user who may not see a booking gets `404 NOT_FOUND` (not 403), so ids do not leak. A user who may see it but may not do the action gets `403 FORBIDDEN` (cancel by Pitika, owner, Admin). |
| B-09 | Owner approves after start | Refused with `409 TIME_PASSED`, the same as Pitika (BR-APR-03). Reject is still allowed. |
| B-10 | Completed | `display_status` is computed: CONFIRMED and now ≥ end of last session → `COMPLETED`. List filters `?status=` use `display_status`, so `CONFIRMED` means "confirmed, not yet completed". |
| B-11 | Cancel / reject keeps rows | Cancel and reject set every session `is_blocking = false`. The food order and IT ticket rows stay (history); lists hide them by booking status. |
| B-12 | Food list | `/pitika/catering` shows bookings in SETUP_IN_PROGRESS or CONFIRMED whose first session is on that date. Admin may call it too and sees every province. Default date = today. |
| B-13 | Catalog edit | `catering_packages` and `it_services` PATCH needs `version` → `STALE_VERSION` if old. Names are unique (`409 DUPLICATE`). Non-Admins see only active rows. |
| B-14 | Private → shared | Refused while the room has PENDING_OWNER bookings, or R2 bookings still PENDING_PITIKA (they would reach an owner step on a shared room), with a new code `409 HAS_PENDING_OWNER_BOOKINGS`. |
| B-15 | PATCH refused fields | `private_justification` is also refused with `FIELD_NOT_EDITABLE`. Sending `catering` when the booking has no food order (or `it` with no IT ticket) → `FIELD_NOT_EDITABLE`. |
| B-16 | Session index in errors | 0-based, the same as pydantic: `sessions.0.start_time`. |
| B-17 | Local datetimes in responses | Local values go out as `date` ("2026-11-10") + `time` ("09:00") pairs. Stored UTC datetimes go out with a `Z`, as today. |
| B-18 | ics | Hand-written text. Times in UTC with `Z`. One VEVENT per session. |
| B-19 | IT body version | `PUT /it/tickets/{id}/staff` and `POST /it/tickets/{id}/ready` send the **booking's** version. Assigning staff raises the booking version. |
| B-21 | Moving a place | Moving a room to another floor, a floor to another building, a building to another office, or changing an office's province is refused while it has future bookings (`409 HAS_FUTURE_BOOKINGS`). Otherwise waiting bookings could move to another Pitika's province, or to one with no Pitika. |
| B-22 | Inactive IT Staff | Turning off an IT Staff user is not blocked. Ready needs at least one **active** assigned IT Staff, else `409 INVALID_TRANSITION` "Assign active IT Staff first." Lists show inactive staff with `is_active: false`. |
| B-23 | Booker's own email | If the booker puts their own email in `participant_emails`, it is removed (they are already counted as the "+1"). |
| B-24 | Empty PATCH | A PATCH with only `version` changes nothing and does not raise the version. |
| B-25 | Food after edit | Servings always = current attendees. A small edit that changes attendees changes the servings, with no new Pitika approval (BR-EDT-02). |
| B-26 | One person, two rooms | A user may book two rooms at the same time. Clash checks are per room only. |
| B-27 | Booker turned off | When the Admin turns a user off, every booking of theirs that is not final and not ended becomes CANCELLED in the same transaction: `cancel_reason` "Cancelled: the booker's account was turned off.", sessions stop blocking (decided Nov 3, 2026). The answer of `PATCH /users/{id}` gets a new list `bookings_cancelled: [ids]`. |
| B-28 | Reference code | **Changes the requirements** (glossary: "NBC-" and 5 digits). The format is `NBC-YY-NNNNN`, e.g. `NBC-26-48213`: 90,000 codes per year, so they never run out (decided Nov 3, 2026). The door pass keeps `NBC-` + 5 digits. |
| B-29 | Waiting bookings | No limit per person on waiting bookings or rooms held at one time. Pitika rejects bookings that look wrong (decided Nov 3, 2026). |
| B-20 | Self-approval | A Pitika may approve or reject their own booking (decided Nov 3, 2026). The same holds for a room owner on an R2 booking they made before they became the owner. No extra check. |
| B-30 | Masking by route | A booking is private when the room is private now **or** the booking's route is not R1 (it was made while the room was private). So a room that turns shared does not show its old private bookings: the schedule and the clash message still show `Reserved (Private Session)` to those who cannot view them. One helper, `booking_access.is_private_booking`, decides it everywhere. |
| B-31 | Loaded for write | Every booking write (edit, cancel, Pitika and owner approve/reject, IT assign and ready) reads the booking row `FOR UPDATE` with fresh values (`load_booking_for_write`) before `check_version`. A second request at the same version waits, then sees the new version and gets `409 STALE_VERSION` before it writes any child row (no duplicate-key 500). The visibility rules stay (hidden bookings are still 404). Room changes and new bookings lock the room row the same way. |
| B-32 | Admin list | `GET /bookings` lists every booking for the Admin, with the Pitika list's filters plus `province` (section 9.5b). Read only: the Admin still cannot approve, reject, cancel or edit (decided Nov 4, 2026, for the admin dashboard). |
| B-33 | Admin cancel | **Changes the requirements** (section 1, "Cancelling another person's booking"). The Admin may cancel any booking that is not final and not ended (D-32 B), reason optional (D-35 B), with the same effects as a booker's cancel (D-38 A). `POST /admin/bookings/{id}/cancel` (decided Nov 4, 2026). |
| B-34 | Admin as backup reviewer | The Admin may approve or reject a PENDING_PITIKA booking only when the room's province has no active Pitika (D-33 C; else 403 FORBIDDEN "This office has an active Pitika. Ask them to decide."), and any PENDING_OWNER booking (D-34 B). Same time rules as everyone (D-37 A). No Admin IT steps (D-40 A). A reject with no reason saves "Rejected by the Admin.". `GET /admin/bookings/{id}/actions`, `POST …/approve`, `POST …/reject`. |
| B-35 | Who acted | `bookings.cancelled_by` (the booker or Admin; null for the system, B-27); `booking_reviews.by_admin` and `booking_rejections.by_admin` mark Admin decisions, with the Admin in `reviewer_id` / `actor_user_id` (D-36 A). |
| B-36 | No notification | The booker sees an Admin action when they open the booking (D-39 A). |

## 3. File map

### 3.1 New files

| File | What is in it |
|---|---|
| `app/constants/booking.py` | StrEnums: BookingStatus, DisplayStatus, MeetingType, ReviewStage, ReviewDecision, RejectedBy, ITStatus, BookingRoute, BookingStep. Fixed texts (masked title, expiry reason). |
| `app/models/booking.py` | `Booking` |
| `app/models/booking_session.py` | `BookingSession` |
| `app/models/booking_review.py` | `BookingReview` |
| `app/models/booking_rejection.py` | `BookingRejection` |
| `app/models/booking_door_pass.py` | `BookingDoorPass` |
| `app/models/booking_participant.py` | `BookingParticipant` |
| `app/models/catering_order.py` | `CateringOrder` |
| `app/models/it_ticket.py` | `ITTicket` |
| `app/models/it_ticket_staff.py` | `it_ticket_staff` (a `Table`, like `user_roles`) |
| `app/models/catering_package.py` | `CateringPackage` |
| `app/models/it_service.py` | `ITService` |
| `app/models/public_holiday.py` | `PublicHoliday` |
| `alembic/versions/e4b7c2a9f310_add_booking_tables.py` | One migration, down_revision `d5a8c3e17f42` |
| `app/schemas/booking.py` | Create, check, patch, cancel bodies; detail, list item, check result, door pass, warnings |
| `app/schemas/booking_review.py` | Approve and reject bodies (Pitika and owner share them) |
| `app/schemas/room_schedule.py` | Schedule item |
| `app/schemas/it_ticket.py` | Staff body, ready body, ticket item |
| `app/schemas/catering_order.py` | Food list item |
| `app/schemas/catering_package.py`, `it_service.py`, `public_holiday.py` | Catalog create, update, out |
| `app/services/clock.py` | `now_utc()`, `now_local()`, `local_to_utc()` |
| `app/services/booking_access.py` | Who may see / act on a booking; masking |
| `app/services/booking_scheduling.py` | Session checks, clash check, route, holiday and capacity warnings |
| `app/services/booking_codes.py` | Reference code and door pass code |
| `app/services/booking_transitions.py` | `advance()` (the version check), side effects: reject, confirm, forward IT |
| `app/services/booking.py` | Check, create, read, list mine, edit, cancel, door pass |
| `app/services/booking_review.py` | Pitika and owner lists, approve, reject |
| `app/services/booking_ics.py` | The calendar file |
| `app/services/booking_expiry.py` | `run_once(session)`: T15 and T17 |
| `app/services/room_schedule.py` | The schedule of one room |
| `app/services/room_bookings.py` | Guards for section 10 (counts only; imports models, clock, errors and constants only, so `room.py` and `user.py` can use it) |
| `app/services/it_ticket.py` | List, assign staff, ready |
| `app/services/catering_order.py` | The day's food list |
| `app/services/catering_package.py`, `it_service.py`, `public_holiday.py` | Catalog CRUD |
| `app/expiry_runner.py` | The thread and the MySQL lock (B-03) |
| `app/routers/bookings.py` | `/bookings…` |
| `app/routers/room_schedule.py` | `/rooms/{id}/schedule` |
| `app/routers/pitika_bookings.py` | `/pitika/bookings…` |
| `app/routers/catering_orders.py` | `/pitika/catering` |
| `app/routers/owner_bookings.py` | `/owner/bookings…` |
| `app/routers/it_tickets.py` | `/it/tickets…` |
| `app/routers/catering_packages.py`, `it_services.py`, `public_holidays.py` | Catalogs |
| `scripts/run_expiry.py` | Runs `run_once` one time and prints the result |

### 3.2 Changed files

| File | Change |
|---|---|
| `app/config.py` | Booking settings (section 4) |
| `app/errors.py` | New error codes (section 13); update the docstring "Do not add others" to name both specs |
| `app/models/__init__.py` | Export the new models |
| `app/models/room.py` | Comment on `is_private`: no longer "a label only"; it picks the route and needs an owner |
| `app/schemas/room.py` | Same comment fix |
| `app/security.py` | Aliases: `PitikaUser`, `RoomOwnerUser`, `ITLeadUser`, `ITUser` (IT_LEAD or IT_STAFF), `PitikaOrAdminUser` |
| `app/main.py` | Include new routers; a `lifespan` that starts and stops the expiry runner when `settings.expiry_job_enabled` |
| `app/services/room.py` | OWNER_REQUIRED, HAS_PENDING_OWNER_BOOKINGS, HAS_FUTURE_BOOKINGS (section 12) |
| `app/services/floor.py`, `building.py`, `location.py` | HAS_FUTURE_BOOKINGS when turned off |
| `app/services/user.py` | OWNER_HAS_PRIVATE_ROOMS; R9 now clears **shared** rooms only; turning a user off cancels their bookings (B-27) |
| `app/schemas/user.py`, `app/routers/users.py` | `UserChanged.bookings_cancelled: list[int]` (B-27) |
| `tests/conftest.py` | `expiry_job_enabled=False` in the `settings` fixture; new factory fixtures; `freeze_now` fixture |
| `tests/factories.py` | New factories (section 14.1) |
| `tests/test_migrations.py` | `ALL_TABLES` + 12 tables; rename `test_models_define_the_14_spec_tables` |
| `tests/test_schema.py` | `EXPECTED_COLUMNS` for the 12 new tables |
| `.env.example` | The new settings with their defaults |

## 4. Settings

Add to `Settings` in `app/config.py` (D-14: numbers are settings, not code):

| Setting | Default | Used by |
|---|---|---|
| `booking_min_minutes` | 15 | BR-SCH-02 |
| `booking_max_sessions` | 20 | BR-SCH-10 |
| `booking_max_days_ahead` | 90 | BR-SCH-10 |
| `booking_max_attendees` | 100 | BR-FRM-03 |
| `booking_max_participants` | 50 | BR-FRM-05 |
| `schedule_max_days` | 31 | `/rooms/{id}/schedule` |
| `it_setup_lead_minutes` | 30 | BR-IT-05 |
| `expiry_job_enabled` | true | B-03 |
| `expiry_interval_seconds` | 60 | B-03 |

All `Field(ge=1)` except `expiry_job_enabled` (bool). Services read them from the `Settings` passed in by the router (`AppSettings` dependency), never from `get_settings()`.

Because these limits are settings, the schemas do **not** hard-code them. The service checks them and raises `422 VALIDATION_ERROR` with `fields`, the same shape pydantic errors have.

## 5. Time and clock

`app/services/clock.py`:

```python
LOCAL_OFFSET = timedelta(hours=7)  # Phnom Penh, no daylight saving

def now_utc() -> datetime: ...      # naive UTC, whole seconds (same as models.base.utcnow)
def now_local() -> datetime: ...    # now_utc() + LOCAL_OFFSET
def local_to_utc(value: datetime) -> datetime: ...
def session_start(s) -> datetime    # datetime.combine(s.date, s.start_time), local
def session_end(s) -> datetime
```

`now_utc` reads a module-level `_source` callable. The test fixture `freeze_now(local_dt)` monkeypatches `_source` so `now_local()` returns `local_dt`.

Words used below:

- **first start** = local start of the first session (by date, then start time).
- **last end** = local end of the last session (by date, then end time).
- **started** = `now_local() >= first start`. **ended** = `now_local() >= last end`.
- **today** = `now_local().date()`.

## 6. Constants and enums

`app/constants/booking.py` (StrEnum each, values as in requirements 6.1):

- `BookingStatus`: PENDING_PITIKA, PENDING_OWNER, SETUP_IN_PROGRESS, CONFIRMED, REJECTED, CANCELLED. Helpers: `FINAL = {REJECTED, CANCELLED}`, `PENDING = {PENDING_PITIKA, PENDING_OWNER}`.
- `DisplayStatus`: the six + COMPLETED.
- `MeetingType`, `ReviewStage`, `ReviewDecision`, `RejectedBy`, `ITStatus`, `BookingRoute` as in 6.1.
- `BookingStep`: PITIKA, OWNER, IT_SETUP, CONFIRMED (used in the check answer).
- `MASKED_TITLE = "Reserved (Private Session)"`
- `EXPIRY_REASON = "Expired: not approved before the meeting time."`
- `REFERENCE_PREFIX = "NBC-"`

## 7. Data model and migration

Common: every table uses `MYSQL_TABLE`, `IdMixin` (unsigned int id), FKs `ondelete="RESTRICT", onupdate="RESTRICT"`, the naming convention in `Base`. `TimestampMixin` where the requirements say timestamps. Datetimes are naive UTC except where marked **local**. String enum columns are `String(20)` + `CheckConstraint("<col> IN (...)")`.

### 7.1 Catalogs

**catering_packages** — `IdMixin, ActiveMixin, SortOrderMixin, TimestampMixin`

| Column | Type | Null | Notes |
|---|---|---|---|
| name | String(200) | no | Unique |
| description | String(1000) | yes | |
| version | Integer, default 1 | no | |

**it_services** — same columns as catering_packages.

**public_holidays** — `IdMixin, TimestampMixin`

| Column | Type | Null | Notes |
|---|---|---|---|
| holiday_date | Date | no | Unique |
| name_km | String(255) | no | |
| name_en | String(255) | yes | |
| remarks | String(1000) | yes | |

### 7.2 bookings — `IdMixin, TimestampMixin`

| Column | Type | Null | Notes |
|---|---|---|---|
| reference_code | String(20) | no | Unique |
| requester_id | FK users | no | Index |
| room_id | FK rooms | no | Index |
| requester_info | JSON | no | BR-FRM-06, see 8.4 |
| meeting_title | String(200) | no | |
| meeting_type | String(30) | no | CHECK MeetingType |
| meeting_purpose | String(1000) | yes | |
| attendees | Integer unsigned | no | CHECK `attendees >= 1` |
| private_justification | String(1000) | yes | |
| route | String(2) | no | CHECK BookingRoute |
| status | String(20) | no | CHECK BookingStatus, index |
| cancelled_at | DateTime | yes | |
| cancel_reason | String(500) | yes | |
| version | Integer unsigned, default 1 | no | |

### 7.3 booking_sessions — `IdMixin`

| Column | Type | Null | Notes |
|---|---|---|---|
| booking_id | FK bookings | no | Index |
| room_id | FK rooms | no | B-05, copy of `bookings.room_id` |
| date | Date | no | **local** |
| start_time | Time | no | **local** |
| end_time | Time | no | **local**; CHECK `start_time < end_time` |
| is_blocking | Boolean, default true | no | |

Index `(room_id, date, is_blocking)`.

### 7.4 Review and access

**booking_reviews** — `IdMixin`: booking_id FK (index), stage String(10) CHECK, decision String(15) CHECK, reviewer_id FK users **null** (null for NOT_REQUIRED), notes String(1000) null, reviewed_at DateTime.

**booking_rejections** — `IdMixin`: booking_id FK **unique**, rejected_by String(10) CHECK, actor_user_id FK users **null** (D-29), reason String(1000), decided_at DateTime.

**booking_door_passes** — `IdMixin`: booking_id FK **unique**, passcode String(10) (index, not unique: old passes may repeat), expires_at DateTime (UTC of last end).

**booking_participants** — `IdMixin`: booking_id FK, email String(254). Unique `(booking_id, email)`.

### 7.5 Services

**catering_orders** — `IdMixin, TimestampMixin`: booking_id FK **unique**, packages JSON (`[{id, name}]`), remarks String(1000) null, approver_notes String(1000) null, decided_by FK users null, decided_at DateTime null.

**it_tickets** — `IdMixin, TimestampMixin`: booking_id FK **unique**, requested_items JSON (`[{id, name}]`), special_requirements String(1000) null, status String(10) CHECK ITStatus default RECEIVED, technician_notes String(1000) null, forwarded_at / assigned_at / ready_at DateTime null.

**it_ticket_staff** — `Table`: ticket_id FK it_tickets, user_id FK users (index); composite primary key `(ticket_id, user_id)`.

### 7.6 Migration

- One file `e4b7c2a9f310_add_booking_tables.py`. `upgrade()` creates the 12 tables in FK order: catalogs, holidays, bookings, sessions, reviews, rejections, door passes, participants, catering_orders, it_tickets, it_ticket_staff. `downgrade()` drops them in reverse.
- No data change. Old private rooms with no owner stay (B-07).
- `test_migrations_match_the_models` must stay green (`compare_type=True`), so the model and migration types match exactly.

## 8. Shared services

### 8.1 Access — `app/services/booking_access.py`

```python
def can_view(session, current: CurrentUser, booking: Booking) -> bool
def can_see_door_pass(session, current, booking) -> bool
def load_visible_booking(session, current, booking_id, *, for_write=False) -> Booking
    # 404 if missing or not can_view; for_write=True reads it with load_booking_for_write
def load_booking_for_write(session, booking_id) -> Booking
    # FOR UPDATE + populate_existing, 404 if missing (B-31)
def is_private_booking(booking) -> bool   # room private now, or route != R1 (B-30)
def pitika_province(current) -> str | None                          # get_user_province(user).code
```

`can_view` is true when any of these is true (requirements section 3):

| Who | Condition |
|---|---|
| Booker | `booking.requester_id == current.id` |
| Admin | has ADMIN |
| Room owner | `booking.room.room_owner_id == current.id` |
| Pitika | has PITIKA and `pitika_province(current) == room province` |
| IT Lead | has IT_LEAD and the booking has an IT ticket with `forwarded_at` set |
| IT Staff | has IT_STAFF and is in `it_ticket_staff` for this booking's ticket |

`can_see_door_pass`: booking is CONFIRMED and (booker, Admin, room owner, or Pitika of the province). IT roles: no.

**Masking** (BR-PRV-01, BR-PRV-02, B-30): a booking is masked when the room is private now or the booking's route is not R1 (`is_private_booking`), and the user cannot `can_view` it. `visible_title(session, current, booking) -> str` gives `MASKED_TITLE` for a masked booking, else the real title. The schedule decides `masked` once per item and takes the title from it. R1 bookings in a shared room are never masked.

### 8.2 Scheduling — `app/services/booking_scheduling.py`

Pure checks get plain data (sessions as a list of `{date, start_time, end_time}`), the room, `settings` and `now_local`, so they are easy to unit-test.

```python
def check_session_shapes(sessions, settings, today) -> None        # 422
def check_room_bookable(room) -> None                               # 409 ROOM_NOT_BOOKABLE
def check_room_hours(sessions, room) -> None                        # 422 OUTSIDE_ROOM_HOURS
def check_not_past(sessions, now_local) -> None                     # 409 TIME_PASSED
def pick_route(room, booker_id, has_catering, has_it) -> BookingRoute
def check_reviewer(session, room, route) -> None                    # 409 NO_REVIEWER
def check_clashes(session, current, room, sessions) -> None         # 409 SCHEDULE_CONFLICT
def warnings_for(session, room, sessions, attendees) -> list[dict]
def steps_for(route, has_it) -> list[BookingStep]
```

**check_session_shapes** (in this order, first error wins, field names 0-based):

1. `1 <= len(sessions) <= booking_max_sessions` → `sessions`: "Add 1 to 20 sessions."
2. For each i: `end_time > start_time` → `sessions.i.end_time`: "End must be after start."
3. For each i: minutes ≥ `booking_min_minutes` → `sessions.i.end_time`: "A session is at least 15 minutes."
4. For each i: `date <= today + booking_max_days_ahead` → `sessions.i.date`: "You can book at most 90 days ahead."
5. Overlap inside the booking (BR-SCH-06): sort by (date, start); for each pair on the same date with `a.start < b.end and a.end > b.start` → `sessions.j.start_time`: "This session overlaps session {i+1}." (j = the later one's original index.)

**check_room_bookable**: `room_service.is_bookable(room)` false → 409 "This room cannot be booked right now." Private room with no owner → 409 "This private room has no owner yet." (B-07).

**check_room_hours**: each `room.start_time <= start` and `end <= room.end_time`, else `422 OUTSIDE_ROOM_HOURS`, message "This room is open from 08:00 to 17:00." (real hours), field `sessions.i.start_time` or `.end_time`.

**check_not_past** (BR-SCH-03): `session_start(s) < now_local` → `409 TIME_PASSED`, "This session starts at 09:00, which has passed.", field `sessions.i.start_time`. A start equal to now is allowed.

**pick_route** (requirements section 4):

```
if not room.is_private:                         R1
elif room.room_owner_id != booker_id:           R2
elif has_catering or has_it:                    R4
else:                                           R3
```

**check_reviewer** (BR-SCH-13): for R1, R2, R4, count active users with role PITIKA whose division → department → location has the room's province. 0 → `409 NO_REVIEWER`, "No reviewer for this office yet." R3 skips it.

**check_clashes** (BR-SCH-04, 05, BR-PRV-02): for each session i, in order, find one blocking session `x` with `x.room_id = room.id AND x.date = s.date AND x.is_blocking AND s.start < x.end_time AND s.end > x.start_time`. Exclude sessions of the same booking (not needed on create; kept for safety). First hit → `409 SCHEDULE_CONFLICT`, message `"This room is already booked from {x.start} to {x.end} for {visible_title}."`, field `sessions.i`.

**warnings_for**:

- One `{"code": "PUBLIC_HOLIDAY", "date": "2026-11-09", "name": "<name_en or name_km>"}` per distinct session date that is in `public_holidays` (BR-HOL-02).
- `{"code": "OVER_CAPACITY", "seats": room.capacity, "attendees": n}` when `attendees > room.capacity` (BR-FRM-04). Only when attendees is known (not in `/bookings/check`).

**steps_for**: R1 → [PITIKA], R2 → [PITIKA, OWNER], R3 → [], R4 → [PITIKA]; then add IT_SETUP if `has_it` and route ≠ R3; then CONFIRMED.

### 8.3 Codes — `app/services/booking_codes.py`

- `new_reference_code(session)`: `f"NBC-{yy}-{secrets.randbelow(90000) + 10000}"`, where `yy` = the last 2 digits of the local year when the booking is sent, e.g. `NBC-26-48213` (B-28); loop until no booking has it (max 20 tries, then raise `RuntimeError`). The unique key is the last guard: the create flushes the booking inside `session.begin_nested()`; on a duplicate-key error, pick a new code and try again (max 3).
- `new_door_pass(session, booking, expires_at)`: same format (BR-DP-01); loop until the code is not equal to `booking.reference_code` and no door pass with `expires_at > now_utc()` has it.

### 8.4 requester_info (BR-FRM-06)

Built at send from the booker:

```json
{"name_en": "...", "name_kh": "...", "staff_id": "...", "position": "<position.name_en>",
 "division": "<name_en or null>", "department": "<name_en or null>",
 "office": "<location.name_en or null>", "email": "...", "phone": "<or null>"}
```

### 8.5 Transitions — `app/services/booking_transitions.py`

All status moves go through these. Nothing else writes `bookings.status`.

```python
def check_version(booking, version) -> None
    # booking.version != version → 409 STALE_VERSION "This booking changed. Reload it."

def advance(session, booking, version, **values) -> None
    # UPDATE bookings SET <values>, version = version + 1, updated_at = now_utc()
    #   WHERE id = :id AND version = :version
    # rowcount 0 → 409 STALE_VERSION. Then session.refresh(booking).

def invalid(message) -> AppError        # 409 INVALID_TRANSITION
def stop_blocking(session, booking)     # UPDATE booking_sessions SET is_blocking = 0 WHERE booking_id
def cancel(session, booking, version, reason)
    # advance(status=CANCELLED, cancelled_at=now_utc(), cancel_reason=reason); stop_blocking
def reject(session, booking, version, by: RejectedBy, actor_id | None, reason, stage | None)
    # advance(status=REJECTED); stop_blocking; insert booking_rejections;
    # if stage: insert booking_reviews(stage, REJECTED, actor, notes=reason)
def make_confirmed(session, booking, version)
    # advance(status=CONFIRMED); insert door pass (expires_at = local_to_utc(last end))
def forward_it(session, booking, version)
    # advance(status=SETUP_IN_PROGRESS); ticket.forwarded_at = now_utc()
def after_last_review(session, booking, version)
    # has IT ticket → forward_it, else make_confirmed
```

Order of checks in every action endpoint:

1. Role (router dependency) → 403.
2. Booking visible to this user (`load_visible_booking` or the queue's own scope) → 404.
3. Actor allowed for this action (e.g. only the booker cancels) → 403.
4. `check_version` → 409 STALE_VERSION.
5. Status allowed (transition table) → 409 INVALID_TRANSITION. Messages by current status: "This booking is already confirmed.", "This booking is waiting for the room owner.", "This booking was rejected.", "This booking was cancelled.", "This booking is completed.", "This booking is in IT setup."
6. Time rules → 409 TIME_PASSED.
7. Body rules → 422.
8. Write with `advance` (second version guard), commit.

## 9. Endpoints

All under `/api/v1`. Lists: `PageParams`, answer `Page[...]`. Every body is a `RequestModel` (unknown fields refused). Text uses `Text` / `OptionalText` (trimmed). "HTML is never accepted" (requirements 7.11): add a validator `NoHtml` to `schemas/common.py` that refuses `<` followed by a letter, `/` or `!` → "HTML is not allowed." Use it on every free-text booking field.

### 9.1 Response shapes — `app/schemas/booking.py`

`SessionOut`: `id, date, start_time (LocalTime), end_time (LocalTime)`.

`BookingRoomRef`: `id, name_en, name_kh, is_private, location: NamedRef, province: ProvinceRef`.

`BookingListItem`:

```
id, reference_code, room: BookingRoomRef, meeting_title, meeting_type, route,
status, display_status, requester: {id, name_en, name_kh},
first_session: SessionOut, session_count, attendees,
has_catering, has_it, created_at (UtcDateTime), version
```

`BookingDetail` = list item fields +

```
requester_info, meeting_purpose, private_justification, participant_emails: [str],
sessions: [SessionOut], last_end: {date, time},
catering: null | {packages, remarks, servings (= attendees), delivery_date, delivery_time,
                  approver_notes, decided_by: {id, name_en} | null, decided_at},
it: null | {ticket_id, items, special_requirements, status, technician_notes,
            staff: [{id, name_en, name_kh}], setup_date, setup_time,
            forwarded_at, assigned_at, ready_at},
reviews: [{stage, decision, reviewer: {id, name_en} | null, notes, reviewed_at}],
rejection: null | {rejected_by, actor: {id, name_en} | null, reason, decided_at},
cancelled_at, cancel_reason, updated_at
```

`BookingSaved` = `BookingDetail` + `warnings: [dict]` (create and PATCH answers).

`setup_*` = first start − `it_setup_lead_minutes` (BR-IT-05). `display_status` per B-10.

### 9.2 `GET /rooms/{id}/schedule?from=&to=` — router `room_schedule.py`

- Any signed-in user. Room 404 if missing (inactive rooms still answer).
- `from`, `to`: dates. Default `from` = today, `to` = from + 6 days. `to < from` → 422 `to`. More than `schedule_max_days` days (inclusive) → 422 `to`: "At most 31 days."
- Items: every blocking session of the room in the range, sorted by date, start.
- `ScheduleItem`: `date, start_time, end_time, booking_id | null, reference_code | null, title, requester_name | null, status, is_masked`. Masked items (8.1) have `booking_id`, `reference_code`, `requester_name` = null and `title = MASKED_TITLE`.
- Answer `{"items": [...], "total": n}` (`ItemList`).

### 9.3 `POST /bookings/check`

Body `BookingCheck`: `room_id: RefId`, `sessions: list[SessionIn]` (`date: date`, `start_time`, `end_time`: `LocalTime`), `has_catering: bool = False`, `has_it: bool = False`.

Runs, in order: `check_session_shapes`, room lookup (422 `room_id` "Room not found."), `check_room_bookable`, `check_room_hours`, `check_not_past`, `pick_route`, `check_reviewer`, `check_clashes`. Saves nothing; no lock.

- Pydantic shape errors (bad time, missing field) → normal 422.
- A rule error is **not** raised. It is put in the answer:

```json
{"route": "R2", "first_status": "PENDING_PITIKA",
 "steps": ["PITIKA", "OWNER", "IT_SETUP", "CONFIRMED"],
 "problem": {"code": "SCHEDULE_CONFLICT", "message": "...", "fields": {"sessions.1": "..."}},
 "warnings": [{"code": "PUBLIC_HOLIDAY", "date": "2026-11-09", "name": "Independence Day"}]}
```

`route`, `first_status`, `steps` are null when the problem stops them (room not found / not bookable). 200 always for rule problems.

### 9.4 `POST /bookings` (T1, T2)

Body `BookingCreate` (requirements 8.1 example):

```
room_id: RefId
sessions: list[SessionIn]
meeting_title: Text(200), 3+ letters
meeting_type: MeetingType
meeting_purpose: OptionalText(1000)
attendees: int
participant_emails: list[Email] = []
private_justification: OptionalText(1000) = None
catering: null | {package_ids: list[RefId] (min 1), remarks: OptionalText(1000)}
it: null | {service_ids: list[RefId] (min 1), special_requirements: OptionalText(1000)}
```

Steps in `booking_service.create_booking(session, current, body, settings)`:

1. `check_session_shapes`.
2. Attendees `1..booking_max_attendees` → 422 `attendees`. Participant emails: drop repeats (lowercase already) and the booker's own email (B-23), more than `booking_max_participants` → 422 `participant_emails`. `attendees >= len(emails) + 1` → else 422 `attendees`: "Attendees must be at least the participants plus you."
3. Room: `session.get(Room)`; missing → 422 `room_id`. `check_room_bookable`, `check_room_hours`, `check_not_past`.
4. `route = pick_route(...)`; `check_reviewer`.
5. Route R2 and no justification → 422 `private_justification`: "Explain why you need this private room." (BR-FRM-07). Other routes: keep it if sent.
6. Catalogs: each package / service id must exist (422 `catering.package_ids`: "Package not found.") and be active (409 INACTIVE_REFERENCE). Repeated ids are dropped.
7. **Lock**: `SELECT … FROM rooms WHERE id = :id FOR UPDATE` (BR-SCH-08). Then `check_clashes`.
8. Insert: booking (status PENDING_PITIKA, or CONFIRMED for R3), sessions (`room_id` copied, blocking), participants, catering order (packages copy `[{id, name}]`), IT ticket (items copy, status RECEIVED, `forwarded_at` null).
9. R3 only (T2): one `booking_reviews` row `(PITIKA, NOT_REQUIRED, reviewer null)` and the door pass.
10. Commit. Answer `201 BookingSaved` with `warnings_for(...)`.

### 9.5 `GET /bookings/mine?status=&q=`

The current user's bookings. `status` = a `DisplayStatus` value (422 if not). `q` matches `meeting_title` or `reference_code` (`apply_search`). Sort `created_at desc, id desc`.

### 9.5b `GET /bookings?status=&province=&from=&to=&room_id=&q=` (B-32)

Admin only (`AdminUser`, others 403). Every booking, or those of rooms in `province`. Same filters, search and sort as the Pitika list (9.11): `status` = a `DisplayStatus` (422 if not), `from`/`to` keep bookings with any session in the range, `q` matches title, reference code and booker name. Sort by first start, then id. Item: `BookingListItem`. `booking_review.list_admin_bookings` shares `_list_in_rooms` with the Pitika and owner lists.

### 9.6 `GET /bookings/{id}`

`load_visible_booking` → `BookingDetail`.

### 9.7 `PATCH /bookings/{id}` (T13)

Body `BookingUpdate`: `version: int` (required) + optional `meeting_title, meeting_type, meeting_purpose, attendees, participant_emails, catering: {remarks}, it: {special_requirements}`. The model also declares `room_id, sessions, private_justification: Any = None`, and the nested models declare `package_ids` / `service_ids: Any = None`, so the service can answer the right code.

Checks: visible (404) → booker only (403) → any refused field set → `422 FIELD_NOT_EDITABLE` "To change the room, date or time, cancel and book again." (BR-EDT-03, B-15) → version → not final (409) and not completed → not started (409 TIME_PASSED "The meeting has started. It cannot be changed.") → attendees / emails rules as 9.4 step 2 (using the new or old values) → write.

Write: plain ORM changes, participants replaced when sent, then `advance(session, booking, version)` with no status change (raises version). A body with only `version` writes nothing (B-24). Answer `BookingSaved` (OVER_CAPACITY warning if any). Status never changes.

### 9.8 `POST /bookings/{id}/cancel` (T12)

Body: `reason: OptionalText(500)` (5+ letters when given), `version`.

Checks: visible (404) → booker only (403 "Only the booker can cancel. Reject it instead.") → version → not final (409) → not ended (409 INVALID_TRANSITION "This booking has ended.").

Write: `advance(status=CANCELLED, cancelled_at=now_utc(), cancel_reason=reason)`, `stop_blocking`. Answer `BookingDetail`.

### 9.9 `GET /bookings/{id}/door-pass`

Visible (404) → `can_see_door_pass` false: not confirmed → 404 "No door pass yet."; confirmed but wrong user → 403. Answer `{"passcode": "NBC-48213", "expires_at": "…Z", "expired": now_utc() >= expires_at}` (BR-DP-03).

### 9.10 `GET /bookings/{id}/ics` — `booking_ics.py`

Visible (404). `Content-Type: text/calendar; charset=utf-8`, `Content-Disposition: attachment; filename="<reference_code>.ics"`.

```
BEGIN:VCALENDAR / VERSION:2.0 / PRODID:-//NBC//Room Booking//EN / METHOD:PUBLISH
per session:
  BEGIN:VEVENT
  UID:booking-<id>-session-<session id>@nbc-room-booking
  DTSTAMP:<now_utc>Z
  DTSTART:<local_to_utc(start)>Z  DTEND:<…>Z
  SUMMARY:<title>  LOCATION:<room name_en>, <building>, <location>
  DESCRIPTION:Reference <code>
  STATUS:CONFIRMED | TENTATIVE (pending/setup) | CANCELLED (rejected/cancelled)
  END:VEVENT
END:VCALENDAR
```

Lines end with `\r\n`. Escape `\`, `;`, `,`, newline. Fold lines longer than 75 bytes. No door pass in the file.

### 9.11 Pitika — `pitika_bookings.py`, role PITIKA

`GET /pitika/bookings?status=&from=&to=&room_id=&q=`: bookings whose room province = the Pitika's province (no province → empty list). `from`/`to` keep bookings with any session date in the range. `q`: title, reference code, requester name (join users). Sort: first start asc, id asc. Item: `BookingListItem`.

`POST /pitika/bookings/{id}/approve` — body `notes: OptionalText(1000), version`:

Booking in province (else 404) → version → status PENDING_PITIKA (else INVALID_TRANSITION) → not started (409 TIME_PASSED, BR-APR-03) → write:

- insert review `(PITIKA, APPROVED, current, notes)`;
- catering order (if any): `decided_by = current`, `decided_at = now_utc()`, `approver_notes = notes` (BR-APR-06, 07);
- route R2 → `advance(status=PENDING_OWNER)` (T3, BR-APR-04); else `after_last_review` (T4/T5).

`POST /pitika/bookings/{id}/reject` — body `reason: Text 5..1000, version` → in province → version → PENDING_PITIKA → `reject(by=PITIKA, stage=PITIKA)` (T6). No time check.

### 9.12 Food list — `catering_orders.py`, role PITIKA or ADMIN

`GET /pitika/catering?date=` (default today). B-12. Item: `booking_id, reference_code, booking_status, room: BookingRoomRef, meeting_title (masking does not apply; Pitika may see), delivery_date, delivery_time, servings, packages, remarks, approver_notes`. Sort by delivery time, room name. `ItemList`.

### 9.13 Room owner — `owner_bookings.py`, role ROOM_OWNER

`GET /owner/bookings?status=&room_id=&q=`: bookings in private rooms where `room_owner_id = current.id` **now** (BR-OWN-05: the queue follows the room). Sort as Pitika.

`POST /owner/bookings/{id}/approve` — body `notes, version` → own private room (else 404) → version → PENDING_OWNER → not started (B-09) → review `(OWNER, APPROVED)` → `after_last_review` (T7/T8).

`POST /owner/bookings/{id}/reject` — body `reason, version` → … → `reject(by=OWNER, stage=OWNER)` (T9).

### 9.14 IT — `it_tickets.py`

`GET /it/tickets?status=&q=` (IT_LEAD or IT_STAFF): tickets with `forwarded_at` set and booking not REJECTED / CANCELLED (BR-IT-01). IT Lead: all. IT Staff only: tickets they are assigned to (a user with both roles sees all). `status` = ITStatus. `q`: title, reference code. Sort by first start asc.

`ITTicketItem`: `id, status, items, special_requirements, technician_notes, staff, setup_date, setup_time, forwarded_at, assigned_at, ready_at, review_notes: [notes of APPROVED reviews] (BR-APR-07), booking: BookingListItem`.

`PUT /it/tickets/{id}/staff` (IT_LEAD) — body `user_ids: list[RefId]` (min 1), `technician_notes: OptionalText(1000)`, `version` (B-19):

Ticket forwarded and visible (else 404) → version → booking SETUP_IN_PROGRESS and ticket not READY (else INVALID_TRANSITION) → every user exists (422 `user_ids`) and is active with IT_STAFF (409 INACTIVE_REFERENCE, "This user is not active IT Staff.") → replace `it_ticket_staff` rows, `status = ASSIGNED`, `assigned_at = now_utc()`, notes → `advance(...)` (T10, BR-IT-02). Answer `ITTicketItem`.

`POST /it/tickets/{id}/ready` (IT_LEAD) — body `version` → visible → version → booking SETUP_IN_PROGRESS → ticket ASSIGNED with at least one active IT Staff (else INVALID_TRANSITION "Assign active IT Staff first.", B-22) → `ready_at`, `status = READY` → `make_confirmed` (T11).

IT Staff calling PUT / ready → 403 (BR-IT-04).

### 9.15 Catalogs and holidays

Same style as the current equipment / category routers.

| Path | GET (any user) | POST / PATCH / DELETE (Admin) |
|---|---|---|
| `/catering-packages` | Page; `is_active`, `search`; non-Admin sees active only | POST: `name` (2–200), `description`, `sort_order`, `is_active` |
| `/catering-packages/{id}` | — | PATCH: same fields + `version` (required) |
| `/it-services`, `/it-services/{id}` | same | same |
| `/public-holidays?year=` | Page sorted by date; `year` filter | POST: `holiday_date`, `name_km` (required), `name_en`, `remarks` |
| `/public-holidays/{id}` | — | PATCH; DELETE → 204 |

Duplicates → `409 DUPLICATE` via `records.save` (add messages: `holiday_date` → "This date already has a holiday."). Catalog PATCH raises `version` by 1; old version → STALE_VERSION. Turning a package or service off changes no booking (copies are saved).

## 10. Expiry job

### 10.1 Logic — `app/services/booking_expiry.py`

```python
def run_once(session) -> ExpiryResult   # rejected: list[int], confirmed: list[int]
```

1. Ids of bookings with status in (PENDING_PITIKA, PENDING_OWNER, SETUP_IN_PROGRESS) and `MIN(TIMESTAMP(date, start_time)) <= now_local` over their sessions.
2. For each id, in its own transaction: re-read the booking; skip if status changed.
   - Pending → `reject(by=SYSTEM, actor None, reason=EXPIRY_REASON, stage None)` (T15).
   - SETUP_IN_PROGRESS → `make_confirmed` (T17). The IT ticket is not changed.
   - Use the booking's current version. A STALE_VERSION here means a person acted first: roll back, skip, continue.
3. Log one line: counts and ids.

### 10.2 Runner — `app/expiry_runner.py`

- `ExpiryRunner(settings).start()` / `.stop()`. A daemon thread.
- Every `expiry_interval_seconds`: if it does not hold the lock, try `SELECT GET_LOCK('booking_expiry', 0)` on its own connection (kept open). With the lock: `run_once(SessionLocal())`. Any error: log it, keep looping.
- Wait with `threading.Event.wait(interval)` so `stop()` is quick. `stop()` releases the lock.
- `main.py`: a `lifespan` that starts it when `settings.expiry_job_enabled`, stops it on shutdown.

### 10.3 Script — `scripts/run_expiry.py`

`python -m scripts.run_expiry`: one `run_once`, prints "Rejected: n, confirmed: m". Exit 0.

## 11. Errors to add — `app/errors.py`

`SCHEDULE_CONFLICT, TIME_PASSED, OUTSIDE_ROOM_HOURS, ROOM_NOT_BOOKABLE, NO_REVIEWER, INVALID_TRANSITION, STALE_VERSION, FIELD_NOT_EDITABLE, OWNER_REQUIRED, OWNER_HAS_PRIVATE_ROOMS, HAS_FUTURE_BOOKINGS, HAS_PENDING_OWNER_BOOKINGS` (the last one is B-14). HTTP codes and messages as requirements section 9.

## 12. Changes to the current API (requirements section 10)

Helpers in `app/services/room_bookings.py` (imports models, clock, errors and constants only):

```python
def future_booking_count(session, room_ids) -> int
    # distinct bookings with a blocking session in these rooms
    # whose TIMESTAMP(date, end_time) > now_local
def pending_owner_count(session, room_id) -> int
    # PENDING_OWNER, plus PENDING_PITIKA with route R2 (B-14)
def private_room_ids_owned_by(session, user_id) -> list[int]
```

| Where | Change |
|---|---|
| `room.create_room`, `room.update_room` | Final state `is_private` and no owner → `422 OWNER_REQUIRED` "A private room needs an owner.", field `room_owner_id`. |
| `room.update_room` | `is_private` true → false and `pending_owner_count > 0` → `409 HAS_PENDING_OWNER_BOOKINGS` "Resolve 3 bookings waiting for the room owner first." |
| `room.update_room` | `is_active` true → false and `future_booking_count > 0` → `409 HAS_FUTURE_BOOKINGS` "This room has 3 future bookings. Ask the bookers to cancel first." |
| `floor`, `building`, `location` update | Turned off: same check over every room inside → "This floor has 3 future bookings. Ask the bookers to cancel first." (building / office) |
| `room`, `floor`, `building`, `location` update | Moved to another parent, or office `province` changed, with future bookings inside → `409 HAS_FUTURE_BOOKINGS` "This room has 3 future bookings. Move it after they end." (B-21) |
| `user.update_user` (turn off), `user.set_user_roles` (lose ROOM_OWNER) | Owns any private room → `409 OWNER_HAS_PRIVATE_ROOMS` "Assign a new owner for 2 private rooms first." (field `is_active` / `role_codes`). Otherwise `_clear_owned_rooms` as today (only shared rooms are left to clear). |
| `user.update_user` (turn off) | After the owner check passes: for each booking with `requester_id = user` that is not final and not ended → `advance(status=CANCELLED, cancelled_at, cancel_reason="Cancelled: the booker's account was turned off.")` + `stop_blocking`. Return the ids as `bookings_cancelled` (B-27). Turning the user on again restores nothing. |
| Owner change | Nothing to build (the owner queue reads `room_owner_id` at read time). Test it. |
| Seats / opening hours | No change. Test that old bookings stay. |

## 13. Security aliases — `app/security.py`

```python
PitikaUser = Annotated[CurrentUser, Depends(require_roles(RoleCode.PITIKA))]
RoomOwnerUser = Annotated[CurrentUser, Depends(require_roles(RoleCode.ROOM_OWNER))]
ITLeadUser = Annotated[CurrentUser, Depends(require_roles(RoleCode.IT_LEAD))]
ITUser = Annotated[CurrentUser, Depends(require_roles(RoleCode.IT_LEAD, RoleCode.IT_STAFF))]
PitikaOrAdminUser = Annotated[CurrentUser, Depends(require_roles(RoleCode.PITIKA, RoleCode.ADMIN))]
```

## 14. Tests

### 14.1 Fixtures and factories

- `settings` fixture: `expiry_job_enabled=False`.
- `freeze_now` fixture: `freeze_now(datetime(2026, 11, 9, 8, 0))` sets local now. Default for booking tests: a fixed Monday 08:00 local, so "tomorrow 09:00" is always valid.
- Factories (`tests/factories.py`) + fixtures:
  - `make_catering_package`, `make_it_service`, `make_holiday`.
  - `make_pitika(province="PHNOM_PENH")`: location in that province → department → division → user with PITIKA.
  - `make_private_room(owner=None)`: owner gets ROOM_OWNER.
  - `make_booking(room, requester, status=…, route=…, sessions=[(date, start, end)], catering=False, it=False, forwarded=False)`: inserts rows directly (no API), for read / transition tests.
- Helper `book(client, headers, **overrides)` in `tests/booking_helpers.py`: posts a valid body and returns the JSON.

### 14.2 Concurrency (two real connections)

`tests/test_booking_concurrency.py` cannot use the rollback `db_session`. It uses `migrated_engine` directly, commits its data, and in teardown deletes every row it made (child tables first). Two threads with their own `Session`:

- Two Pitika approve the same booking → one 200-style success, one `STALE_VERSION`.
- Two creates for the same room and time → one saved, one `SCHEDULE_CONFLICT`.

Call the service functions directly (not the HTTP client), with a `threading.Barrier` so both start together.

### 14.3 Test files (each item of requirements 12.1 is covered)

| File | Covers |
|---|---|
| `test_clock.py` | offset, freeze |
| `test_booking_scheduling.py` | shapes, hours, past, route table, steps, overlap inside booking (unit) |
| `test_catering_packages.py`, `test_it_services.py`, `test_public_holidays.py` | CRUD, Admin only, inactive hidden, DUPLICATE, STALE_VERSION |
| `test_bookings_check.py` | route + steps for R1–R4, problem field, warnings, saves nothing |
| `test_bookings_create.py` | T1, T2, every 422/409 in 9.4, clash rules (overlap refused, back-to-back ok, rejected/cancelled do not block, pending blocks), one bad session saves nothing, NO_REVIEWER, R3 with no Pitika, holiday + capacity warnings, requester_info copy |
| `test_room_schedule.py` | range rules, masking for private rooms, owner / Pitika / booker see the title |
| `test_bookings_read.py` | detail visibility for each role (404 for others), mine list filters, COMPLETED |
| `test_pitika_bookings.py` | T3, T4, T5, T6, province scope, TIME_PASSED on approve, reject after start ok, food approved, notes passed on |
| `test_pitika_catering.py` | B-12 |
| `test_owner_bookings.py` | T7, T8, T9, owner change moves the queue |
| `test_it_tickets.py` | hidden until forwarded, T10, T11, staff rules, IT Staff 403, hidden after cancel |
| `test_bookings_edit.py` | T13, FIELD_NOT_EDITABLE, after start, status kept |
| `test_bookings_cancel.py` | T12, until last end, sessions freed, others 403 |
| `test_door_pass.py` | hidden before confirm, who sees it, expired flag, format, ≠ reference; reference code format `NBC-YY-NNNNN` (B-28) |
| `test_booking_ics.py` | one VEVENT per session, escaping, status |
| `test_booking_expiry.py` | T15, T17 (with door pass), skips changed bookings, `scripts.run_expiry` |
| `test_booking_routes.py` | end to end R1–R4 with and without IT; one INVALID_TRANSITION |
| `test_room_booking_guards.py` | section 12, incl. B-14 (pending R2), B-21 (moving a place), B-27 (booker turned off) |
| `test_booking_concurrency.py` | 14.2 |

## 15. Build order

Each step: tests first, then code, then `pytest` and `ruff check .` green, then a commit (no Claude attribution).

1. **Base**: settings, `clock.py`, `constants/booking.py`, error codes, security aliases, `NoHtml`. Tests: `test_clock.py`, `test_config.py` update.
2. **Models + migration**: all 12 models, `models/__init__.py`, migration, `test_migrations.py` + `test_schema.py` updates.
3. **Catalogs**: packages, services, holidays (schema, service, router). Factories.
4. **Scheduling and access services**: `booking_scheduling.py`, `booking_access.py`, `booking_codes.py`. Unit tests.
5. **Check**: `POST /bookings/check`.
6. **Create + read**: `POST /bookings`, `GET /bookings/{id}`, `GET /bookings/mine`, `booking_transitions.py` (R3 needs `make_confirmed`). `make_booking` factory.
7. **Schedule**: `GET /rooms/{id}/schedule`.
8. **Pitika**: list, approve, reject; food list.
9. **Owner**: list, approve, reject.
10. **IT**: list, staff, ready.
11. **Door pass + ics.**
12. **Edit + cancel.**
13. **Expiry**: `run_once`, runner, lifespan, script.
14. **Section 12 guards** in room, floor, building, location, user services.
15. **Concurrency tests**, end-to-end route tests, `.env.example`, full suite.

## 16. Left to the builder

- Exact names of private helpers and response-building functions.
- Query style (joins vs subqueries) as long as the rules hold and lists stay one query per page plus small lookups.
- Log wording.
