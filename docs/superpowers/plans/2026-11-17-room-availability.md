# Room availability (Pitika) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Room availability page for Pitika (and Admin): every room's day as a timeline, a "Free at" filter, hover details, and the booking drawer with Approve / Reject.

**Architecture:** Frontend only (`admin_dashboard`). Pure day logic in `src/utils/roomDay.ts`; one page `src/views/RoomAvailabilityView.vue` that loads rooms (`listAllRooms`) and the day (`getDaySchedule`) and reuses `ReviewPanel` + `BookingActionDialog` (waiting for Pitika) or `BookingPanel` (anything else) for the drawer. No backend change: `GET /room-schedule?date=&room_ids=` already returns each room's blocking sessions with status, booking id, code, title, booker, masked flag.

**Tech Stack:** Vue 3 `<script setup>` + TypeScript, Vitest + @vue/test-utils, the dashboard's CSS tokens (`src/styles/main.css`).

**Spec:** `docs/superpowers/specs/2026-11-17-room-availability-design.md`

## Global Constraints

- Page title and menu label: `Room availability`; route path `room-availability`, name `room-availability`; roles `['ADMIN', 'PITIKA']`; menu: Daily group, right after `Food list`.
- The lane runs 07:00 to 18:00; Free at options: `Any time`, `Now`, then 07:00 … 17:30 every 30 min.
- Booked = `CONFIRMED`, `SETUP_IN_PROGRESS`; Waiting = `PENDING_PITIKA`, `PENDING_OWNER`; masked items (`is_masked`) show "Private booking" and are not clickable.
- No summary numbers or cards above the table (owner, twice).
- Simple English in all copy. Food has no numbers anywhere.
- Run vitest from PowerShell in `D:\booking_system_api\admin_dashboard` (Git Bash `d:/` breaks vitest).

## Review Focus

- A room closed at the Free at time (before `start_time` or at/after `end_time`) must not count as free → Task 1 test `closed hours are not free`.
- Back-to-back bookings (10:00–10:45, then 11:00) and a booking ending exactly at the Free at time: free from its end, not before → Task 1 tests `a booking covers [start, end)`.
- Another day than today: no Now line, no past hatching, no Next, Free at defaults to Any time → Task 2 test `another day has no Now line`.
- A masked private booking must not open a drawer or show its booker → Task 3 test `a masked booking shows Private booking and does not open`.
- Rooms of another province never show for a Pitika → Task 2 test `shows only rooms of my province`.

---

### Task 1: Day logic (`src/utils/roomDay.ts`)

**Files:**
- Create: `admin_dashboard/src/utils/roomDay.ts`
- Test: `admin_dashboard/src/utils/__tests__/roomDay.spec.ts`

**Interfaces:**
- Produces:
  - `const DAY_START = 7 * 60`, `const DAY_END = 18 * 60` (minutes)
  - `toMinutes(time: string): number` — `"10:45"` or `"10:45:00"` → 645
  - `clockLabel(minutes: number): string` — 645 → `"10:45"`
  - `lanePct(minutes: number): number` — 0..100, clamped to the lane
  - `type BlockKind = 'booked' | 'waiting' | 'masked'`; `blockKind(item: { status: string; is_masked: boolean }): BlockKind`
  - `freeUntil(room: { start_time: string; end_time: string }, items: Array<{ start_time: string; end_time: string }>, at: number): number | null` — minutes until when the room stays free from `at`, `null` when not free (closed or a block covers `at`)
  - `freeAtOptions(): Array<{ value: string; label: string }>` — `[{value:'', label:'Any time'}, {value:'now', label:'Now'}, {value:'420', label:'07:00'}, … {value:'1050', label:'17:30'}]`

- [ ] **Step 1: Write the failing tests** — `describe('roomDay')` with:
  - `toMinutes('10:45:00') === 645`, `clockLabel(645) === '10:45'`, `lanePct(7*60) === 0`, `lanePct(18*60) === 100`, `lanePct(6*60) === 0`, `lanePct(12*60+30)` ≈ 50.
  - `blockKind`: CONFIRMED/SETUP_IN_PROGRESS → booked; PENDING_PITIKA/PENDING_OWNER → waiting; any with `is_masked: true` → masked.
  - `a booking covers [start, end)`: room 07:30–18:00, items 10:00–10:45 and 11:00–12:30 → `freeUntil(…, 600)` null, `freeUntil(…, 645)` === 660, `freeUntil(…, 630)` null, `freeUntil(…, 780)` === 1080.
  - `closed hours are not free`: room 08:00–17:00 → `freeUntil(room, [], 7*60+30)` null, `freeUntil(room, [], 17*60)` null, `freeUntil(room, [], 16*60)` === 1020.
  - `freeAtOptions()` length 2 + 22, first two as above, last `{value:'1050', label:'17:30'}`.
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/roomDay.spec.ts` — Expected: FAIL (module not found).
- [ ] **Step 3: Implement** the functions in `roomDay.ts` (free = inside opening hours and no item with start ≤ at < end; until = min(next item start after `at`, room end)).
- [ ] **Step 4: Run** the same command — Expected: PASS.
- [ ] **Step 5: Commit** `git add admin_dashboard/src/utils/roomDay.ts admin_dashboard/src/utils/__tests__/roomDay.spec.ts && git commit -m "Room availability: the day logic (free at, blocks, lane)"`

### Task 2: The page, its route and menu entry

**Files:**
- Create: `admin_dashboard/src/views/RoomAvailabilityView.vue`
- Modify: `admin_dashboard/src/router/index.ts` (after the `food-list` route), `admin_dashboard/src/layouts/nav.ts` (after the Food list item: `{ label: 'Room availability', icon: 'calendar-range', route: 'room-availability', roles: ['ADMIN', 'PITIKA'] }`)
- Test: `admin_dashboard/src/views/__tests__/room-availability.spec.ts`

**Interfaces:**
- Consumes: Task 1; `listAllRooms(api)` (`src/api/references.ts`), `getDaySchedule(api, day, roomIds)` (`src/api/staff.ts`), `usePhnomPenhToday`, `useLiveRefresh`, `phnomPenhClock`, `addDays`, `formatDay`, `useSessionStore` (`user.province?.code`, `isAdmin`).
- Produces: rows with `data-room="<id>"` and `data-free="true|false"`; blocks as `button.block` with `data-booking="<id>"` and classes `booked|waiting|masked`; `.now-line` in each lane today; `.result` line; `select#free-at`; `input#room-q`; `select#room-kind`; `select#room-building`.

- [ ] **Step 1: Write the failing tests** (fetch stubbed like `food-list.spec.ts`; rooms 12 Mekong Room PHNOM_PENH 07:30–18:00, 13 Board Room PHNOM_PENH private, 99 Siem Reap room; schedule for 12: CONFIRMED 09:00–10:30 "Budget review", for 13: PENDING_PITIKA 14:00–16:00 "Risk review"; clock 2026-11-04T03:20:00Z = 10:20 Phnom Penh; user = Pitika in PHNOM_PENH):
  - `shows only rooms of my province`: rows `[12, 13]`; the schedule call is `?date=2026-11-04&room_ids=12%2C13`.
  - `draws each booking on the lane`: block `[data-booking]` texts contain "Budget review" and "09:00–10:30"; 12's block has class `booked`, 13's `waiting`.
  - `Free at Now puts the free rooms first and says how many`: default `#free-at` value `now`; rows order `[13, 12]` (12 busy at 10:20); `.result` text `1 of 2 rooms free at 10:20, now`; 13 shows `Free until 14:00`; row 12 has class `not-free`.
  - `Free at 14:00`: select `840` → order `[12, 13]`, 12 shows `Free for the rest of the day`, result `1 of 2 rooms free at 14:00`.
  - `filters by search, kind and building, and Clear filters resets them`.
  - `another day has no Now line`: `/room-availability?date=2026-11-05` → no `.now-line`, `#free-at` value `''`.
  - `is in the Daily group of the sidebar after Food list, for Admin and Pitika` (via `NAV_GROUPS`).
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/room-availability.spec.ts` — Expected: FAIL.
- [ ] **Step 3: Implement** the page per the spec ("The page", "Free at", "Data and refresh"): head + day buttons + date picker as `FoodListView.vue` (day in `?date=`), filters row, result line, sheet with header hours 07:00–17:00, rows (thumbnail = `cover_photo.thumbnail_url` through `RoomPhoto`, name + Khmer, floor · building · seats, Free until line), lanes (past hatch + now line + Now tag only today; green line at a Free at time other than Now), legend. Rooms: active only; Pitika → `province.code === user.province.code`; Admin (`session.isAdmin`) → all. Sort by building then name; with Free at, free first by `freeUntil` descending. Clock ref refreshed every 20 s. Add the route and the nav item.
- [ ] **Step 4: Run** the spec and `npm run type-check` — Expected: PASS, no type errors.
- [ ] **Step 5: Commit** `git commit -m "Room availability: the page — every room's day, Free at, filters, Now line"`

### Task 3: Hover details and the booking drawer

**Files:**
- Modify: `admin_dashboard/src/views/RoomAvailabilityView.vue`
- Test: `admin_dashboard/src/views/__tests__/room-availability.spec.ts`

**Interfaces:**
- Consumes: `usePanelParam('booking')`, `usePanelRecord`, `getBooking`, `ReviewPanel` (props as in `ReviewView.vue`), `BookingActionDialog` (props as in `ReviewView.vue`), `BookingPanel`, `REVIEWERS.pitika.approve/reject` (`src/views/review/reviewers.ts`), `useToast`.
- Produces: `.tip` tooltip (`role="tooltip"`), drawer via `?booking=ID`.

- [ ] **Step 1: Write the failing tests:**
  - `hover shows the title, times and booker`: `mouseenter` on 13's block → `.tip` text `Risk review`, `14:00–16:00`, the booker name, `Waiting for Pitika`; `mouseleave` removes it; focus shows it too.
  - `a waiting booking opens the To review panel and can be approved`: click 13's block → address `booking=` the id; `ReviewPanel` dialog with Approve; Approve → `BookingActionDialog`; confirm → POST `/api/v1/pitika/bookings/<id>/approve` with `{ notes: null, version }`; toast; drawer closed; schedule reloaded.
  - `reject needs a reason`: the reason under 5 characters keeps the dialog open with the field error; a valid one POSTs `/reject`.
  - `a booked booking opens the Bookings drawer`: click 12's block → `BookingPanel` (title `Budget review`), no Approve.
  - `a masked booking shows Private booking and does not open`: an item `is_masked: true, booking_id: null` → block text `Private booking`, `disabled`, no booker in its tooltip.
- [ ] **Step 2: Run** the spec — Expected: the new tests FAIL.
- [ ] **Step 3: Implement**: tooltip on `mouseenter`/`focus` of a block (fixed position above the block, below when no room); click → `panel.open(booking_id)`; the record loads with `getBooking`; show `ReviewPanel` when `record.status === 'PENDING_PITIKA'` and the user has PITIKA (Approve/Reject → `BookingActionDialog`, `decide()` as in `ReviewView.vue`, reject `minLength` 5, toast `"<code> approved|rejected"`, close, reload), else `BookingPanel` with `:admin-actions="session.isAdmin"`; `@changed` reloads the day.
- [ ] **Step 4: Run** the whole suite `npx vitest run`, `npm run type-check`, `npx eslint src/views/RoomAvailabilityView.vue src/utils/roomDay.ts` — Expected: all pass.
- [ ] **Step 5: Check in the real app** as `demo.pitika@example.com`: open Room availability, hover a block, open a booking. Screenshot.
- [ ] **Step 6: Commit** `git commit -m "Room availability: hover details and the booking drawer with Approve / Reject"`
