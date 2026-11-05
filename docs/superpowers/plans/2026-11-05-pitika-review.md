# Pitika To Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Pitika signs in to the admin dashboard, sees only their menu, and approves or rejects the bookings waiting for them on a "To review" page grouped by urgency, with room photos and a process bar.

**Architecture:** Roles decide routes and menu: each route lists the roles that may open it (`meta.roles`), the guard and the rail read the user's role codes. The To review page lists `GET /pitika/bookings?status=PENDING_PITIKA`, loads each waiting booking's detail (for the food/IT/private labels) and the rooms (for cover photos), and groups rows with pure functions in `utils/reviewQueue.ts`. Decisions go through the existing Ledger pop-up (`BookingActionDialog`), which gains a minimum length for the reject reason. No API change.

**Tech Stack:** Vue 3 `<script setup lang="ts">`, Vue Router, Pinia, Vitest + @vue/test-utils, Playwright, Lucide icons.

**Spec:** `docs/superpowers/specs/2026-11-05-pitika-review-design.md` (look and copy); `DESIGN.md` (tokens, Side Panel, Booking Panel, History); API: `app/routers/pitika_bookings.py`.

## Global Constraints

- Role codes are the API's: `ADMIN`, `PITIKA` (from `GET /me` → `roles[].code`).
- Reject reason: 5 to 1000 characters, required. Approve notes: optional, up to 1000.
- Days are Phnom Penh days (`usePhnomPenhToday`, `utils/time.ts`); session dates are already Phnom Penh, times "HH:MM".
- Photo `<img src>` is `${apiBaseUrl}${thumbnail_url}` (as in `RoomPhotos.vue`); the header uses `url`.
- No class names that are Tailwind utilities (`grid`, `table`, `flex`, `hidden`, `block`, …) in components.
- Copy is the spec's, word for word.

## Review Focus

- A Pitika with no province (no division): the API returns an empty list → the empty state shows, not an error. Test in Task 4.
- A booking decided by someone else meanwhile (409 INVALID_TRANSITION / STALE_VERSION): the pop-up shows the API message and the queue reloads, removing the row. Test in Task 5.
- The first session already started while waiting: Today pill reads "Started"; Approve answers 409 TIME_PASSED, shown in the pop-up; Reject still works. Test in Tasks 3 and 5.
- A room with no photo: the row and the header show the paper tile with a door icon, never a broken image. Test in Task 4.
- A user who is both Admin and Pitika: both menus, home stays Rooms. Test in Task 1.

---

### Task 1: Roles decide routes and menu

**Files:**
- Modify: `admin_dashboard/src/stores/session.ts` (expose `roleCodes: ComputedRef<string[]>`)
- Modify: `admin_dashboard/src/router/guard.ts`, `admin_dashboard/src/router/index.ts` (route `meta.roles`, new route `review`, path `/review`, placeholder view until Task 4)
- Modify: `admin_dashboard/src/layouts/nav.ts`, `admin_dashboard/src/layouts/AppRail.vue`
- Test: `admin_dashboard/src/router/__tests__/guard.spec.ts`, `admin_dashboard/src/layouts/__tests__/nav.spec.ts` (new)

**Interfaces:**
- Produces: `SessionState = { signedIn: boolean; mustChangePassword: boolean; roles: string[] }`; `RouteMeta.roles?: string[]` (no `roles` = every dashboard role, e.g. profile); `DASHBOARD_ROLES = ['ADMIN', 'PITIKA']`; `homeFor(roles: string[]): string` → `'home'` when ADMIN, else `'review'` when PITIKA; `navFor(roles: string[]): NavGroup[]`; `NavItem.roles?: string[]`.
- Route roles: every existing shell route `['ADMIN']` except `bookings` and `food-list` `['ADMIN', 'PITIKA']`, `profile` none; `review` `['PITIKA']`.

- [ ] **Step 1: Failing guard tests** — replace `isAdmin` with `roles` in the fixtures, and add:
  - `pitika = { signedIn: true, mustChangePassword: false, roles: ['PITIKA'] }`: `resolveNavigation(nav('review','/review'), pitika)` → `true`; `nav('offices', …)` with `meta.roles ['ADMIN']` → `{ name: 'review' }`; `SIGN_IN` → `{ name: 'review' }`; `NO_ACCESS` → `{ name: 'review' }`.
  - `staff` (`roles: ['STAFF']`) → any shell page `{ name: 'no-access' }`.
  - `both` (`['ADMIN','PITIKA']`): `HOME` → `true`, `review` → `true`, `SIGN_IN` → `{ name: 'home' }`.
  - `Nav` gains `meta.roles?: string[]`.
- [ ] **Step 2: Run** `npx vitest run src/router/__tests__/guard.spec.ts` — FAIL.
- [ ] **Step 3: Implement** `resolveNavigation`: signed-out and password rules unchanged; no dashboard role → no-access; `sign-in`/`no-access` → `homeFor`; a route whose `meta.roles` shares no role with the user → `homeFor`. The router passes `{ …, roles: session.roleCodes }`.
- [ ] **Step 4: Failing nav tests** (`nav.spec.ts`): `navFor(['ADMIN'])` equals today's groups (Daily: Bookings, Food list, Rooms; then the four setup groups); `navFor(['PITIKA'])` is one group "Daily" with To review (icon `inbox`, route `review`), Bookings, Food list; `navFor(['ADMIN','PITIKA'])` Daily has To review first, then the Admin items.
- [ ] **Step 5: Implement** `navFor` in `nav.ts` (filter items by `roles`, drop empty groups; To review item `{ label: 'To review', icon: 'inbox', route: 'review', roles: ['PITIKA'] }` first in Daily; Bookings and Food list `roles: ['ADMIN','PITIKA']`; others `['ADMIN']`); add `inbox: Inbox` to `NAV_ICONS`. `AppRail.vue` renders `navFor(session.roleCodes)` instead of `NAV_GROUPS`; the rail subtitle reads "Admin" or "Pitika" (first dashboard role).
- [ ] **Step 6: Run** `npx vitest run src/router src/layouts` — PASS (update `shell.spec.ts` only where it relied on `isAdmin`).
- [ ] **Step 7: Commit** `Dashboard: routes and menu follow the user's roles; Pitika gets To review, Bookings, Food list`.

### Task 2: Pitika API and a Bookings page from the Pitika list

**Files:**
- Modify: `admin_dashboard/src/api/bookings.ts`
- Modify: `admin_dashboard/src/views/BookingsView.vue`, `admin_dashboard/src/views/bookings/BookingFilters.vue`, `admin_dashboard/src/views/bookings/BookingPanel.vue`
- Test: `admin_dashboard/src/views/__tests__/bookings-list.spec.ts`, `admin_dashboard/src/views/__tests__/booking-panel.spec.ts`

**Interfaces:**
- Produces: `listPitikaBookingPage(client, params: BookingFilters): Promise<Page<BookingListItem>>` (`GET /api/v1/pitika/bookings`, same params as the Admin list minus `province`); `pitikaApprove(client, id, { notes: string | null; version: number }): Promise<BookingDetail>`; `pitikaReject(client, id, { reason: string; version: number }): Promise<BookingDetail>`.
- `BookingsView` reads `session.isAdmin`: an Admin lists `/bookings`; a Pitika-only user lists `/pitika/bookings` and the province filter is hidden. `BookingPanel` prop `adminActions: boolean` (default `true`): when false it does not call `/admin/bookings/{id}/actions` and shows no action buttons.

- [ ] **Step 1: Failing tests**: a Pitika-only session (`me` with roles `[{ code: 'PITIKA' }]`) on `/bookings` calls `/api/v1/pitika/bookings?page=1&size=20`, has no `#filter-province`; its panel makes no `/admin/bookings/12/actions` call and has no Cancel booking button.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** `npx vitest run src/views/__tests__/bookings-list.spec.ts src/views/__tests__/booking-panel.spec.ts` — PASS.
- [ ] **Step 5: Commit** `Dashboard: Pitika API calls; Bookings lists the Pitika's province for a Pitika`.

### Task 3: Queue rules (pure)

**Files:**
- Create: `admin_dashboard/src/utils/reviewQueue.ts`
- Test: `admin_dashboard/src/utils/__tests__/reviewQueue.spec.ts`

**Interfaces:**
- Consumes: `BookingListItem`, `BookingDetail`, `addDays`, `formatDay`.
- Produces:
  - `type UrgencyKey = 'today' | 'tomorrow' | 'week' | 'later'`
  - `groupByUrgency(items: BookingListItem[], today: string): Array<{ key: UrgencyKey; label: string; hint: string; items: BookingListItem[] }>` — by `first_session.date`: today (or before) → Today, hint "Decide before they start, or they expire"; today+1 → Tomorrow; up to the coming Sunday → This week; after → Later; empty groups dropped; order kept.
  - `startsIn(item: BookingListItem, now: Date): string` — Phnom Penh: "Starts in 4 h 40 min", "Starts in 25 min", "Started" once `first_session.start_time` on its date has passed.
  - `rowSteps(item: BookingListItem): Array<{ label: string; state: 'done' | 'todo'; gap?: boolean }>` — `[{Sent, done}, …after]` where after = `Room owner` (R2), `IT setup` (has_it and not R3), `Confirmed`; the first after-step has `gap: true`.
  - `checkLabels(detail: BookingDetail): Array<{ kind: 'private' | 'food' | 'it' | 'r4'; text: string; count?: number }>` — R2: `{private, 'Private · reason given' | 'Private · no reason'}`; food: package names joined ", " with `count` servings; IT: item names joined ", "; R4: `{r4, 'Food and IT only'}`.
  - `nextStepText(detail: BookingDetail): string` — the spec's three sentences, plus " The food is approved with it." when `catering` is set.

- [ ] **Step 1: Failing tests**, with today `2026-11-05` (a Thursday): items on 11-05 → Today, 11-06 → Tomorrow, 11-08 → This week, 11-09 → Later; 11-04 (started, still waiting) → Today. `startsIn` at `2026-11-05T02:20:00Z` (09:20) for a 14:00 session → "Starts in 4 h 40 min"; 09:45 → "Starts in 25 min"; 09:00 → "Started". `rowSteps` R1 no IT → Sent, Confirmed(gap); R1 with IT → Sent, IT setup(gap), Confirmed; R2 → Sent, Room owner(gap), Confirmed; R2 with IT → Sent, Room owner(gap), IT setup, Confirmed. `checkLabels` for each label kind; `nextStepText` for R2, IT, plain, and with food.
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/reviewQueue.spec.ts` — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `Dashboard: review queue rules (urgency groups, starts in, row steps, check labels)`.

### Task 4: The To review page

**Files:**
- Create: `admin_dashboard/src/views/ReviewView.vue`, `admin_dashboard/src/components/ProcessBar.vue`, `admin_dashboard/src/components/RoomPhoto.vue`
- Modify: `admin_dashboard/src/router/index.ts` (route `review` → `ReviewView`)
- Test: `admin_dashboard/src/views/__tests__/review.spec.ts`

**Interfaces:**
- Consumes: Task 2 `listPitikaBookingPage`; Task 3 functions; `getBooking`; `listAllRooms` (`cover_photo.thumbnail_url | url`); `apiBaseUrl`.
- Produces: `ProcessBar` props `{ steps: Array<{ label: string; state: 'done' | 'stop' | 'now' | 'todo'; gap?: boolean }>; size?: 'small' | 'large' }` (look per spec; `gap` draws the dashed amber line into that step). `RoomPhoto` props `{ path: string | null; alt: string }` (img or paper tile with `DoorOpen`). The page emits nothing; it owns the open booking via `?id=` like BookingsView (`usePanelParam`).

- [ ] **Step 1: Failing tests** (fake Date 2026-11-05T02:20:00Z; fetch stub): lists `?status=PENDING_PITIKA&page=1&size=100`; renders group heads in order with counts; a row shows the reference, title, Khmer and English room, first session, booker, attendees, the check labels from the detail, the Today pill only on today's row, the ProcessBar with a `.gap` step; a room without a cover shows `.room-photo.none`; the empty list shows "Nothing to review"; the count in the head reads "001 waiting".
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/review.spec.ts` — FAIL.
- [ ] **Step 3: Implement** `ReviewView.vue`: page head "To review" + mono count "{n} waiting"; sub "Bookings of rooms in your province waiting for your decision, the most urgent first. Approving also approves the food and IT."; filters: `ListSearch` (`q`) and the room `SearchPicker` (`room_id`); the sheet with sticky group heads; rows as `role="list"`/`listitem`, Enter or click opens the panel; details loaded with `Promise.allSettled` (a failed detail leaves its labels out); rooms loaded once. Today's pill refreshes with `usePhnomPenhToday`'s minute tick (`startsIn` re-evaluated each minute).
- [ ] **Step 4: Run** — PASS. **Step 5: Commit** `Dashboard: Pitika To review queue grouped by urgency, with room photos and the row bar`.

### Task 5: Review panel and decisions

**Files:**
- Create: `admin_dashboard/src/views/bookings/ReviewPanel.vue`
- Modify: `admin_dashboard/src/views/bookings/BookingActionDialog.vue` (prop `minLength?: number`, default 0), `admin_dashboard/src/views/ReviewView.vue`
- Test: `admin_dashboard/src/views/__tests__/review.spec.ts`, `admin_dashboard/src/views/__tests__/booking-panel.spec.ts` (dialog `minLength`)

**Interfaces:**
- Consumes: Task 2 `pitikaApprove`/`pitikaReject`; Task 3 `nextStepText`, `startsIn`; Task 4 `ProcessBar`, `RoomPhoto`; `buildHistory(detail).steps` for the full bar.
- Produces: `ReviewPanel` props `{ booking: BookingDetail; coverUrl: string | null; headerUrl: string | null; startsIn: string | null }`, emits `close`, `approve`, `reject`. `BookingActionDialog` with `minLength > 0`: confirm disabled until `[...text.trim()].length >= minLength`, hint "At least 5 characters." (from `minLength`) under the box while short.

- [ ] **Step 1: Failing tests**: opening a row shows the panel with the header photo, the title, "Waiting for Pitika · NBC-…", the large ProcessBar with Pitika `now`, the R4 note on an R4 booking, Meeting/Food/IT sections. Approve → dialog "Approve this booking?" with `nextStepText`; confirm posts `/api/v1/pitika/bookings/12/approve` `{ notes: null, version: 1 }`, the row leaves, toast "NBC-26-48213 approved". Reject → confirm disabled with "At least 5 characters.", enabled after "Room closed", posts `{ reason: 'Room closed', version: 1 }`, toast "… rejected". A 409 answer shows its message in the dialog and reloads the list (one more list call). TIME_PASSED on approve shows "The meeting has started. It cannot be approved." (the API's text) in the dialog.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement** (approve/reject buttons in rows open the same dialog without opening the panel). **Step 4: Run** `npx vitest run` — all PASS.
- [ ] **Step 5: Commit** `Dashboard: Pitika review panel; approve with notes, reject with a reason of 5+ characters`.

### Task 6: Browser checks and design notes

**Files:**
- Create: `admin_dashboard/e2e/review-layout.spec.ts`
- Modify: `DESIGN.md` (Navigation: roles; a "Review Queue" section from the spec), `admin_dashboard/README.md` (Pitika sign-in)

- [ ] **Step 1:** Playwright (API mocked like `bookings-layout.spec.ts`, `me` with role PITIKA): at 1366, 900 and 390 the queue has no sideways scroll; the rail shows only To review, Bookings, Food list; every row's Approve button sits inside the sheet; the panel and the reject dialog fit; the reject confirm is disabled until 5 characters.
- [ ] **Step 2: Run** `npx playwright test e2e/review-layout.spec.ts` — PASS; then the full suite, `npx vue-tsc --noEmit -p tsconfig.app.json`, `npx eslint src e2e`.
- [ ] **Step 3: Commit** `Dashboard: browser checks and design notes for the Pitika To review page`.
