# Room Booking API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add room booking (sessions, routes R1–R4, Pitika / owner / IT steps, door pass, ics, expiry) to the existing NBC Meeting Room API.

**Architecture:** New models, one migration, and services that hold every rule. Routers stay thin. All status changes go through `app/services/booking_transitions.py` (version check). All "now" comes from `app/services/clock.py`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, MySQL 8, Alembic, pytest. No new packages.

**Spec:** `docs/superpowers/specs/2026-11-03-room-booking-api-design.md` (the "spec"). Rules come from `docs/superpowers/specs/2026-11-02-room-booking-api-requirements.md` (the "requirements"). Read both. IDs like B-14, T4, BR-SCH-03 point there.

## Global Constraints

- No new packages. requirements.txt stays as it is.
- One model class per file in `app/models/`. One schema, service and router file per resource. Rules live in services.
- Base path `/api/v1`. JSON snake_case. Errors `{"error": {"code", "message", "fields"}}` via `AppError`.
- Booking code never calls `datetime.now()` / `utcnow()` for business time: use `clock.now_utc()` / `clock.now_local()`.
- Local time = UTC + 7 hours, fixed (`LOCAL_OFFSET = timedelta(hours=7)`). No `zoneinfo`.
- Field errors use 0-based session index: `sessions.0.start_time` (B-16).
- Masked title text is exactly `Reserved (Private Session)`.
- Expiry reason is exactly `Expired: not approved before the meeting time.`
- Reference code `NBC-YY-NNNNN` (B-28). Door pass `NBC-NNNNN`, NNNNN 10000–99999, from `secrets`.
- Limits come from `Settings` (spec section 4), never hard-coded in schemas.
- Tests need MySQL: `docker compose up -d mysql`. Run tests with `.venv/Scripts/python -m pytest`. Lint with `.venv/Scripts/python -m ruff check .`.
- Commits: message style `Booking: <what changed>`. Never add Co-Authored-By Claude or "Generated with Claude".
- Do not touch `admin_dashboard/` (the uncommitted `RoomFilters.vue` change is not ours).

## Review Focus

1. **Sessions sent out of order** (later date first): "first session" must be the earliest by (date, start), for display, expiry, edit window and food delivery. → test in Task 6 and Task 13.
2. **Early-morning local time** (06:30 local = 23:30 UTC the day before): "today" and "past" must use the local date. → test in Task 1 and Task 4.
3. **Session exactly at room open / close** (08:00 start, 18:00 end) and back-to-back sessions: allowed. → test in Task 4.
4. **Normal text with `<`** ("Budget < 5000", Khmer titles) must be saved; only HTML-like text (`<b>`, `</`, `<!`) is refused. → test in Task 1.
5. **PATCH that sends a refused field as `null`** (`"room_id": null`) is still `FIELD_NOT_EDITABLE`, not ignored. → test in Task 12.

## Shared test helpers (used from Task 3 on)

- `tests/booking_helpers.py`: `NOW = datetime(2026, 11, 9, 8, 0)` (local, a Monday), `DAY = date(2026, 11, 10)`, `body(room_id, **overrides) -> dict` (a valid `POST /bookings` body: one session `DAY 09:00–10:00`, title "Team meeting", type INTERNAL, attendees 5), `book(client, headers, room_id, **overrides) -> Response`, `error(response) -> tuple[int, str]`, `fields(response) -> dict`.
- Booking tests use the `freeze_now` fixture with `NOW` (autouse in each booking test module via `pytestmark = pytest.mark.usefixtures("frozen")`, where `frozen` is a fixture in `conftest.py` calling `freeze_now(NOW)`).

---

### Task 1: Base — settings, clock, enums, error codes, roles, NoHtml

**Files:**
- Create: `app/services/clock.py`, `app/constants/booking.py`, `tests/test_clock.py`, `tests/test_booking_constants.py`
- Modify: `app/config.py`, `app/errors.py`, `app/security.py`, `app/schemas/common.py`, `.env.example`, `tests/conftest.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `clock.LOCAL_OFFSET`, `clock._source: Callable[[], datetime]` (aware UTC), `now_utc() -> datetime` (naive UTC, whole seconds), `now_local() -> datetime`, `local_to_utc(value: datetime) -> datetime`, `session_start(s) -> datetime`, `session_end(s) -> datetime` (`s` has `.date`, `.start_time`, `.end_time`).
  - Enums in `app/constants/booking.py` (spec section 6), plus `FINAL`, `PENDING`, `MASKED_TITLE`, `EXPIRY_REASON`, `BOOKER_OFF_REASON = "Cancelled: the booker's account was turned off."`.
  - Settings fields of spec section 4.
  - `ErrorCode` members of spec section 11.
  - `PitikaUser`, `RoomOwnerUser`, `ITLeadUser`, `ITUser`, `PitikaOrAdminUser`.
  - `schemas.common.NoHtml` (an `AfterValidator`), `BookingText(max_length, min_length=1)` and `OptionalBookingText(max_length, min_length=None)`: like `Text` / `OptionalText` plus `NoHtml` and a minimum length after trimming.
  - conftest: `freeze_now` fixture → `freeze_now(local: datetime) -> None`; `settings` fixture gets `expiry_job_enabled=False`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_clock.py
def test_now_local_is_utc_plus_7(freeze_now):
    freeze_now(datetime(2026, 11, 10, 6, 30))
    assert clock.now_local() == datetime(2026, 11, 10, 6, 30)
    assert clock.now_utc() == datetime(2026, 11, 9, 23, 30)

def test_local_to_utc():
    assert clock.local_to_utc(datetime(2026, 11, 10, 9, 0)) == datetime(2026, 11, 10, 2, 0)

def test_session_start_and_end():  # SimpleNamespace(date=..., start_time=..., end_time=...)
    assert clock.session_start(s) == datetime(2026, 11, 10, 9, 0)

# tests/test_booking_constants.py
def test_booking_status_values(): assert [s.value for s in BookingStatus] == [
    "PENDING_PITIKA", "PENDING_OWNER", "SETUP_IN_PROGRESS", "CONFIRMED", "REJECTED", "CANCELLED"]
def test_texts(): assert MASKED_TITLE == "Reserved (Private Session)"
@pytest.mark.parametrize("text", ["Budget < 5000", "ប្រជុំ", "a<5"])
def test_no_html_allows(text): ...  # NoHtml returns text
@pytest.mark.parametrize("text", ["<b>hi</b>", "x </script>", "<!-- c -->"])
def test_no_html_refuses(text): ...  # ValueError "HTML is not allowed."
def test_new_error_codes(): assert {"SCHEDULE_CONFLICT", "STALE_VERSION",
    "HAS_PENDING_OWNER_BOOKINGS"} <= {c.value for c in ErrorCode}

# tests/test_config.py (add)
def test_booking_setting_defaults(settings):
    assert (settings.booking_min_minutes, settings.booking_max_sessions,
            settings.booking_max_days_ahead, settings.booking_max_attendees,
            settings.booking_max_participants, settings.schedule_max_days,
            settings.it_setup_lead_minutes) == (15, 20, 90, 100, 50, 31, 30)
```

- [ ] **Step 2:** Run `.venv/Scripts/python -m pytest tests/test_clock.py tests/test_booking_constants.py tests/test_config.py -q`. Expected: FAIL (import errors).
- [ ] **Step 3: Implement.** `NoHtml` refuses `re.search(r"<[A-Za-z/!]", value)`. `freeze_now` uses `monkeypatch.setattr(clock, "_source", lambda: (local - LOCAL_OFFSET).replace(tzinfo=UTC))`. Update the `ErrorCode` docstring to name both specs. Add the new settings to `.env.example` with defaults.
- [ ] **Step 4:** Run the same tests, then the full suite. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: clock, enums, settings and error codes`.

---

### Task 2: Models and migration

**Files:**
- Create: the 12 model files of spec 3.1 (`booking.py` … `public_holiday.py`), `alembic/versions/e4b7c2a9f310_add_booking_tables.py`
- Modify: `app/models/__init__.py`, `app/models/room.py` (comment on `is_private`), `app/schemas/room.py` (same comment), `tests/test_migrations.py`, `tests/test_schema.py`

**Interfaces:**
- Produces models with the columns of spec section 7 and these relationships:
  - `Booking.room`, `Booking.requester`, `Booking.sessions` (`order_by=(BookingSession.date, BookingSession.start_time)`), `Booking.participants`, `Booking.catering_order` (`uselist=False`), `Booking.it_ticket` (`uselist=False`), `Booking.reviews` (order by id), `Booking.rejection` (`uselist=False`), `Booking.door_pass` (`uselist=False`).
  - `ITTicket.booking`, `ITTicket.staff` (`secondary=it_ticket_staff`, order by `User.name_en`).
  - `CateringOrder.booking`, `CateringOrder.decider` (FK `decided_by`).
  - Class names: `Booking, BookingSession, BookingReview, BookingRejection, BookingDoorPass, BookingParticipant, CateringOrder, ITTicket, it_ticket_staff, CateringPackage, ITService, PublicHoliday`.

- [ ] **Step 1: Write failing tests.** `test_migrations.py`: add the 12 table names to `ALL_TABLES`; rename the 14-table test to `test_models_define_all_tables`. `test_schema.py`: add `EXPECTED_COLUMNS` rows for each new table (type + nullable from spec 7). Add:

```python
def test_booking_session_index(conn):  # ix_booking_sessions_room_id_date_is_blocking exists
def test_booking_status_check_constraint(db_session):  # status "DONE" → ER_CHECK_CONSTRAINT_VIOLATED
def test_session_time_order_check(db_session):  # start 10:00, end 09:00 → check violated
def test_reference_code_unique(db_session):  # ER_DUP_ENTRY
def test_rejection_actor_may_be_null(db_session)
```

- [ ] **Step 2:** Run `pytest tests/test_migrations.py tests/test_schema.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** models and the migration (create in FK order, drop in reverse). Enum columns: `String(n)` + `CheckConstraint("<col> IN ('A', 'B')", name="<col>_values")`.
- [ ] **Step 4:** Run the two files, then the full suite (`test_migrations_match_the_models` must pass). Expected: PASS.
- [ ] **Step 5: Commit** `Booking: tables and migration`.

---

### Task 3: Catalogs — catering packages, IT services, public holidays

**Files:**
- Create: `app/schemas/catering_package.py`, `it_service.py`, `public_holiday.py`; `app/services/catering_package.py`, `it_service.py`, `public_holiday.py`; `app/routers/catering_packages.py`, `it_services.py`, `public_holidays.py`; `tests/test_catering_packages.py`, `tests/test_it_services.py`, `tests/test_public_holidays.py`; `tests/booking_helpers.py`
- Modify: `app/main.py` (include routers), `app/services/records.py` (`_DUPLICATE_MESSAGES["holiday_date"] = "This date already has a holiday."`), `tests/factories.py`, `tests/conftest.py`

**Interfaces:**
- Produces factories + fixtures: `make_catering_package(**fields)`, `make_it_service(**fields)`, `make_holiday(holiday_date: date, **fields)`.
- Produces services (same shape for packages and services):
  `list_catering_packages(session, current, page, size, is_active, search) -> dict`, `create_catering_package(session, data) -> CateringPackage`, `update_catering_package(session, package_id, changes) -> CateringPackage` (`changes` holds `version`).
  Holidays: `list_holidays(session, page, size, year) -> dict`, `create_holiday`, `update_holiday`, `delete_holiday(session, holiday_id) -> None`.
- Out schemas: `CateringPackageOut` / `ITServiceOut`: `id, name, description, sort_order, is_active, version, created_at, updated_at`. `PublicHolidayOut`: `id, holiday_date, name_km, name_en, remarks, created_at, updated_at`.

- [ ] **Step 1: Write failing tests** (packages; copy for IT services):

```python
def test_create_package(client, as_admin)                    # 201, version == 1
def test_name_2_to_200(client, as_admin)                     # "A" → 422 fields["name"]
def test_name_unique(client, as_admin)                       # 409 DUPLICATE
def test_patch_needs_version(client, as_admin)               # no version → 422
def test_patch_stale_version(client, as_admin)               # version 1 twice → 2nd 409 STALE_VERSION
def test_patch_raises_version(client, as_admin)              # → version 2
def test_staff_cannot_write(client, as_staff)                # 403 FORBIDDEN
def test_staff_sees_only_active(client, as_staff, make_catering_package)
def test_admin_filters_is_active(client, as_admin, make_catering_package)
def test_html_refused(client, as_admin)                      # description "<b>x</b>" → 422
# holidays
def test_create_holiday(client, as_admin)                    # name_km required, name_en optional
def test_holiday_date_unique(client, as_admin)               # 409 DUPLICATE "This date already has a holiday."
def test_list_by_year_sorted_by_date(client, as_staff, make_holiday)
def test_delete_holiday(client, as_admin, make_holiday)      # 204, then GET list has none
```

- [ ] **Step 2:** Run the three files. Expected: FAIL.
- [ ] **Step 3: Implement** following `equipment` (router, schema, service). Version check: `if record.version != changes.pop("version"): raise AppError(STALE_VERSION, 409, "This item changed. Reload it.")`, then `record.version += 1`.
- [ ] **Step 4:** Run the three files. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: catering packages, IT services and public holidays`.

---

### Task 4: Scheduling, access and code services

**Files:**
- Create: `app/services/booking_scheduling.py`, `app/services/booking_access.py`, `app/services/booking_codes.py`, `tests/test_booking_scheduling.py`, `tests/test_booking_access.py`, `tests/test_booking_codes.py`
- Modify: `tests/factories.py`, `tests/conftest.py`

**Interfaces:**
- Consumes: Task 1 clock and enums, Task 2 models, `room_service.is_bookable`, `province.get_user_province`.
- Produces (signatures exactly as spec 8.1–8.3, plus):
  - `booking_scheduling.active_pitika_count(session, province: str) -> int`
  - `booking_scheduling.check_clashes(session, current, room, sessions, exclude_booking_id: int | None = None) -> None`
  - `booking_scheduling.first_status(route: BookingRoute) -> BookingStatus`
  - `booking_access.room_province(room) -> str`, `pitika_province(current) -> str | None`, `can_view(session, current, booking) -> bool`, `is_door_pass_viewer(current, booking) -> bool` (role part only; the CONFIRMED part is checked by the endpoint), `load_visible_booking(session, current, booking_id) -> Booking`, `visible_title(session, current, booking) -> str`
  - `booking_codes.new_reference_code(session, now_local: datetime) -> str`, `new_door_pass_code(session, reference_code: str) -> str`
  - Factories + fixtures: `make_pitika(province="PHNOM_PENH", **fields) -> User`; `make_bookable_room(province="PHNOM_PENH", private=False, owner=None, **fields) -> Room` (a private room with no `owner` gets a new ROOM_OWNER user; hours 08:00–18:00, capacity 10); `make_booking(room, requester, *, status, route=None, sessions=((DAY, time(9), time(10)),), catering=False, it=False, forwarded=False, assigned_staff=(), version=1) -> Booking` (route defaults from `pick_route`; sessions blocking unless status is final).

- [ ] **Step 1: Write failing tests**

```python
# shapes (settings fixture, today = date(2026, 11, 9))
def test_no_sessions()                      # 422 fields {"sessions": ...}
def test_21_sessions()                      # 422 "sessions"
def test_end_before_start()                 # fields["sessions.0.end_time"]
def test_14_minutes_refused_15_ok()         # "A session is at least 15 minutes."
def test_91_days_ahead_refused_90_ok()      # fields["sessions.0.date"]
def test_overlap_inside_booking()           # given order [B 9:30-10:30, A 9:00-10:00] → field names the later one
def test_back_to_back_inside_booking_ok()
# room
def test_room_hours_boundaries_ok()         # 08:00-09:00 and 17:00-18:00 pass
def test_outside_hours()                    # 07:45 → 422 OUTSIDE_ROOM_HOURS "This room is open from 08:00 to 18:00."
def test_inactive_floor_not_bookable()      # 409 ROOM_NOT_BOOKABLE
def test_private_room_without_owner()       # 409 "This private room has no owner yet."
def test_past_uses_local_date()             # now 2026-11-10 06:30 local: 2026-11-10 07:00 ok; 2026-11-09 09:00 → 409 TIME_PASSED
def test_start_equal_now_ok()
# route
@pytest.mark.parametrize("private,own,food,it,route", [
    (False, False, False, False, "R1"), (False, True, True, True, "R1"),
    (True, False, False, False, "R2"), (True, True, False, False, "R3"),
    (True, True, True, False, "R4"), (True, True, False, True, "R4")])
def test_pick_route(...)
def test_steps()   # R2 + IT → [PITIKA, OWNER, IT_SETUP, CONFIRMED]; R3 → [CONFIRMED]
def test_no_reviewer(make_bookable_room)    # R1 in SIEM_REAP, no Pitika → 409 NO_REVIEWER
def test_inactive_pitika_does_not_count()
def test_r3_needs_no_pitika()
# clash
def test_clash_overlap(make_booking)        # 409 SCHEDULE_CONFLICT, field "sessions.0"
def test_back_to_back_ok(make_booking)
def test_rejected_and_cancelled_do_not_block(make_booking)
def test_pending_blocks(make_booking)
def test_clash_message_masked_for_others()  # "...from 09:00 to 10:00 for Reserved (Private Session)."
def test_clash_message_shows_title_to_owner()
# warnings
def test_holiday_warning_once_per_date(make_holiday)  # 2 sessions same holiday date → 1 warning
def test_over_capacity_warning()            # {"code": "OVER_CAPACITY", "seats": 10, "attendees": 12}
# access (tests/test_booking_access.py): can_view for booker, admin, owner, Pitika same / other
# province, IT Lead before / after forward, IT Staff assigned / not; door-pass viewers.
# codes (tests/test_booking_codes.py)
def test_reference_code_format()            # re.fullmatch(r"NBC-26-\d{5}", code)
def test_door_pass_format()                 # re.fullmatch(r"NBC-[1-9]\d{4}", code)
def test_door_pass_skips_active_codes(monkeypatch)  # patch secrets.randbelow to repeat a taken code first
```

- [ ] **Step 2:** Run the three files. Expected: FAIL.
- [ ] **Step 3: Implement** per spec 8.1–8.3. `check_session_shapes` sorts a copy by (date, start) but reports the original index.
- [ ] **Step 4:** Run the three files. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: scheduling, access and code rules`.

---

### Task 5: `POST /bookings/check`

**Files:**
- Create: `app/schemas/booking.py` (start: `SessionIn`, `BookingCheck`, `BookingCheckResult`, `Problem`), `app/services/booking.py` (start), `app/routers/bookings.py` (start), `tests/test_bookings_check.py`
- Modify: `app/main.py`

**Interfaces:**
- Produces: `booking_service.check_booking(session, current, body: BookingCheck, settings) -> BookingCheckResult`. `BookingCheckResult`: `route, first_status, steps, problem: Problem | None, warnings`. `Problem`: `code, message, fields`.

- [ ] **Step 1: Write failing tests**

```python
def test_check_r1_steps(client, ...)        # 200, route "R1", steps ["PITIKA", "CONFIRMED"], problem None
def test_check_r2_with_it(...)              # ["PITIKA", "OWNER", "IT_SETUP", "CONFIRMED"], "PENDING_PITIKA"
def test_check_r3(...)                      # first_status "CONFIRMED", steps ["CONFIRMED"]
def test_check_clash_is_problem_not_error(...)  # 200, problem.code "SCHEDULE_CONFLICT", fields {"sessions.0": ...}
def test_check_unknown_room(...)            # 200, route None, problem.fields {"room_id": "Room not found."}
def test_check_bad_time_is_422(...)         # "25:00" → 422 VALIDATION_ERROR
def test_check_holiday_warning(...)
def test_check_saves_nothing(db_session, ...)  # count(Booking) == 0
```

- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** Run the checks of spec 9.3 in order inside `try`; turn the first `AppError` into `Problem`.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: check a booking before sending`.

---

### Task 6: Create and read bookings

**Files:**
- Create: `app/services/booking_transitions.py`, `tests/test_bookings_create.py`, `tests/test_bookings_read.py`
- Modify: `app/schemas/booking.py`, `app/services/booking.py`, `app/routers/bookings.py`

**Interfaces:**
- Produces in `booking_transitions.py` (spec 8.5): `check_version`, `invalid_transition(booking) -> AppError` (message by status / completed), `advance(session, booking, version, **values) -> None`, `stop_blocking`, `reject`, `make_confirmed`, `forward_it`, `after_last_review`, plus `first_start(booking) -> datetime`, `last_end(booking) -> datetime`, `has_started(booking) -> bool`, `has_ended(booking) -> bool`, `display_status(booking) -> DisplayStatus`.
- Produces in `booking.py`: `create_booking(session, current, body: BookingCreate, settings) -> tuple[Booking, list[dict]]`, `get_booking(session, current, booking_id) -> Booking`, `list_my_bookings(session, current, page, size, status: str | None, q: str | None) -> dict`, `build_booking_detail(session, booking, settings) -> BookingDetail`, `build_booking_list_items(session, bookings) -> list[BookingListItem]`, `filter_display_status(query, status: str | None) -> Select` (422 `status` for unknown values).
- Schemas: `BookingCreate`, `CateringIn`, `ITIn`, `BookingListItem`, `BookingDetail`, `BookingSaved`, `BookingRoomRef` (spec 9.1, 9.4).

- [ ] **Step 1: Write failing tests**

```python
# create
def test_r1_created_pending(...)            # 201, status PENDING_PITIKA, route R1, version 1, reference NBC-26-\d{5}
def test_r3_confirmed_with_door_pass(...)   # status CONFIRMED; booking_reviews row (PITIKA, NOT_REQUIRED, None); door pass exists
def test_requester_info_copied(...)         # keys name_en … phone; later profile change does not change it
def test_sessions_out_of_order(...)         # sent [DAY+1, DAY] → first_session.date == DAY, sessions sorted
def test_attendees_rules(...)               # 0, 101 → 422; 2 attendees + 2 emails → 422 fields["attendees"]
def test_own_email_removed(...)             # participant_emails [own] → []
def test_51_participants(...)               # 422 fields["participant_emails"]
def test_r2_needs_justification(...)        # 422 fields["private_justification"]
def test_inactive_package(...)              # 409 INACTIVE_REFERENCE; unknown → 422 "catering.package_ids"
def test_food_and_it_copied(...)            # catering.packages [{id, name}]; it.status RECEIVED, forwarded_at None
def test_one_bad_session_saves_nothing(...) # 2nd session clashes → 409, count(Booking) == 0
def test_over_capacity_and_holiday_warnings(...)
def test_title_3_letters(...)               # "ab" → 422
def test_same_person_two_rooms_same_time(...)   # B-26: both 201
# read
def test_detail_visible_to_allowed_roles(...)   # parametrize booker, admin, owner, Pitika, IT lead (forwarded)
def test_detail_404_for_others(...)             # other staff, Pitika of other province, IT lead before forward
def test_mine_newest_first_and_q(...)           # q matches title or reference
def test_mine_status_completed(...)             # CONFIRMED booking with last end past → display_status COMPLETED
def test_mine_unknown_status_422(...)
```

- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** spec 9.4–9.6 and 8.5. Room lock: `session.execute(select(Room.id).where(Room.id == room.id).with_for_update())`. Reference code insert inside `session.begin_nested()`, retry up to 3 on duplicate key (`records._duplicate_field` returns `"reference_code"`).
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: send a booking and read bookings`.

---

### Task 7: Room schedule

**Files:**
- Create: `app/schemas/room_schedule.py`, `app/services/room_schedule.py`, `app/routers/room_schedule.py`, `tests/test_room_schedule.py`
- Modify: `app/main.py`

**Interfaces:**
- Produces: `get_schedule(session, current, room_id, date_from: date | None, date_to: date | None, settings) -> list[ScheduleItem]`.

- [ ] **Step 1: Write failing tests**

```python
def test_default_range_is_7_days(...)
def test_32_days_refused(...)               # 422 fields["to"] "At most 31 days."
def test_to_before_from(...)                # 422 fields["to"]
def test_only_blocking_sorted(...)          # cancelled hidden; sorted by date, start
def test_private_masked_for_staff(...)      # title MASKED_TITLE, booking_id None, requester_name None, is_masked True
def test_private_visible_to_owner_and_booker(...)
def test_shared_never_masked(...)
def test_inactive_room_still_answers(...)   # 200
```

- [ ] **Step 2:** Run. Expected: FAIL. **Step 3:** Implement spec 9.2. **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: room schedule with private sessions masked`.

---

### Task 8: Pitika review and food list

**Files:**
- Create: `app/schemas/booking_review.py`, `app/services/booking_review.py`, `app/routers/pitika_bookings.py`, `app/schemas/catering_order.py`, `app/services/catering_order.py`, `app/routers/catering_orders.py`, `tests/test_pitika_bookings.py`, `tests/test_pitika_catering.py`
- Modify: `app/main.py`

**Interfaces:**
- Produces: `ApproveBody(notes, version)`, `RejectBody(reason 5..1000, version)`; `list_pitika_bookings(session, current, page, size, status, date_from, date_to, room_id, q) -> dict`, `pitika_approve(session, current, booking_id, notes, version) -> Booking`, `pitika_reject(session, current, booking_id, reason, version) -> Booking`; `list_food_orders(session, current, day: date) -> list[CateringOrderItem]`.

- [ ] **Step 1: Write failing tests**

```python
def test_list_only_own_province(...)
def test_list_from_to_match_any_session(...)
def test_t3_r2_goes_to_owner(...)           # PENDING_OWNER, version 2, review (PITIKA, APPROVED)
def test_t4_it_forwarded(...)               # SETUP_IN_PROGRESS, it.forwarded_at set
def test_t5_confirmed_with_door_pass(...)
def test_food_approved_with_notes(...)      # decided_by == pitika, approver_notes == notes
def test_t6_reject_needs_reason(...)        # "abc" → 422; ok → REJECTED, rejection.rejected_by PITIKA, sessions not blocking
def test_other_province_404(...)
def test_approve_after_start_time_passed(...)   # freeze after start → 409 TIME_PASSED
def test_reject_after_start_ok(...)
def test_wrong_status_invalid_transition(...)   # PENDING_OWNER → 409 INVALID_TRANSITION
def test_stale_version(...)                     # version 0 → 409 STALE_VERSION
def test_self_approval_allowed(...)             # B-20
def test_staff_forbidden(...)                   # 403
# food list
def test_food_list_day_and_status(...)      # only SETUP_IN_PROGRESS / CONFIRMED with first session on date
def test_food_list_servings_follow_attendees(...)
def test_admin_sees_all_provinces(...)
```

- [ ] **Step 2:** Run. Expected: FAIL. **Step 3:** Implement spec 9.11–9.12. **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: Pitika review and the day's food list`.

---

### Task 9: Room owner review

**Files:**
- Create: `app/routers/owner_bookings.py`, `tests/test_owner_bookings.py`
- Modify: `app/services/booking_review.py`, `app/main.py`

**Interfaces:**
- Produces: `list_owner_bookings(session, current, page, size, status, room_id, q) -> dict`, `owner_approve(session, current, booking_id, notes, version) -> Booking`, `owner_reject(session, current, booking_id, reason, version) -> Booking`.

- [ ] **Step 1: Write failing tests**

```python
def test_t7_it_forwarded(...)
def test_t8_confirmed(...)
def test_t9_reject(...)                     # rejected_by OWNER
def test_other_owner_404(...)
def test_pending_pitika_invalid_transition(...)
def test_approve_after_start_time_passed(...)   # B-09
def test_queue_follows_new_owner(...)       # Admin PATCH room_owner_id → new owner lists and approves it
```

- [ ] **Step 2:** Run. Expected: FAIL. **Step 3:** Implement spec 9.13. **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: room owner review`.

---

### Task 10: IT tickets

**Files:**
- Create: `app/schemas/it_ticket.py`, `app/services/it_ticket.py`, `app/routers/it_tickets.py`, `tests/test_it_tickets.py`
- Modify: `app/main.py`

**Interfaces:**
- Produces: `list_tickets(session, current, page, size, status, q) -> dict`, `assign_staff(session, current, ticket_id, user_ids, technician_notes, version) -> ITTicket`, `mark_ready(session, current, ticket_id, version) -> ITTicket`, `build_ticket_items(session, tickets, settings) -> list[ITTicketItem]`.

- [ ] **Step 1: Write failing tests**

```python
def test_not_listed_before_forward(...)
def test_lead_sees_all_staff_sees_assigned(...)
def test_hidden_after_cancel(...)
def test_t10_assign(...)                    # ticket ASSIGNED, assigned_at set, booking version +1
def test_assign_needs_active_it_staff(...)  # STAFF-only user → 409 INACTIVE_REFERENCE; unknown id → 422
def test_reassign_replaces(...)
def test_t11_ready_confirms(...)            # booking CONFIRMED, door pass, ticket READY
def test_ready_before_assign(...)           # 409 INVALID_TRANSITION
def test_ready_with_only_inactive_staff(...)   # B-22 → 409 "Assign active IT Staff first."
def test_it_staff_cannot_change(...)        # 403
def test_setup_time_30_min_before(...)      # setup_time "08:30" for 09:00 start
def test_review_notes_shown(...)            # BR-APR-07
```

- [ ] **Step 2:** Run. Expected: FAIL. **Step 3:** Implement spec 9.14. **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: IT tickets, staff and Ready`.

---

### Task 11: Door pass and calendar file

**Files:**
- Create: `app/services/booking_ics.py`, `tests/test_door_pass.py`, `tests/test_booking_ics.py`
- Modify: `app/schemas/booking.py` (`DoorPassOut`), `app/services/booking.py` (`get_door_pass`), `app/routers/bookings.py`

**Interfaces:**
- Produces: `get_door_pass(session, current, booking_id) -> BookingDoorPass`, `build_ics(booking) -> str`.

- [ ] **Step 1: Write failing tests**

```python
def test_no_door_pass_before_confirm(...)   # 404 "No door pass yet."
def test_door_pass_viewers(...)             # booker, owner, Pitika, admin → 200; IT lead → 403
def test_expired_flag(...)                  # freeze after last end → expired True
def test_expires_at_is_last_end_utc(...)    # last session DAY 10:00 local → "2026-11-10T03:00:00Z"
def test_ics_one_event_per_session(...)     # text.count("BEGIN:VEVENT") == 2; DTSTART:20261110T020000Z
def test_ics_escapes_and_folds(...)         # title "a, b; c" → "a\\, b\\; c"; every line ≤ 75 bytes; CRLF
def test_ics_status(...)                    # pending → TENTATIVE, cancelled → CANCELLED
def test_ics_404_for_others(...)
```

- [ ] **Step 2:** Run. Expected: FAIL. **Step 3:** Implement spec 9.9–9.10. **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: door pass and calendar file`.

---

### Task 12: Edit and cancel

**Files:**
- Create: `tests/test_bookings_edit.py`, `tests/test_bookings_cancel.py`
- Modify: `app/schemas/booking.py` (`BookingUpdate`, `CateringUpdate`, `ITUpdate`, `CancelBody`), `app/services/booking.py`, `app/routers/bookings.py`

**Interfaces:**
- Produces: `update_booking(session, current, booking_id, body: BookingUpdate, settings) -> tuple[Booking, list[dict]]`, `cancel_booking(session, current, booking_id, reason: str | None, version: int) -> Booking`. Refused fields are found with `body.model_fields_set` (and the nested models' `model_fields_set`), so a `null` value counts as sent.

- [ ] **Step 1: Write failing tests**

```python
def test_small_edit_keeps_status(...)       # CONFIRMED stays CONFIRMED, version +1
@pytest.mark.parametrize("extra", [{"room_id": 2}, {"room_id": None}, {"sessions": []},
    {"private_justification": "x"}, {"catering": {"package_ids": [1]}}, {"it": {"service_ids": [1]}}])
def test_refused_fields(...)                # 422 FIELD_NOT_EDITABLE
def test_catering_on_booking_without_food(...)  # FIELD_NOT_EDITABLE (B-15)
def test_only_booker_edits(...)             # admin → 403
def test_edit_after_start(...)              # 409 TIME_PASSED
def test_edit_final(...)                    # cancelled → 409 INVALID_TRANSITION
def test_only_version_changes_nothing(...)  # version stays 1 (B-24)
def test_attendees_rechecked(...)           # 1 attendee with 1 email → 422
def test_participants_replaced(...)
# cancel
def test_cancel_pending(...)                # CANCELLED, sessions not blocking, cancelled_at set
def test_cancel_confirmed_mid_series(...)   # after 1st session, before last end → ok; sessions still in detail
def test_cancel_after_last_end(...)         # 409 INVALID_TRANSITION "This booking has ended."
def test_others_cannot_cancel(...)          # Pitika, owner, admin → 403
def test_cancel_reason_rules(...)           # "abc" → 422; None ok
def test_cancelled_time_free_again(...)     # same slot can be booked
```

- [ ] **Step 2:** Run. Expected: FAIL. **Step 3:** Implement spec 9.7–9.8. **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: small edits and cancel`.

---

### Task 13: Expiry job

**Files:**
- Create: `app/services/booking_expiry.py`, `app/expiry_runner.py`, `scripts/run_expiry.py`, `tests/test_booking_expiry.py`
- Modify: `app/main.py` (lifespan)

**Interfaces:**
- Produces: `ExpiryResult` (dataclass `rejected: list[int]`, `confirmed: list[int]`), `run_once(session) -> ExpiryResult`, `ExpiryRunner(settings).start() / .stop()`, `scripts.run_expiry.main() -> int`.

- [ ] **Step 1: Write failing tests**

```python
def test_t15_pending_rejected_at_start(...)     # freeze at first start → REJECTED, rejected_by SYSTEM, actor None, reason EXPIRY_REASON
def test_pending_owner_rejected(...)
def test_t17_setup_confirmed_with_pass(...)     # CONFIRMED, door pass, ticket status unchanged
def test_not_started_untouched(...)
def test_uses_earliest_session(...)             # sessions saved [DAY+1, DAY]; freeze at DAY start → expired
def test_skips_changed_booking(monkeypatch)     # make advance raise STALE for one id → others still done
def test_script_prints_counts(capsys, ...)      # "Rejected: 1, confirmed: 0"
def test_runner_not_started_in_tests(app)       # app.state has no running runner when expiry_job_enabled False
```

- [ ] **Step 2:** Run. Expected: FAIL. **Step 3:** Implement spec section 10. `scripts/run_expiry.py` uses `SessionLocal`. **Step 4:** Run. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: expiry job`.

---

### Task 14: Changes to the current API (section 12 guards)

**Files:**
- Create: `app/services/room_bookings.py`, `tests/test_room_booking_guards.py`
- Modify: `app/services/room.py`, `floor.py`, `building.py`, `location.py`, `user.py`, `app/schemas/user.py`, `app/routers/users.py`, existing tests that break (`tests/test_rooms.py`, `tests/test_users.py`: private rooms now need an owner; R9 clears shared rooms only)

**Interfaces:**
- Produces: `future_booking_count(session, room_ids: list[int]) -> int`, `pending_owner_count(session, room_id: int) -> int`, `private_room_ids_owned_by(session, user_id: int) -> list[int]`, `room_ids_in(session, *, floor_id=None, building_id=None, location_id=None) -> list[int]`. `UserChanged.bookings_cancelled: list[int]`.

- [ ] **Step 1: Write failing tests**

```python
def test_private_room_needs_owner(...)          # POST/PATCH → 422 OWNER_REQUIRED, field room_owner_id
def test_private_to_shared_with_pending_owner(...)   # 409 HAS_PENDING_OWNER_BOOKINGS "Resolve 1 bookings ..."
def test_private_to_shared_with_pending_r2(...)      # B-14
def test_turn_off_room_with_future_bookings(...)     # 409 HAS_FUTURE_BOOKINGS "This room has 1 future bookings. Ask the bookers to cancel first."
@pytest.mark.parametrize("place", ["floor", "building", "location"])
def test_turn_off_place_with_future_bookings(...)
def test_past_bookings_do_not_block(...)
@pytest.mark.parametrize("move", ["room.floor_id", "floor.building_id", "building.location_id", "location.province"])
def test_move_with_future_bookings(...)              # B-21
def test_owner_turned_off_with_private_room(...)     # 409 OWNER_HAS_PRIVATE_ROOMS "Assign a new owner for 1 private rooms first."
def test_owner_loses_role_with_private_room(...)
def test_shared_rooms_still_cleared(...)             # rooms_unassigned lists the shared room
def test_booker_turned_off_cancels_bookings(...)     # B-27: bookings_cancelled == [id]; reason BOOKER_OFF_REASON; completed one untouched
def test_lower_seats_and_hours_keep_bookings(...)
```

- [ ] **Step 2:** Run the new file. Expected: FAIL.
- [ ] **Step 3: Implement** spec section 12. Use the room's message from the spec; plural wording stays as the requirements write it ("3 future bookings").
- [ ] **Step 4:** Run the full suite; fix existing tests that relied on private rooms without owners. Expected: PASS.
- [ ] **Step 5: Commit** `Booking: guards on rooms, places and users`.

---

### Task 15: Concurrency and end-to-end routes

**Files:**
- Create: `tests/test_booking_concurrency.py`, `tests/test_booking_routes.py`

**Interfaces:**
- Consumes: services from Tasks 6, 8, 9, 10, 12.

- [ ] **Step 1: Write tests**

```python
# concurrency: own fixture on migrated_engine, data committed, rows deleted in teardown
def test_two_pitika_one_wins()        # Barrier(2); results sorted == ["ok", "STALE_VERSION"]
def test_two_creates_one_wins()       # results sorted == ["SCHEDULE_CONFLICT", "ok"]
# routes, through the HTTP client
@pytest.mark.parametrize("route,it", [("R1", False), ("R1", True), ("R2", False), ("R2", True),
                                      ("R3", False), ("R4", False), ("R4", True)])
def test_route_to_confirmed(...)      # each step's status in order; ends CONFIRMED with a door pass
def test_move_not_in_table(...)       # approve a CONFIRMED booking → 409 INVALID_TRANSITION
```

- [ ] **Step 2:** Run the two files. Expected: PASS (if a test fails, fix the service, not the test).
- [ ] **Step 3:** Run `.venv/Scripts/python -m pytest -q` and `.venv/Scripts/python -m ruff check .`. Expected: all pass, no lint errors.
- [ ] **Step 4: Commit** `Booking: concurrency and end-to-end route tests`.
