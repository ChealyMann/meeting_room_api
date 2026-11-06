# Room owner pages (Part A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Room owner gets the Pitika-style To review (queue, ring, Waiting · Approved · Rejected) for bookings of their private rooms, and a Bookings list of their rooms; the To review menu items get a waiting count.

**Architecture:** Backend: the Pitika's decided-list and summary queries become shared helpers taking a review stage and a room subquery; the owner router gets `from`/`to`, `/decided` and `/summary`. Dashboard: one reviewer config per role (`pitika`, `owner`) holds the API calls and the per-role rules; `ReviewView`, `DecidedList` and `ReviewPanel` read it, so the owner page is the Pitika page with another config. Roles, home, menu and the Bookings source learn ROOM_OWNER.

**Tech Stack:** FastAPI, SQLAlchemy 2, MySQL, pytest; Vue 3 + TypeScript, vue-router, Pinia, vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-05-owner-and-it-pages-design.md` (Part A and "Shared"), building on `2026-11-05-pitika-review-design.md` and `2026-11-05-pitika-decided-design.md`.

## Global Constraints

- Schemas, routers and services: one file per resource; models: one class per file.
- Never use class names that clash with Tailwind utilities or `main.css` globals (`grid`, `table`, `flex`, `hidden`, `ring`, `border`, `shadow`, `switch`, `sheet`, …). Check each new class name.
- Phnom Penh time for days and times. No new booking rules; read only after a decision.
- The Pitika pages must behave exactly as before (their existing tests pass unchanged, except where a test named a Pitika-only symbol that is now generic).
- Commit messages plain, no Claude attribution lines.
- Gate at the end: `ruff check app tests`, `ruff format --check` on changed files, `pytest -q`, `npx vitest run`, `npx vue-tsc --noEmit -p tsconfig.app.json`, `npx eslint src e2e` (no new warnings), `npx playwright test`.

## Review Focus

1. **The room gets a new owner** (BR-OWN-05: the queue follows the room). The new owner sees its waiting bookings; the old owner's Approved list no longer lists them (rooms owned **now**). Pinned in Task 1.
2. **R2 approve without IT vs with IT.** Without IT the next step text is "It is confirmed, with a door pass."; with IT "It goes to IT setup next.". The row bar is Sent ✓ · Pitika ✓ · gap · (IT setup) · Confirmed. Pinned in Task 3.
3. **Seats unknown** (the rooms list failed, or the room is missing from it): no seats label, never "NaN seats" or "undefined". Pinned in Task 3.
4. **Pitika notes after an Admin backup approval** (the PITIKA review has `by_admin = true`): the owner still sees "Pitika notes" and the text. Pinned in Task 3.
5. **A user who is Pitika and Room owner:** two separate pages ("To review" for Pitika, "My rooms" for owner), each with its own list and counts; Bookings shows once and uses the Pitika list. Pinned in Task 2 and Task 5.

---

### Task 1: API: owner dates, decided list and summary

**Files:**
- Modify: `app/services/booking_review.py` (shared `_list_decided`, `_decided_summary`; owner versions; owner list `from`/`to`)
- Modify: `app/routers/owner_bookings.py` (`from`/`to`; `GET /decided`; `GET /summary`)
- Test: `tests/test_owner_decided.py`; `tests/test_owner_bookings.py` (dates)

**Interfaces:**
- Produces: `GET /api/v1/owner/bookings?from&to` (plus existing `status`, `room_id`, `q`, `page`, `size`); `GET /api/v1/owner/bookings/decided?decision=APPROVED|REJECTED&q&room_id&from&to&page&size` → `Page[DecidedBookingItem]`; `GET /api/v1/owner/bookings/summary` → `PitikaSummary` shape `{ waiting, approved_today, rejected_today }` (reuse the schema; rename the class to `ReviewSummary` and keep `PitikaSummary = ReviewSummary` so the dashboard types stay valid until regenerated).
- `_list_decided(session, current, stage: ReviewStage, rooms, page, size, decision, date_from, date_to, room_id, q) -> dict` and `_decided_summary(session, current, stage, rooms, waiting_status: BookingStatus) -> dict[str, int]`; `list_pitika_decided` / `pitika_summary` call them (their tests must pass unchanged). `booking_view.build_decided_items(bookings, reviewer_id, stage)` gains `stage`.
- Owner rooms subquery: `select(Room.id).where(Room.is_private, Room.room_owner_id == current.id)` (as `list_owner_bookings` uses now).

- [ ] **Step 1: Failing tests** (`tests/test_owner_decided.py`, fixtures like `tests/test_owner_bookings.py`'s `owner`/`waiting`, helpers like `tests/test_pitika_decided.py`):
  - `test_lists_my_owner_approvals_newest_first` (two approvals one hour apart; `decided_at` of the newest `"2026-11-09T02:00:00Z"`; notes `"Ok"` as `decision_note`).
  - `test_lists_my_owner_rejections_with_reason`.
  - `test_pitika_review_not_in_owner_list`: a booking whose only review by me is a PITIKA review (I am Pitika too) is not listed.
  - `test_new_owner_takes_the_queue` (Review Focus 1): approve as owner A; set `room.room_owner_id` to B → A's decided total 0; B's summary `waiting` counts the room's other PENDING_OWNER booking.
  - `test_admin_backup_not_listed_or_counted` (direct `BookingReview(stage=OWNER, reviewer_id=me, by_admin=True)` row).
  - `test_filters` (q, room_id, from/to, `to < from` → 422 `fields.to`); `test_decision_required_and_checked`; `test_forbidden_for_staff_and_pitika` (403).
  - `test_summary_counts_today` → `{"waiting": 2, "approved_today": 2, "rejected_today": 1}` with one approval the day before; `test_summary_day_is_phnom_penh` (23:50 / 00:30 as in the Pitika test).
  - `test_query_count_does_not_grow` (1 vs 5 decided).
  - In `tests/test_owner_bookings.py`: `test_list_from_to_match_any_session` (copy of the Pitika one, owner list).
- [ ] **Step 2: Run** `pytest tests/test_owner_decided.py tests/test_owner_bookings.py -q` → FAIL (404 / unknown params ignored).
- [ ] **Step 3: Implement** the shared helpers and the owner endpoints; `_my_review(current, stage)` replaces `_my_pitika_review`.
- [ ] **Step 4: Run** `pytest tests/test_owner_decided.py tests/test_owner_bookings.py tests/test_pitika_decided.py tests/test_pitika_bookings.py -q` → PASS; `ruff check app tests`.
- [ ] **Step 5: Commit** `API: owner list dates, owner decided list and summary (shared with Pitika)`.

### Task 2: Dashboard: Room owner role, home, menu and route

**Files:**
- Modify: `admin_dashboard/src/router/guard.ts`, `admin_dashboard/src/router/index.ts`, `admin_dashboard/src/layouts/nav.ts`, `admin_dashboard/src/layouts/AppRail.vue`, `admin_dashboard/src/stores/session.ts`
- Test: `src/router/__tests__/guard.spec.ts`, `src/layouts/__tests__/nav.spec.ts`, `src/stores/__tests__/` (session), `src/layouts/__tests__/shell.spec.ts` if it pins the subtitle

**Interfaces:**
- `DASHBOARD_ROLES = ['ADMIN', 'PITIKA', 'ROOM_OWNER']` (IT roles come in Part B).
- `homeFor`: ADMIN → `home`, PITIKA → `review`, ROOM_OWNER → `owner-review`, else `no-access`.
- Route `{ path: 'owner-review', name: 'owner-review', component: ReviewView, props: { reviewer: 'owner' }, meta: { title: 'To review', roles: ['ROOM_OWNER'] } }`; `review` gets `props: { reviewer: 'pitika' }`. `bookings` roles add `ROOM_OWNER`.
- `navFor(roles)`: owner item `{ label: 'To review', icon: 'inbox', route: 'owner-review', roles: ['ROOM_OWNER'] }` after the Pitika's To review; its label is **"My rooms"** (icon `door-open`) when `roles` has PITIKA too. Bookings `roles: ['ADMIN', 'PITIKA', 'ROOM_OWNER']`.
- Rail subtitle: first of Admin, Pitika, Room owner the user has.
- Session store: `bookingsSource: ComputedRef<'admin' | 'pitika' | 'owner'>` (Admin first, then Pitika, then owner); keep `pitikaOnly` working (it equals `bookingsSource === 'pitika'`).

- [ ] **Step 1: Failing tests:** guard: owner-only lands on `owner-review`; owner opening `offices` → `owner-review`; owner on `review` (Pitika page) → `owner-review`; Staff-only still `no-access`. nav: `navFor(['ROOM_OWNER'])` → Daily: To review (route `owner-review`), Bookings; `navFor(['PITIKA','ROOM_OWNER'])` → To review (`review`), My rooms (`owner-review`), Bookings, Food list; Admin unchanged. Session: `bookingsSource` for `['ROOM_OWNER']` = owner, `['PITIKA','ROOM_OWNER']` = pitika, `['ADMIN','ROOM_OWNER']` = admin. Rail subtitle "Room owner" for an owner.
- [ ] **Step 2: Run** `npx vitest run src/router src/layouts src/stores` → FAIL.
- [ ] **Step 3: Implement.** `ReviewView` gets `defineProps<{ reviewer?: 'pitika' | 'owner' }>()` (default `'pitika'`) in this task only so the route compiles; Task 4 uses it.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `Dashboard: Room owner role: home, menu (My rooms beside Pitika) and route`.

### Task 3: Dashboard: owner API calls and queue rules

**Files:**
- Modify: `admin_dashboard/src/api/schema.d.ts` (regenerate with the API running: `npm run gen:api`), `src/api/types.ts` (`ReviewSummary`), `src/api/bookings.ts`
- Create: `admin_dashboard/src/utils/ownerQueue.ts`
- Test: `src/utils/__tests__/ownerQueue.spec.ts`, `src/api/__tests__/bookings.spec.ts`

**Interfaces:**
- API calls: `listOwnerBookingPage(client, f: BookingFilters)` (`/api/v1/owner/bookings`, no `province`), `ownerApprove(client, id, { notes, version })`, `ownerReject(client, id, { reason, version })`, `listOwnerDecidedPage(client, f & { decision })`, `getOwnerSummary(client)`.
- `ownerRowSteps(item: BookingListItem): RowStep[]` → Sent done, Pitika done, then `gap` into the first of: IT setup (when `has_it`), Confirmed.
- `ownerCheckLabels(b: BookingDetail, seats: number | null): OwnerLabel[]` with `OwnerLabel = { kind: 'private' | 'governor' | 'seats' | 'pitika-notes'; text: string; over?: boolean }`: "Private · reason given" / "Private · no reason"; "With Governor" for `INTERNAL_WITH_GOVERNOR` / `EXTERNAL_WITH_GOVERNOR`; `"25 people · 20 seats"` with `over: true` when attendees > seats, left out when `seats` is null; "Pitika notes" when the PITIKA-stage review (any `by_admin`) has notes.
- `pitikaNotes(b: BookingDetail): string | null` (that review's notes).
- `ownerNextStepText(b)`: `has_it` → "It goes to IT setup next." else "It is confirmed, with a door pass.".

- [ ] **Step 1: Failing tests** for each function, including Review Focus 2 (R2 with and without IT: steps and next text), 3 (`seats` null → no seats label; 25 vs 20 → `over: true`; 10 vs 20 → no `over`), 4 (PITIKA review `by_admin: true`, notes "Check the projector" → label and `pitikaNotes`). API calls: exact URLs and bodies (`/api/v1/owner/bookings/12/approve` `{ notes: null, version: 3 }`; decided `?decision=REJECTED&page=1&size=20`; summary).
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/ownerQueue.spec.ts src/api` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS; `npx vue-tsc --noEmit -p tsconfig.app.json`.
- [ ] **Step 5: Commit** `Dashboard: owner API calls and queue rules (row steps, what to check, next step)`.

### Task 4: Dashboard: one To review page for both reviewers

**Files:**
- Create: `admin_dashboard/src/views/review/reviewers.ts`
- Modify: `src/views/ReviewView.vue`, `src/views/review/DecidedList.vue`, `src/views/bookings/ReviewPanel.vue`
- Test: `src/views/__tests__/owner-review.spec.ts` (new); `src/views/__tests__/review.spec.ts` and `src/views/review/__tests__/*` must still pass

**Interfaces:**
- `interface Reviewer { key: 'pitika' | 'owner'; waitingStatus: 'PENDING_PITIKA' | 'PENDING_OWNER'; waitingLabel: string; list; approve; reject; decided; summary; rowSteps(item); labels(detail, seats): Array<{ kind: string; text: string; over?: boolean; count?: number }>; nextStepText(detail): string; panelNote(detail): string | null; rooms(all: RoomListItem[], user): RoomListItem[] }` and `export const REVIEWERS: Record<'pitika' | 'owner', Reviewer>`.
  - pitika: today's calls and rules; `waitingLabel` "Waiting for Pitika"; `panelNote` the R4 note; rooms of the user's province.
  - owner: Task 3's calls and rules; `waitingLabel` "Waiting for room owner"; `panelNote` = `The Pitika wrote: “…”` when `pitikaNotes`; rooms with `is_private` and `owner.id === user.id`.
- `ReviewView` props `{ reviewer: 'pitika' | 'owner' }`; everything Pitika-specific reads `REVIEWERS[props.reviewer]`. `DecidedList` and `ReviewPanel` get the `Reviewer` (or its fields) as props; `ReviewPanel` takes `waitingLabel` and `note` instead of hard-coded text.
- Owner label styles: `.chk.governor`, `.chk.seats`, `.chk.seats.over` (crimson), `.chk.pitika-notes`.

- [ ] **Step 1: Failing tests** (`owner-review.spec.ts`, copied setup from `review.spec.ts`, `me` roles `ROOM_OWNER`, fetch stub on `/api/v1/owner/...`, rooms with `capacity` and `owner`): lists `?status=PENDING_OWNER&page=1&size=100`; the row shows "Private · reason given", "With Governor", "25 people · 20 seats" with `.over`, "Pitika notes"; no food/IT labels; the row bar has Sent, Pitika done and a gap; panel subtitle "Waiting for room owner" and the note "The Pitika wrote: “Check the projector”"; approve posts `/api/v1/owner/bookings/21/approve` and the dialog says "It goes to IT setup next."; reject needs 5 characters; summary from `/api/v1/owner/bookings/summary`; Approved tab calls `/api/v1/owner/bookings/decided?decision=APPROVED&page=1&size=20`; the room picker lists only my private rooms.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/owner-review.spec.ts` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `npx vitest run src/views` → PASS (Pitika tests unchanged).
- [ ] **Step 5: Commit** `Dashboard: owner To review: the Pitika page with the owner's queue, checks and decisions`.

### Task 5: Dashboard: owner Bookings list and menu counts

**Files:**
- Modify: `src/views/BookingsView.vue`, `src/views/bookings/BookingFilters.vue`, `src/layouts/AppRail.vue`
- Create: `src/composables/useWaitingCounts.ts`
- Test: `src/views/__tests__/bookings-list.spec.ts`, `src/layouts/__tests__/` (rail counts)

**Interfaces:**
- `BookingsView` picks the list by `session.bookingsSource` (admin → `listBookingPage`, pitika → `listPitikaBookingPage`, owner → `listOwnerBookingPage`); the province filter only for admin; Admin actions only for admin. `BookingFilters` prop `rooms: 'all' | 'province' | 'owned'` for the room picker.
- `useWaitingCounts(): Ref<Record<string, number>>` keyed by route name (`review` from the Pitika summary `waiting`, `owner-review` from the owner summary), loaded once on rail mount and again on a `review:decided` window event that both decision paths dispatch; a failed load leaves the key out. The rail shows a small crimson count after the item's label (hidden at 0 and while unknown; collapsed rail: a dot).

- [ ] **Step 1: Failing tests:** an owner-only session on `/bookings` calls `/api/v1/owner/bookings?page=1&size=20`, has no `#filter-province`, no Admin actions call; its room picker has only owned private rooms. Rail: Pitika with summary `waiting: 3` shows "3" on To review; owner with `waiting: 0` shows no count; Pitika+owner shows both; after a decision the count is fetched again.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/bookings-list.spec.ts src/layouts` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `npx vitest run` → PASS.
- [ ] **Step 5: Commit** `Dashboard: owner Bookings list of my rooms; waiting counts in the menu`.

### Task 6: Browser checks

**Files:**
- Create: `admin_dashboard/e2e/owner-review-layout.spec.ts` (mocks like `review-layout.spec.ts`, `me` roles ROOM_OWNER)

- [ ] **Step 1: Tests:** an owner lands on `/owner-review` and the menu is To review, Bookings; at 1366, 900 and 390 px the queue and the Approved tab have no sideways scroll, every row's Approve sits inside its row, the ring has no box-shadow and the tab bar is wider than 200px; the panel and the reject pop-up fit; the menu count shows on To review.
- [ ] **Step 2: Run** `npx playwright test e2e/owner-review-layout.spec.ts` → PASS; then the gate in Global Constraints.
- [ ] **Step 3: Commit** `Dashboard: browser checks for the owner pages`.
