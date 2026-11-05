# Pitika "Decided by me" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Pitika's To review page gets a "today" ring and three tabs (Waiting · Approved · Rejected); Approved and Rejected list the bookings this Pitika decided, as soft cards, newest decision first, with where each booking is now.

**Architecture:** Two read-only API endpoints on the Pitika bookings router (a decided list and a today summary), built on the existing province-scoped list query. In the dashboard, `ReviewView.vue` keeps the Waiting queue and the shared filter bar; a new head component draws the ring, the summary line and the tab switch; a new list component shows the decided cards and opens `ReviewPanel` read only. The open tab lives in the address (`?tab=approved|rejected`).

**Tech Stack:** FastAPI, SQLAlchemy 2, MySQL, pytest; Vue 3 + TypeScript, vue-router, vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-05-pitika-decided-design.md`

## Global Constraints

- Schemas, routers and services: one file per resource; models: one class per file.
- Tailwind is global: never name a class `grid`, `table`, `flex`, `hidden`, `block`, `inline`, `container` in a component.
- Days and times shown and counted in Phnom Penh time (UTC+7, `app.services.clock`; `usePhnomPenhToday` in the dashboard).
- Only the Pitika's **current** province; reviews with `stage = PITIKA`, `reviewer_id = me`, `by_admin = false`.
- Read only: no new action of any kind on a decided booking.
- Look: "modern and clean": white cards, 12px radius, light shadow (`0 1px 2px rgba(42,28,19,.05)`), 8px gap, few lines. Colours from DESIGN.md tokens (ok `#2F6B3F`, crimson `#991B1B`, warn `#9A4A06`, thread `#E2B33C`).
- Commit messages: plain, no Claude attribution lines.
- All must pass at the end: `ruff check`, `ruff format --check` (on changed files), `pytest`, `npx vitest run`, `npx vue-tsc --noEmit -p tsconfig.app.json`, `npx eslint src e2e`, `npx playwright test e2e/review-layout.spec.ts`.

## Review Focus

1. **Decision near midnight.** A decision at 23:50 Phnom Penh is "yesterday" at 00:30 the next day (UTC is 7 hours behind). Pinned in Task 2 and Task 3.
2. **Approved, then the room owner rejected.** The booking stays on the Approved tab (it is my decision) with a crimson "Rejected" pill; it is not on the Rejected tab. Pinned in Task 1 and Task 3.
3. **Admin backup decisions** (`by_admin = true`) are neither listed nor counted. Pinned in Task 1 and Task 2.
4. **No province / nothing yet.** Empty list, summary all 0, the ring shows "0/0" with no NaN, line "Nothing decided yet today · nothing waiting". Pinned in Task 2 and Task 3.
5. **Switching tabs with `page=3` or an open panel in the address.** The switch drops `page` and the panel key, keeps the filters. Pinned in Task 4.

---

### Task 1: API: the decided list

**Files:**
- Modify: `app/schemas/booking_review.py` (add `DecidedBookingItem`)
- Modify: `app/services/booking_review.py` (add `list_pitika_decided`; share the filters with `_list_in_rooms`)
- Modify: `app/routers/pitika_bookings.py` (add `GET /decided`)
- Test: `tests/test_pitika_decided.py`

**Interfaces:**
- Produces: `GET /api/v1/pitika/bookings/decided?decision=APPROVED|REJECTED&q&room_id&from&to&page&size` → `Page[DecidedBookingItem]`.
- `class DecidedBookingItem(BookingListItem)`: `decided_at: UtcDateTime`, `decision_note: str | None` (approve: the review's notes; reject: the rejection's reason).
- `list_pitika_decided(session, current, page, size, decision: ReviewDecision, date_from, date_to, room_id, q) -> dict` (same `paginate` dict; items are `Booking`).

- [ ] **Step 1: Write the failing tests** in `tests/test_pitika_decided.py` (reuse `pitika`, `pending`, `approve`, `reject` the way `tests/test_pitika_bookings.py` defines them; `URL = "/api/v1/pitika/bookings/decided"`):
  - `test_lists_my_approvals_newest_first`: approve A at NOW, `freeze_now(NOW + 1h)`, approve B → `?decision=APPROVED` ids `[B, A]`; `decided_at` of B ends in `Z` and equals NOW+1h in UTC; `decision_note` is the notes sent (`"Fine"`) or `None`.
  - `test_lists_my_rejections_with_reason`: reject with `"Room is not free."` → `?decision=REJECTED` one item, `decision_note == "Room is not free."`; `?decision=APPROVED` empty.
  - `test_other_pitika_and_admin_backup_not_listed`: a second Pitika of the same province approves C; an Admin backup approval (the existing admin approve path, `by_admin = True`) of D → my list has neither.
  - `test_approved_then_owner_rejected_stays_on_approved` (Review Focus 2): R2 booking, I approve, the room owner rejects → on `APPROVED` with `display_status == "REJECTED"`; `REJECTED` list empty.
  - `test_only_current_province`: approve in Phnom Penh, then move the Pitika's office to Siem Reap → empty; no province → `{"items": [], "total": 0}`.
  - `test_filters`: `q` (title, reference, booker name), `room_id`, `from`/`to` (any session in range), `to` before `from` → 422 `fields.to`.
  - `test_decision_required_and_checked`: no `decision` → 422; `decision=NOT_REQUIRED` → 422.
  - `test_staff_and_admin_forbidden`: 403 for a Staff and an Admin without Pitika.
  - `test_query_count_does_not_grow`: copy the pattern of `test_list_query_count_does_not_grow` (1 vs 5 decided bookings, same query count).

- [ ] **Step 2: Run** `pytest tests/test_pitika_decided.py -q` → FAIL (404 on the route).

- [ ] **Step 3: Implement.** Pull the room/date/search part of `_list_in_rooms` into `_apply_list_filters(query, date_from, date_to, room_id, q) -> Select` (with the `to < from` 422) and use it from both. `list_pitika_decided`: province rooms via `booking_access.pitika_province` / `room_ids_in_province` (no province → empty page); `select(Booking).join(User, requester).join(BookingReview, BookingReview.booking_id == Booking.id)` where `stage == PITIKA`, `reviewer_id == current.id`, `by_admin.is_(False)`, `decision == decision`; order `BookingReview.reviewed_at.desc(), Booking.id.desc()`; load options plus `selectinload(Booking.reviews)` and `selectinload(Booking.rejection)` so the router builds `decided_at` / `decision_note` without per-row queries. `decision` query param typed as a `Literal["APPROVED", "REJECTED"]` (required).

- [ ] **Step 4: Run** `pytest tests/test_pitika_decided.py tests/test_pitika_bookings.py tests/test_admin_bookings.py -q` → PASS.

- [ ] **Step 5: Commit** `API: Pitika decided list (my approvals and rejections, newest first)`.

### Task 2: API: today's summary

**Files:**
- Modify: `app/schemas/booking_review.py` (add `PitikaSummary`)
- Modify: `app/services/booking_review.py` (add `pitika_summary`)
- Modify: `app/routers/pitika_bookings.py` (add `GET /summary`)
- Test: `tests/test_pitika_decided.py`

**Interfaces:**
- Produces: `GET /api/v1/pitika/bookings/summary` → `PitikaSummary { waiting: int, approved_today: int, rejected_today: int }`.
- `pitika_summary(session, current) -> dict[str, int]`.

- [ ] **Step 1: Failing tests:**
  - `test_summary_counts_today`: 6 waiting in Phnom Penh and 1 in Siem Reap; frozen the day before, I approve 1; frozen today, I approve 2 and reject 1 → `{"waiting": 2, "approved_today": 2, "rejected_today": 1}`.
  - `test_summary_day_is_phnom_penh` (Review Focus 1): `freeze_now(datetime(2026, 11, 9, 23, 50))`, approve; `freeze_now(datetime(2026, 11, 10, 0, 30))` → `approved_today == 0`; approve another → 1.
  - `test_summary_skips_admin_backup_and_other_pitika`.
  - `test_summary_without_province_is_zero` → `{"waiting": 0, "approved_today": 0, "rejected_today": 0}`.
  - `test_summary_forbidden_for_staff`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Today's bounds: `clock.local_to_utc(datetime.combine(clock.now_local().date(), time()))` and +1 day, compared with `reviewed_at`. Waiting = count of `status == PENDING_PITIKA` in province rooms. Two count queries at most (waiting; decisions grouped by `decision`).
- [ ] **Step 4: Run** `pytest -q` (whole suite) and `ruff check app tests` → PASS.
- [ ] **Step 5: Commit** `API: Pitika summary (waiting now, approved and rejected today)`.

### Task 3: Dashboard: API calls and decided rules

**Files:**
- Modify: `admin_dashboard/src/api/schema.d.ts` (regenerate: run the API, then `npm run gen:api`)
- Modify: `admin_dashboard/src/api/types.ts` (`DecidedBookingItem`, `PitikaSummary`)
- Modify: `admin_dashboard/src/api/bookings.ts`
- Create: `admin_dashboard/src/utils/decided.ts`
- Test: `admin_dashboard/src/utils/__tests__/decided.spec.ts`, `admin_dashboard/src/api/__tests__/` (where the other booking calls are tested)

**Interfaces:**
- `listPitikaDecidedPage(client, f: BookingFilters & { decision: 'APPROVED' | 'REJECTED' }): Promise<Page<DecidedBookingItem>>`
- `getPitikaSummary(client): Promise<PitikaSummary>`
- `type Tab = 'waiting' | 'approved' | 'rejected'`; `tabFrom(query: unknown): Tab` (anything else → `'waiting'`).
- `groupByDecisionDay(items: DecidedBookingItem[], today: string): { key: string; label: string; items: DecidedBookingItem[] }[]`. The day is the Phnom Penh day of `decided_at`. Labels: `Today · Thu 5 Nov`, `Yesterday · Wed 4 Nov`, then `Mon 2 Nov`.
- `nowPill(item): { text: string; tone: 'warn' | 'ok' | 'no' | 'plain' }`: PENDING_OWNER → "Room owner next"/warn; SETUP_IN_PROGRESS → "IT setup"/plain; CONFIRMED → "Confirmed"/ok; COMPLETED → "Completed"/plain; CANCELLED → "Cancelled"/plain; REJECTED → "Rejected"/no.
- `summaryLine(s: PitikaSummary): string`, `ringArcs(s): { approved: number; rejected: number; label: string }` (fractions 0–1 of the whole; label `"6/9"`).
- `decidedTime(item): string` → `"13:38"` (Phnom Penh).

- [ ] **Step 1: Failing tests** (`decided.spec.ts`, today `2026-11-05`):
  - `groupByDecisionDay`: decided `2026-11-05T06:38:00Z` → Today; `2026-11-04T16:50:00Z` (23:50 PP on 4 Nov) → Yesterday · Wed 4 Nov; `2026-11-04T17:10:00Z` (00:10 PP on 5 Nov) → Today; `2026-11-02T03:00:00Z` → "Mon 2 Nov". Groups newest first; items keep the API order.
  - `nowPill` for each of the six statuses, with the text and tone above.
  - `summaryLine`: `{waiting:3, approved_today:5, rejected_today:1}` → "Today you decided 6 · 3 still waiting"; waiting 0 → "Today you decided 6 · nothing waiting"; decided 0 → "Nothing decided yet today · 3 waiting"; all 0 → "Nothing decided yet today · nothing waiting".
  - `ringArcs`: the same summary → `{ approved: 5/9, rejected: 1/9, label: '6/9' }`; all 0 → `{ approved: 0, rejected: 0, label: '0/0' }` (no NaN).
  - `tabFrom('approved') === 'approved'`, `tabFrom('x') === 'waiting'`, `tabFrom(['rejected']) === 'rejected'`.
  - API calls: `listPitikaDecidedPage` requests `/api/v1/pitika/bookings/decided?decision=APPROVED&page=1&size=20` (filters only when set); `getPitikaSummary` requests `/api/v1/pitika/bookings/summary`.
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/decided.spec.ts src/api` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS; `npx vue-tsc --noEmit -p tsconfig.app.json` → no errors.
- [ ] **Step 5: Commit** `Dashboard: Pitika decided API calls and rules (decision days, now pill, today ring)`.

### Task 4: Dashboard: head with ring, summary line and tabs

**Files:**
- Create: `admin_dashboard/src/views/review/ReviewHead.vue`
- Modify: `admin_dashboard/src/views/ReviewView.vue` (use the head; load the summary; tab switching)
- Test: `admin_dashboard/src/views/__tests__/review.spec.ts` (extend), `admin_dashboard/src/views/review/__tests__/review-head.spec.ts`

**Interfaces:**
- Consumes: Task 3 (`getPitikaSummary`, `summaryLine`, `ringArcs`, `tabFrom`, `Tab`).
- `ReviewHead` props `{ summary: PitikaSummary | null; tab: Tab }`, emits `select: [Tab]`. The ring is 60px (SVG or conic gradient, builder's choice), `role="img"` with `aria-label` "6 of 9 decided today". The switch is `role="tablist"` with three `role="tab"` buttons ("Waiting 3", "Approved 5", "Rejected 1"; numbers hidden until the summary loads), `aria-selected` on the open one, arrow keys move between them.

- [ ] **Step 1: Failing tests:**
  - head: with `{waiting:3, approved_today:5, rejected_today:1}` shows "6/9", "Today you decided 6 · 3 still waiting", tabs "Waiting3", "Approved5", "Rejected1"; clicking Approved emits `select` with `'approved'`; summary `null` → tabs without numbers and no ring label text.
  - review view: on open, calls `/pitika/bookings/summary` once; the old mono "… waiting" count and the old sub line are gone (the summary line replaces them); after an approve, the summary is fetched again.
  - review view (Review Focus 5): at `/review?page=3&id=21&q=board`, clicking the Approved tab goes to `/review?q=board&tab=approved` (page and panel dropped, filter kept); clicking Waiting removes `tab`.
  - review view: `/review?tab=approved` does not render the waiting queue (`.queue` absent) and keeps the filter bar.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/review.spec.ts src/views/review` → FAIL.
- [ ] **Step 3: Implement.** The tab is read with `tabFrom(route.query.tab)`; switching uses `router.replace` building the query from the current one minus `tab`, `page` and the panel key (`id`), plus `tab` unless Waiting. The summary is loaded on mount, after each decision, and when `usePhnomPenhToday()` changes; a failed summary load leaves `summary` null (the page still works).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `Dashboard: To review head with today's ring and Waiting / Approved / Rejected tabs`.

### Task 5: Dashboard: decided cards and the read-only panel

**Files:**
- Create: `admin_dashboard/src/views/review/DecidedList.vue`
- Modify: `admin_dashboard/src/views/bookings/ReviewPanel.vue` (prop `readOnly?: boolean`)
- Modify: `admin_dashboard/src/views/ReviewView.vue` (render `DecidedList` for the two tabs)
- Test: `admin_dashboard/src/views/review/__tests__/decided-list.spec.ts`, `admin_dashboard/src/views/bookings/__tests__/` (panel)

**Interfaces:**
- Consumes: Task 3 (`listPitikaDecidedPage`, `groupByDecisionDay`, `nowPill`, `decidedTime`), `useResourceList` with spec `{ room_id: 'int', from: 'string', to: 'string', q: 'string' }` and `{ activeFilter: false }` (the same address keys as the waiting list, so the shared filter bar drives both), `usePanelParam()`, `getBooking`, `PagingFoot`.
- `DecidedList` props `{ decision: 'APPROVED' | 'REJECTED' }`.
- `ReviewPanel` with `readOnly`: subtitle is `statusLabel(display_status)` instead of "Waiting for Pitika", no "starts in" note, foot shows only Close.

- [ ] **Step 1: Failing tests** (fetch stub, now `2026-11-05T06:40:00Z`):
  - Approved tab calls `/api/v1/pitika/bookings/decided?decision=APPROVED&page=1&size=20`; day heads "Today · Thu 5 Nov" and "Yesterday · Wed 4 Nov" with "2 approved" / "1 approved" on the right; a card shows the green ✓ icon, the title, the reference chip `NBC-26-39730`, "Governor Room · Tue 10 Nov, 14:00 · Touch Bunthoeun", the pill "Room owner next" (`.now.warn`), time "13:38".
  - A card with `decision_note` shows "Notes: “Fine”"; on the Rejected tab "Reason: “Room is closed for repair”" and the crimson ✕ icon.
  - An approved booking with `display_status: 'REJECTED'` shows the crimson "Rejected" pill on the Approved tab (Review Focus 2).
  - Empty: Approved → "No approved bookings yet" / "Bookings you approve show here."; Rejected → "No rejected bookings" / "Bookings you reject show here."; with `q` set → "No bookings match" and a Clear filters button.
  - Click or Enter on a card opens the panel (address gets `id`), loads `/api/v1/bookings/{id}`; the panel subtitle is "Confirmed" (for a confirmed booking), and it has no Approve or Reject button.
  - 25 items (`total: 25`) → `PagingFoot` shows; page 2 calls `page=2`.
- [ ] **Step 2: Run** `npx vitest run src/views/review src/views/bookings` → FAIL.
- [ ] **Step 3: Implement** the cards per the spec ("Approved / Rejected tabs"): icon, title + mono reference chip, second line, optional third line, pill, time; `role="list"` / `listitem`, the whole card is a button-like row (`tabindex="0"`, Enter opens).
- [ ] **Step 4: Run** `npx vitest run` (whole suite) → PASS.
- [ ] **Step 5: Commit** `Dashboard: decided cards by day with where each booking is now; read-only review panel`.

### Task 6: Browser checks

**Files:**
- Modify: `admin_dashboard/e2e/review-layout.spec.ts`

- [ ] **Step 1: Add tests** (same mocked API; add routes for `/api/v1/pitika/bookings/decided` with 3 approved items with long titles and `/api/v1/pitika/bookings/summary`): at 1366, 900 and 390 px, `/review?tab=approved` has no sideways scroll, every card's pill and time sit inside the card, the tab switch fits inside the page head; at 390 px the ring and title stay on one line and the tabs wrap under them; opening a card shows the panel with only a Close button.
- [ ] **Step 2: Run** `npx playwright test e2e/review-layout.spec.ts` → PASS; then `npx vue-tsc --noEmit -p tsconfig.app.json`, `npx eslint src e2e` (no new warnings), `pytest -q`, `ruff check app tests`.
- [ ] **Step 3: Commit** `Dashboard: browser checks for the decided tabs`.
