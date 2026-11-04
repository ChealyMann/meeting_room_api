# Admin Booking Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Admin can cancel any booking that has not ended, and approve or reject as a backup (for Pitika only when the province has no active Pitika; for the room owner always), with the actor recorded and shown in the booking's history.

**Architecture:** Three new columns record who acted (`bookings.cancelled_by`, `booking_reviews.by_admin`, `booking_rejections.by_admin`). A new service `booking_admin.py` and router `/admin/bookings` reuse the existing transitions (`cancel`, `reject`, `after_last_review`) and the Pitika and owner approve paths, so every status change still goes through the one version check and row lock (B-04, B-31). The dashboard's read-only booking panel gains buttons driven by a new `GET /admin/bookings/{id}/actions`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest; Vue 3 + TypeScript, Vitest, Playwright.

**Spec:** the owner's final answers D-32 to D-40 (review page https://claude.ai/artifact/9aMiG4xN2C45zAsS7P5FWB, answered 4 Nov 2026), recorded by Task 1 as B-33 to B-36 in `docs/superpowers/specs/2026-11-03-room-booking-api-design.md`; that spec stays binding for everything else.

## Global Constraints

- Branch `feature/admin-booking-actions` from `main`. Commits carry no AI attribution lines.
- API house rules: one model class per file; one schema, service and router file per resource; rules in services; routers thin; no new packages; tests first; `pytest` and `ruff check .` green.
- Decisions (verbatim effect):
  - D-32 B: Admin cancels any booking that is not final and not ended (PENDING_PITIKA, PENDING_OWNER, SETUP_IN_PROGRESS, CONFIRMED before last end).
  - D-33 C: Admin approves/rejects a PENDING_PITIKA booking only when the room's province has no active Pitika (`active_pitika_count(...) == 0`); else 403 `FORBIDDEN` "This office has an active Pitika. Ask them to decide."
  - D-34 B: Admin approves/rejects any PENDING_OWNER booking (private room).
  - D-35 B: reason optional for Admin cancel and reject (5–500 letters when given, HTML refused like every booking text). A reject with no reason saves `reason = "Rejected by the Admin."` (the column stays NOT NULL).
  - D-36 A: record the actor: `cancelled_by` = the user who cancelled (booker or Admin; null for the system, B-27); reviews and rejections made by the Admin get `by_admin = true` with `reviewer_id` / `actor_user_id` = the Admin.
  - D-37 A: same time rules: approve refused after the first session starts (409 `TIME_PASSED`); cancel refused after the last session ends (409 `INVALID_TRANSITION` "This booking has ended."); reject only while waiting.
  - D-38 A: an Admin cancel has the same effects as a booker cancel (sessions stop blocking; food and IT rows kept).
  - D-39 A: no notification.
  - D-40 A: no Admin IT steps: a SETUP_IN_PROGRESS booking can be cancelled, never approved or rejected by the Admin.
- Check order in every Admin action (spec 8.5): AdminUser (403) → booking exists (404) → stage rule (403, D-33) → `check_version` (409 `STALE_VERSION`) → status (409 `INVALID_TRANSITION`) → time (409 `TIME_PASSED` / ended) → write via `load_booking_for_write` + `advance`.
- Dashboard: Admin-only app; history wording: "Cancelled by {name}", "Pitika approved · {name} (Admin, for Pitika)", "Room owner rejected · {name} (Admin, for the owner)".

## Review Focus

- Two Admins act on the same booking at the same moment (approve and cancel) → one wins, the other gets `STALE_VERSION`, no duplicate review row (test in Task 2, concurrency style of `tests/test_booking_concurrency.py`).
- A Pitika is turned on for the province after the panel loaded its actions → the Admin's approve gets 403 with the API message, and the panel reloads its actions (test in Task 3).
- The booking ends while the panel is open → Cancel answers 409 "This booking has ended."; the message shows and the buttons disappear after the reload (test in Task 3).
- A reason with HTML (`<b>`) → 422 `fields.reason` shown under the reason box, nothing changes (test in Task 3).
- The Admin is also the booker → their cancel records `cancelled_by` = themselves, and the history reads "Cancelled by {name}" once (test in Task 2).

---

### Task 1: Record who acted (columns, transitions, answers, spec notes)

**Files:**
- Create: `alembic/versions/f1c3a7b9d2e4_admin_booking_actors.py` (down_revision `e4b7c2a9f310`)
- Modify: `app/models/booking.py` (`cancelled_by`), `app/models/booking_review.py` (`by_admin`), `app/models/booking_rejection.py` (`by_admin`), `app/services/booking_transitions.py`, `app/services/booking.py` (booker cancel), `app/services/user.py` (B-27 passes no actor), `app/services/booking_view.py`, `app/schemas/booking.py`, `docs/superpowers/specs/2026-11-03-room-booking-api-design.md` (B-33 to B-36 rows in section 2; 7.2/7.4 columns), `docs/superpowers/specs/2026-11-02-room-booking-api-requirements.md` (section 1 "Not in this version": strike "Cancelling another person's booking", add a pointer to B-33)
- Test: `tests/test_migrations.py`, `tests/test_schema.py`, `tests/test_bookings_cancel.py`, `tests/test_room_booking_guards.py`, `tests/test_bookings_read.py`

**Interfaces:**
- Produces:
  - Columns: `bookings.cancelled_by` FK users null (`ondelete/onupdate RESTRICT`, index not needed); `booking_reviews.by_admin` Boolean NOT NULL server default false; `booking_rejections.by_admin` Boolean NOT NULL server default false.
  - `transitions.cancel(session, booking, version, reason, actor_id: int | None)`; `transitions.reject(..., by_admin: bool = False)` passes `by_admin` to both the rejection and its review row; `booking_review._add_review(booking, stage, current, notes, now, by_admin: bool = False)`.
  - `BookingDetail.cancelled_by: PersonRef | None`; `ReviewOut.by_admin: bool`; `RejectionOut.by_admin: bool`.
  - Spec rows: B-33 (Admin cancel, D-32/35/37/38), B-34 (Admin as backup reviewer, D-33/34/40), B-35 (actor recorded, D-36), B-36 (no notification, D-39).

- [ ] **Step 1: Write failing tests:** `test_migrations` / `test_schema` expect the three columns; `test_booker_cancel_records_actor` (booker cancels → `cancelled_by.id == booker.id` in `GET /bookings/{id}`); in `test_room_booking_guards`, the B-27 test also asserts `cancelled_by is None`; `test_bookings_read` asserts `reviews[0].by_admin is False` and `rejection.by_admin is False` on factory data.
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_migrations.py tests/test_schema.py tests/test_bookings_cancel.py tests/test_room_booking_guards.py tests/test_bookings_read.py -q`. Expected: FAIL (missing columns/fields).
- [ ] **Step 3: Implement** migration, models, transitions, callers, view and schemas; write the spec notes.
- [ ] **Step 4: Run** the same tests, then `pytest -q` and `ruff check .`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Booking: record who cancelled, and Admin reviews and rejections (B-35)"`.

### Task 2: Admin actions API

**Files:**
- Create: `app/services/booking_admin.py`, `app/routers/admin_bookings.py`, `app/schemas/booking_admin.py`
- Modify: `app/services/booking_review.py` (extract the Pitika and owner approve steps into helpers the Admin path calls), `app/main.py` (include router), `admin_dashboard/src/api/schema.d.ts` (regenerate from `app.openapi()`)
- Test: `tests/test_admin_booking_actions.py`, `tests/test_booking_concurrency.py`

**Interfaces:**
- Consumes: Task 1; `booking_access.load_booking_for_write`, `booking_access.room_province`, `booking_scheduling.active_pitika_count`, `transitions.check_version / cancel / reject / has_started / has_ended / invalid_transition`.
- Produces:
  - `booking_review.approve_pitika_stage(session, booking, actor: CurrentUser, notes, *, by_admin: bool) -> None` and `approve_owner_stage(session, booking, actor, notes, *, by_admin: bool) -> None` (the write half of `pitika_approve` / `owner_approve`; those keep their checks and call these).
  - `booking_admin.allowed_actions(session, booking) -> dict` → `{"cancel": bool, "approve": bool, "reject": bool, "stage": "PITIKA" | "OWNER" | None}` (stage = which step approve/reject would act on; both false and stage None for SETUP_IN_PROGRESS, final, ended, or Pitika stage with an active Pitika).
  - `booking_admin.admin_cancel(session, current, booking_id, reason, version) -> Booking`, `admin_approve(session, current, booking_id, notes, version) -> Booking`, `admin_reject(session, current, booking_id, reason, version) -> Booking`.
  - Schemas: `AdminActionsOut{cancel, approve, reject, stage}`; `AdminRejectBody{reason: OptionalBookingText(1000, min_length=5) = None, version: int}`; cancel reuses `CancelBody`, approve reuses `ApproveBody`.
  - Routes (all `AdminUser`, prefix `/admin/bookings`, tag "Admin bookings"): `GET /{id}/actions` → `AdminActionsOut`; `POST /{id}/cancel`, `POST /{id}/approve`, `POST /{id}/reject` → `BookingDetail`.

- [ ] **Step 1: Write failing tests** in `tests/test_admin_booking_actions.py` (fixtures from `tests/booking_helpers.py`, `frozen`; Admin = `make_user(roles=["ADMIN"])`):
  - cancel: each of PENDING_PITIKA, PENDING_OWNER, SETUP_IN_PROGRESS, CONFIRMED → 200, status CANCELLED, `cancelled_by.id == admin.id`, sessions not blocking, food/IT rows kept; ended CONFIRMED → 409 "This booking has ended."; REJECTED → 409 INVALID_TRANSITION; no reason → `cancel_reason is None`; `"<b>x</b>"` → 422 `fields.reason`; Admin who is the booker → `cancelled_by` = themselves.
  - approve, Pitika stage: province with no active Pitika → R1 goes CONFIRMED with door pass, review `{stage: PITIKA, decision: APPROVED, by_admin: true, reviewer.id: admin}`, food `decided_by` = admin; R2 → PENDING_OWNER; with IT → SETUP_IN_PROGRESS; province with an active Pitika → 403 "This office has an active Pitika. Ask them to decide."; after first start → 409 TIME_PASSED.
  - approve/reject, owner stage: PENDING_OWNER → approve gives CONFIRMED (or IT setup) with review `{stage: OWNER, by_admin: true}`; reject → REJECTED, `rejection{rejected_by: OWNER, by_admin: true, actor.id: admin}`; reject with no reason → reason "Rejected by the Admin.".
  - SETUP_IN_PROGRESS: approve and reject → 409 INVALID_TRANSITION (D-40).
  - `STALE_VERSION` on an old version (checked before status).
  - `GET /actions`: one case per row of the `allowed_actions` table above.
  - Non-Admin (STAFF, PITIKA) → 403 on all four routes; missing booking → 404.
  - In `tests/test_booking_concurrency.py`: two Admins call `admin_approve` and `admin_cancel` on the same PENDING_OWNER booking at the same moment (service calls, `threading.Barrier`) → one success, one `STALE_VERSION`, at most one OWNER review row.
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_admin_booking_actions.py -q`. Expected: FAIL (404 routes).
- [ ] **Step 3: Implement** the helpers, service, schemas and router; include the router in `main.py`.
- [ ] **Step 4: Run** the new tests, `tests/test_pitika_bookings.py tests/test_owner_bookings.py tests/test_booking_concurrency.py`, then `pytest -q` and `ruff check .`. Expected: PASS.
- [ ] **Step 5: Regenerate types:** dump `app.openapi()` to a file and run `npx --yes openapi-typescript@7.13.0 <file> -o admin_dashboard/src/api/schema.d.ts`; the diff adds the four routes and the new fields only.
- [ ] **Step 6: Commit** `git commit -m "Booking: Admin cancel, and approve or reject as backup reviewer (B-33, B-34)"`.

### Task 3: Dashboard buttons in the booking panel

**Files:**
- Modify: `admin_dashboard/src/api/bookings.ts`, `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/views/bookings/BookingPanel.vue`, `admin_dashboard/src/views/BookingsView.vue` (reload record and list after an action)
- Test: `admin_dashboard/src/api/__tests__/bookings.spec.ts`, `admin_dashboard/src/views/__tests__/booking-panel.spec.ts`

**Interfaces:**
- Consumes: Task 2 routes and types.
- Produces:
  - `types.ts`: `AdminActionsOut`, `AdminRejectBody`.
  - `bookings.ts`: `getAdminActions(client, id)`, `adminCancel(client, id, body: { reason?: string | null; version: number })`, `adminApprove(client, id, body: { notes?: string | null; version: number })`, `adminReject(client, id, body: { reason?: string | null; version: number })`.
  - `BookingPanel` emits `changed: [booking: BookingDetail]`; `BookingsView` replaces the open record with it and calls `refresh(id)`.
  - Panel foot (left to right): "Close" · then only the allowed ones: "Cancel booking" (quiet, crimson text), "Reject", "Approve" (primary). Each opens an inline step at the bottom of the panel body (never a browser dialog): title ("Cancel this booking?" / "Reject this booking?" / "Approve this booking?"), one line of what happens ("The room is free again. The booker sees the reason when they open the booking." / "It goes to the room owner next." etc., from `stage` and route), a textarea "Reason (optional)" or "Notes (optional)" with `n/500` (`n/1000` for notes and reject), "Back" and the confirm button ("Cancel booking" / "Reject" / "Approve"). Stage label under the title when acting for someone: "You act for Pitika" / "You act for the room owner".
  - After success: toast "{reference} cancelled|approved|rejected", emit `changed`, reload actions. On error: the API message in the step; `fields.reason`/`fields.notes` under the textarea; on 403/409 also reload actions (the buttons follow the server).
  - History: `cancelled_by` → "Cancelled by {name}"; a review or rejection with `by_admin` adds "(Admin, for Pitika)" / "(Admin, for the owner)" after the name.

- [ ] **Step 1: Write failing tests.**
  - `bookings.spec.ts`: `adminReject(api, 12, { reason: null, version: 3 })` posts `/api/v1/admin/bookings/12/reject` with `{"reason":null,"version":3}`.
  - `booking-panel.spec.ts`: actions `{cancel: true, approve: false, reject: false, stage: null}` → only "Cancel booking" shows; actions all false → no action buttons; Cancel → step → confirm with empty reason posts `{"reason":null,"version":1}`, shows the toast, and the panel shows the new status; a 409 "This booking has ended." shows in the step and refetches actions (buttons gone); a 403 on approve shows the message and refetches actions; a 422 `fields.reason` shows under the textarea; stage OWNER shows "You act for the room owner"; history shows "Cancelled by Chan Admin" and "Pitika approved · Chan Admin (Admin, for Pitika)".
- [ ] **Step 2: Run** `npx vitest run src/api/__tests__/bookings.spec.ts src/views/__tests__/booking-panel.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again, then `npx vitest run`, `npm run lint`, `npm run type-check`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: Admin can cancel, approve and reject from the booking panel"`.

### Task 4: Notes, end-to-end and verification

**Files:**
- Modify: `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (DSH-B07 Admin actions row; section 4 wording), `admin_dashboard/README.md` (Bookings section), `DESIGN.md` (Booking Panel: action buttons and the inline confirm step), `admin_dashboard/e2e/bookings-layout.spec.ts` (mocked: panel with actions at 390 px has no sideways scroll and the step fits)

- [ ] **Step 1: Mocked e2e:** `/bookings?id=100` with actions all true at 1366 and 390 px → the three buttons visible, open the Cancel step, no sideways scroll in the panel.
- [ ] **Step 2: Notes** as listed above.
- [ ] **Step 3: Full verification:** API `pytest -q`, `ruff check .`; dashboard `npm run lint`, `npm run type-check`, `npx vitest run`, `npm run build-only`, `npx playwright test e2e/bookings-layout.spec.ts`. Expected: all pass.
- [ ] **Step 4: Commit** `git commit -m "Docs: Admin booking actions"`.
