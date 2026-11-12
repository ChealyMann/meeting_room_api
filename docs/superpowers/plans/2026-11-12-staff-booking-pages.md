# Staff Booking Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Staff find, book (one or many sessions, with food and IT) and follow their bookings inside the dashboard, against the real API, looking like the approved "Calm" demo.

**Architecture:** Two small API additions (a `group` + `icon` on food packages and IT services; one endpoint for every room's busy times on one day), then new Staff pages in `admin_dashboard/` under the existing shell and sidebar. Pure date/time and search rules live in one tested TypeScript module; the pages are thin Vue views over it and over a `src/api/staff.ts` client module.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic (MySQL), pytest · Vue 3 + TS + Vite, Pinia, vue-router, lucide-vue-next, Vitest + @vue/test-utils, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-12-staff-booking-pages-design.md`. Visual and behaviour reference: the demo in `.superpowers/staff-new-site/` (serve the folder, open `index.html`; it is Design 1 "Calm" + Soft fields). Read both before starting.

## Global Constraints

- Work on branch `feature/staff-booking-pages` from `main`. Commits and PRs **without** any Claude attribution line (owner rule). The owner merges.
- API: pip + `requirements*.txt` (no uv). Python 3.12. `ruff format` + `ruff check` clean.
- Models: one class per file. Schemas, routers, services: one file per resource.
- Dashboard: views import the client as `import { api } from '../api'` (or `../../api`); API types come from `src/api/types.ts` (aliases of `src/api/schema.d.ts`). After API changes run `npm run gen:api` with the API on :8000.
- Never name a component CSS class `grid`, `table`, `flex`, `hidden`, `ring`, `border`, `shadow` (Tailwind is global); `main.css` already owns `.switch`, `.sheet`, `.mono`.
- Calm look on Staff pages only (spec "Calls"): dashboard colour tokens, fonts, night theme and focus ring; soft surfaces; crimson only for the main button and picked things; red borders only for real errors.
- Motion: press `scale(0.97)` 160 ms strong ease-out (`cubic-bezier(0.23, 1, 0.32, 1)`), named transitions only, ≤ 300 ms, hover only under `(hover: hover) and (pointer: fine)`, instant with `prefers-reduced-motion`.
- Copy is short, plain English as in the demo (e.g. "Free until 14:00", "Pick a start time", "Send request").
- Don't run pytest and Playwright at the same time.

## Review Focus

1. **A booking that crosses into a busy time after the page loaded** (someone else books first): Send must show the API's conflict next to Schedule and not lose the form. → test in Task 11.
2. **A private room's busy time the staff member may not see** (masked item): cards and the week table treat it as busy and never show its title. → tests in Tasks 2 and 8.
3. **Today after the room closes / a room with unusual hours (07:30–12:00)**: no start times offered past closing; the table rows follow the room's hours. → tests in Task 5.
4. **People above the room's seats typed by hand** (not with + ): Next is blocked with "This room has 14 seats." → test in Task 9.
5. **A Staff user who also has another role** (Pitika + Staff): sees both sets of sidebar items; home stays the role page, not Find a room. → test in Task 4.

---

### Task 1: API — `group` and `icon` on food packages and IT services

**Files:**
- Create: `app/constants/service_groups.py`, `alembic/versions/a9c4e2b7d1f3_service_group_icon.py` (down_revision `f1c3a7b9d2e4`)
- Modify: `app/models/catering_package.py`, `app/models/it_service.py`, `app/schemas/catering_package.py`, `app/schemas/it_service.py`, `app/services/catering_package.py`, `app/services/it_service.py` (only if they copy fields one by one)
- Test: `tests/test_catering_packages.py`, `tests/test_it_services.py`, `tests/test_migrations.py` (if it lists heads)

**Interfaces:**
- Produces: `class FoodGroup(StrEnum): BREAKFAST, MEALS, BREAKS` and `class ITGroup(StrEnum): SCREENS, SOUND, DEVICES, SUPPORT` in `app/constants/service_groups.py`. Both models get `group: Mapped[str | None] = mapped_column(String(20))` and `icon: Mapped[str | None] = mapped_column(String(1000))`. `CateringPackageCreate/Update/Out` get `group: FoodGroup | None` and `icon: str | None` (OptionalText(1000), same as Equipment); `ITService*` get `group: ITGroup | None` and `icon`.

- [ ] **Step 1: Write the failing tests** (in each of the two test files)
  - `test_create_with_group_and_icon`: POST `{"name": "Coffee break", "group": "BREAKFAST", "icon": "coffee"}` → 201, body has `group == "BREAKFAST"`, `icon == "coffee"`; add `"group"`, `"icon"` to `OUT_FIELDS`.
  - `test_group_defaults_to_none`: POST without group → `group is None`, `icon is None`.
  - `test_wrong_group_is_refused`: catering POST `{"group": "SCREENS"}` → 422 `VALIDATION_ERROR`, `"group" in fields(...)`; IT POST `{"group": "MEALS"}` → same.
  - `test_patch_group`: PATCH `{"version": 1, "group": "MEALS"}` → 200, `group == "MEALS"`; PATCH `{"version": 2, "group": None}` → `group is None`.
  - `test_staff_list_shows_group`: as a Staff user, GET list → each item has `group` and `icon`.
- [ ] **Step 2: Run** `pytest tests/test_catering_packages.py tests/test_it_services.py -q` → FAIL (unknown fields / missing keys).
- [ ] **Step 3: Add the constants, columns, migration (two nullable columns per table, downgrade drops them) and schema fields.**
- [ ] **Step 4: Run** `alembic upgrade head` on the dev DB, then the two test files and `pytest tests/test_migrations.py -q` → PASS.
- [ ] **Step 5: Commit** `API: food packages and IT services get a group and an icon (Admin sets them; none = Other)`.

### Task 2: API — every room's busy times for one day

**Files:**
- Create: `app/routers/room_day_schedule.py`
- Modify: `app/schemas/room_schedule.py`, `app/services/room_schedule.py`, `app/main.py` (include the router)
- Test: `tests/test_room_day_schedule.py`

**Interfaces:**
- Produces: `GET /api/v1/room-schedule?date=YYYY-MM-DD&room_ids=1,2,3` (`date` defaults to today in Phnom Penh; `room_ids` optional comma list, at most 200; without it, every room `is_active`). Response `ItemList[RoomDaySchedule]` where `class RoomDaySchedule(ResponseModel): room_id: int; items: list[ScheduleItem]`, ordered by room id; rooms with no sessions still appear with `items: []`. Any signed-in user (`AnyUser`). Service: `get_day_schedule(session, current, day: date | None, room_ids: list[int] | None) -> list[RoomDaySchedule]`, reusing `_item` so masking is identical to `get_schedule`.

- [ ] **Step 1: Write the failing tests** in `tests/test_room_day_schedule.py` (use the existing booking factories/helpers from `tests/booking_helpers.py`, `tests/factories.py`):
  - `test_one_request_gives_every_room`: two rooms, a booking in room A 09:00–10:00 on day D → `GET ?date=D` lists both rooms; room A has one item `09:00–10:00`, room B `items == []`.
  - `test_room_ids_filter`: `?date=D&room_ids=<B>` → only room B.
  - `test_private_booking_is_masked_like_the_room_schedule`: a private-room booking by another user → item has `is_masked is True`, `booking_id is None`, `title` equals the masked title; the same booking through `GET /rooms/{id}/schedule` gives an equal item.
  - `test_cancelled_booking_does_not_block`: cancelled booking → not listed.
  - `test_too_many_ids`: 201 ids → 422 `VALIDATION_ERROR`, `"room_ids" in fields`.
  - `test_needs_sign_in`: no token → 401.
- [ ] **Step 2: Run** `pytest tests/test_room_day_schedule.py -q` → FAIL (404).
- [ ] **Step 3: Implement the schema, the service function (one query over `BookingSession` joined to `Booking` with `is_blocking` true, `date == day`, optional `room_id IN`, grouped in Python) and the router.**
- [ ] **Step 4: Run** the new tests plus `pytest tests/test_room_schedule.py -q` → PASS.
- [ ] **Step 5: Commit** `API: one request gives every room's busy times for a day (same masking as the room schedule)`.

### Task 3: Dashboard — Staff API module and regenerated types

**Files:**
- Create: `admin_dashboard/src/api/staff.ts`
- Modify: `admin_dashboard/src/api/schema.d.ts` (regenerated), `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/api/services.ts` (types now carry `group`/`icon`)
- Test: `admin_dashboard/src/api/__tests__/staff.spec.ts`

**Interfaces:**
- Consumes: Tasks 1–2 endpoints.
- Produces (all `(client: ApiClient, …) => Promise<…>` like the other modules):
  - `listBookableRooms(client, f: { q?: string; is_private?: boolean; page?: number; size?: number }): Promise<Page<RoomListItem>>` → `GET /api/v1/rooms?is_bookable=true&…`
  - `getDaySchedule(client, day: string, roomIds?: number[]): Promise<ItemList<RoomDaySchedule>>` → `GET /api/v1/room-schedule?date=…&room_ids=…`
  - `listRoomPhotos(client, roomId: number): Promise<ItemList<PhotoOut>>` → `GET /api/v1/rooms/{id}/photos`
  - `listActiveServices(client, kind: ServiceKind): Promise<ServiceOut[]>` → one page of 100, active only
  - `listHolidays(client, from: string, to: string): Promise<PublicHolidayOut[]>`
  - `checkBooking(client, body: BookingCheck): Promise<BookingCheckResult>` → `POST /api/v1/bookings/check`
  - `sendBooking(client, body: BookingCreate): Promise<BookingSaved>` → `POST /api/v1/bookings`
  - `listMyBookings(client, f: { page?: number; size?: number }): Promise<Page<BookingListItem>>` → `GET /api/v1/bookings/mine`
  - `getMyBooking(client, id: number): Promise<BookingDetail>`, `getDoorPass(client, id: number): Promise<DoorPassOut>`, `cancelMyBooking(client, id: number, version: number, reason?: string): Promise<BookingDetail>`
  - `bookingCalendarUrl(id: number): string` (the ICS route the API exposes at `bookings.py:127`; read its path there)
  - New aliases in `types.ts`: `RoomDaySchedule`, `BookingCheck`, `BookingCheckResult`, `BookingCreate`, `BookingSaved`, `PhotoOut`, `PublicHolidayOut` (if missing).

- [ ] **Step 1:** Start the API (`run.bat`), run `npm run gen:api`, add the aliases. `npm run type-check` → PASS.
- [ ] **Step 2: Write the failing tests** in `staff.spec.ts` with a stubbed `fetch` (same pattern as `src/api/__tests__/*.spec.ts`): each function calls the right method + path + query (e.g. `getDaySchedule(c, '2026-11-13', [3, 5])` → `GET /api/v1/room-schedule?date=2026-11-13&room_ids=3%2C5`), `sendBooking` posts the body unchanged, `cancelMyBooking(c, 9, 4)` posts `{ "version": 4 }` and with a reason `{ "version": 4, "reason": "Plans changed" }`.
- [ ] **Step 3: Run** `npx vitest run src/api/__tests__/staff.spec.ts` → FAIL; implement `staff.ts`; run → PASS.
- [ ] **Step 4: Commit** `Dashboard: Staff API module (rooms, day schedule, check, send, my bookings, door pass, cancel)`.

### Task 4: Dashboard — routes, sidebar items and home for Staff

**Files:**
- Modify: `admin_dashboard/src/router/index.ts`, `admin_dashboard/src/router/guard.ts`, `admin_dashboard/src/layouts/nav.ts`
- Create (placeholders, filled by later tasks): `admin_dashboard/src/views/staff/FindRoomView.vue`, `RoomView.vue`, `BookView.vue`, `MyBookingsView.vue`
- Test: `admin_dashboard/src/router/__tests__/guard.spec.ts`, `admin_dashboard/src/layouts/__tests__/nav.spec.ts`

**Interfaces:**
- Produces route names and paths (all under the shell, `meta.roles: ['STAFF']`): `find-room` → `/find-room`, `staff-room` → `/find-room/:roomId`, `book` → `/book/:roomId` (query `date`, `start`, `end` carry a time picked on the room page; `step` 1–4), `my-bookings` → `/my-bookings` (query `booking` opens the details).
- `homeFor`: keep every existing role first; add `if (roles.includes('STAFF')) return 'find-room'` just before `return 'no-access'`.
- `NAV_GROUPS` "Daily": first two items `{ label: 'Find a room', icon: 'search', route: 'find-room', roles: ['STAFF'] }`, `{ label: 'My bookings', icon: 'calendar-days', route: 'my-bookings', roles: ['STAFF'] }` (register the two icons in the rail's icon map if needed).

- [ ] **Step 1: Write the failing tests:**
  - guard: `homeFor(['STAFF'])` is `'find-room'` (replace the old `'no-access'` expectations); `homeFor(['PITIKA', 'STAFF'])` stays `'review'`; a Staff user going to `bookings` (Admin/Pitika page) is sent to `find-room`; a Staff user may open `book`.
  - nav: `navFor(['STAFF'])` is `[{ title: 'Daily', items: ['find-room', 'my-bookings'] }]`; `shape(['PITIKA', 'STAFF'])` is `['find-room', 'my-bookings', 'review', 'bookings', 'food-list']` (Review Focus 5).
- [ ] **Step 2: Run** `npx vitest run src/router src/layouts` → FAIL.
- [ ] **Step 3: Add routes, guard line, nav items and placeholder views (a title each).**
- [ ] **Step 4: Run** the same → PASS; `npm run type-check` → PASS.
- [ ] **Step 5: Commit** `Dashboard: Staff sidebar items, routes and home (Find a room)`.

### Task 5: Dashboard — booking rules module (pure, no Vue)

**Files:**
- Create: `admin_dashboard/src/views/staff/rules.ts`
- Test: `admin_dashboard/src/views/staff/__tests__/rules.spec.ts`

**Interfaces (all pure; times are minutes after midnight, days are `YYYY-MM-DD` Phnom Penh):**
- `workdaysFrom(day: string, count: number): string[]` — skips Sat/Sun.
- `roomHours(room: { start_time: string; end_time: string }): { open: number; close: number }`
- `busySpans(items: ScheduleItem[], day: string): { a: number; b: number; masked: boolean }[]`
- `fits(busy: {a,b}[], hours: {open,close}, day: string, today: string, now: number, a: number, len: number): boolean`
- `freeStarts(busy, hours, day, today, now, len: number, step = 30): number[]`
- `nowLine(busy, hours, day, today, now): { tone: 'ok' | 'alert' | 'off'; text: string }` — texts exactly: `Free until HH:MM`, `Free all day`, `In use until HH:MM`, `Opens at HH:MM`, `Closed now`.
- `mergeSessions(list: { date: string; a: number; b: number }[]): same[]` — sorted, touching/overlapping on one day joined.
- `toMeetingType(external: boolean, governor: boolean): MeetingType` and `fromMeetingType(t: MeetingType): { external: boolean; governor: boolean }`.
- `foodGroupFirst(start: number): 'BREAKFAST' | 'MEALS' | 'BREAKS'` — `< 630` BREAKFAST, `< 810` MEALS, else BREAKS.
- `matchesWords(text: string, query: string): boolean` — every typed word must match the start of a word.
- `groupServices<T extends { group: string | null; name: string; description: string | null }>(items: T[], order: string[], query: string): { group: string; items: T[] }[]` — `order` first, `null`/unknown as `'OTHER'` last, empty groups dropped.
- `lenText(min: number): string` → `1 h`, `1 h 30 min`, `30 min`.

- [ ] **Step 1: Write the failing tests** (exact values):
  - `workdaysFrom('2026-11-13', 3)` → `['2026-11-13', '2026-11-16', '2026-11-17']`.
  - Room 07:30–12:00, today, now 11:10, len 60 → `freeStarts` is `[]` (Review Focus 3); same room tomorrow → first start 450 (07:30), last 660 (11:00).
  - A masked item 09:00–10:00 → `fits(..., 540, 60)` false and `busySpans` keeps `masked: true` (Review Focus 2).
  - `nowLine`: busy 14:00–15:00, now 10:00 → `{ tone: 'ok', text: 'Free until 14:00' }`; now 14:30 → `In use until 15:00`; after close → `Closed now`.
  - `mergeSessions([{d,540,600},{d,600,660}])` → one `{d,540,660}`.
  - `toMeetingType(true, true)` → `'EXTERNAL_WITH_GOVERNOR'`; `fromMeetingType('INTERNAL')` → `{ external: false, governor: false }`.
  - `matchesWords('Breakfast & Dim Sum Steamed dumplings', 'tea')` → false; `('Tea & Fresh Fruit', 'tea')` → true; `('Afternoon High Tea', 'high te')` → true.
  - `groupServices` with one `group: null` item → last group is `'OTHER'`; with query `'zzz'` → `[]`.
  - `lenText(90)` → `'1 h 30 min'`.
- [ ] **Step 2: Run** `npx vitest run src/views/staff/__tests__/rules.spec.ts` → FAIL; implement; → PASS.
- [ ] **Step 3: Commit** `Dashboard: Staff booking rules (hours, free times, sessions, meeting type, search, groups)`.

### Task 6: Dashboard — Find a room

**Files:**
- Modify: `admin_dashboard/src/views/staff/FindRoomView.vue`
- Create: `admin_dashboard/src/views/staff/RoomCard.vue`, `admin_dashboard/src/views/staff/staff.css` (shared Calm styles for all Staff pages)
- Test: `admin_dashboard/src/views/staff/__tests__/find-room.spec.ts`

**Interfaces:**
- Consumes: `listBookableRooms` (size 100), `getDaySchedule(today, ids)`, `nowLine`, `roomHours`, `busySpans`; cover photo via the existing `RoomPhoto.vue`/`usePrivateImage`.
- Produces: `RoomCard` props `{ room: RoomListItem; now: { tone; text } }`, emits `details`, `book`.

Behaviour from the spec "Find a room" (title + date + count; search, building, Shared/Private, Free now; 4:3 photo cards; Private tag; **Details** and **Book**/**Request**; empty state "No room matches" + Clear filters).

- [ ] **Step 1: Write the failing tests** (stubbed fetch, memory router):
  - shows one card per room from `/api/v1/rooms`, makes **one** call to `/api/v1/room-schedule` with all ids;
  - a room busy now shows `In use until 15:00`; "Free now" hides it;
  - the private room's button reads `Request`, a shared one `Book`; clicking `Book` routes to `book` with `roomId` and no `date`; `Details` routes to `staff-room`;
  - search `projector` keeps only rooms whose name or equipment matches.
- [ ] **Step 2: Run** → FAIL; build the view and card to the demo's look; → PASS.
- [ ] **Step 3: Commit** `Dashboard: Find a room (photo cards, free now, Details and Book/Request)`.

### Task 7: Dashboard — Room details with "Book a time"

**Files:**
- Modify: `admin_dashboard/src/views/staff/RoomView.vue`
- Create: `admin_dashboard/src/views/staff/PhotoGallery.vue`, `admin_dashboard/src/views/staff/TimePick.vue`
- Test: `admin_dashboard/src/views/staff/__tests__/room.spec.ts`

**Interfaces:**
- Consumes: `getRoom`, `listRoomPhotos`, `getRoomSchedule(room, from, to)` (7 working days), `listHolidays`, `freeStarts`, `workdaysFrom`, `nowLine`.
- Produces: `TimePick` props `{ room: RoomDetail; busy: ScheduleItem[]; holidays: PublicHolidayOut[] }`, emits `pick: { date: string; a: number; b: number }`; `PhotoGallery` props `{ photos: PhotoOut[]; name: string }` (fade, dots, arrows, arrow keys).

- [ ] **Step 1: Write the failing tests:** only free start times show for the chosen length (a busy 10:00–11:00 hides 09:30 for 1 h); the button reads `Continue · 09:00–10:00, Fri 13 Nov` and routes to `book` with `date=2026-11-13&start=09:00&end=10:00`; a holiday day in the strip carries an amber `Holiday` mark and stays clickable; "Several days? Pick on the calendar" routes to `book` without a time.
- [ ] **Step 2: Run** → FAIL; implement; → PASS.
- [ ] **Step 3: Commit** `Dashboard: room details with photos and Book a time`.

### Task 8: Dashboard — booking flow shell, side card and week table (step 1)

**Files:**
- Modify: `admin_dashboard/src/views/staff/BookView.vue`
- Create: `admin_dashboard/src/views/staff/book/useBookingDraft.ts`, `book/WeekTable.vue`, `book/SideCard.vue`, `book/StepBar.vue`
- Test: `admin_dashboard/src/views/staff/__tests__/book-schedule.spec.ts`

**Interfaces:**
- Produces: `useBookingDraft(roomId: number)` returning a reactive draft `{ step: 1|2|3|4; sessions: {date,a,b}[]; title: string; external: boolean; governor: boolean; people: number; emails: string[]; justification: string; notes: string; foods: number[]; foodNote: string; its: number[]; itNote: string }` plus `addSession`, `removeSession`, `toCheckBody(): BookingCheck`, `toCreateBody(): BookingCreate` (servings are not sent; meeting type via `toMeetingType`). `WeekTable` props `{ room; days: string[]; busy: ScheduleItem[]; holidays; sessions }`, emits `add: {date,a,b}`, `remove: {date,a,b}`. `SideCard` slot-free; props `{ room; draft; step; checkSteps?: BookingStep[]; warnings? }`.

Behaviour: spec "Book — step 1" and "Side card" (5 working days from today, room hours, click = 1 h, drag = any length, merge, remove; busy with "Busy", masked busy the same; holiday day head amber "Holiday" + name on hover, cells bookable; sticky "Your sessions" and "Total"; full-height card; no page scroll on a computer). Query `date/start/end` pre-adds one session.

- [ ] **Step 1: Write the failing tests:** arriving with `?date=…&start=09:00&end=10:00` shows one session; clicking a free cell adds `1 h`; a mouse drag over six free half-hours adds `3 h`; a picked block next to another joins (`08:00–12:00 · 4 h`); clicking a picked block removes it, but not in the same click that added it; a masked busy cell is disabled and shows `Busy` with no title (Review Focus 2); a holiday column shows `Holiday` and its cells are enabled; `Next: Meeting details` with no session shows `Pick at least one time in the table.`
- [ ] **Step 2: Run** → FAIL; implement; → PASS.
- [ ] **Step 3: Commit** `Dashboard: booking step 1, the week table and the side card`.

### Task 9: Dashboard — step 2 Meeting details (soft fields)

**Files:**
- Create: `admin_dashboard/src/views/staff/book/MeetingStep.vue`
- Test: `admin_dashboard/src/views/staff/__tests__/book-meeting.spec.ts`

Behaviour: spec "step 2" with **Meeting type** = segmented `Internal` / `External` + switch `The Governor attends` (default Internal, off) placed under the title; soft fields with floating labels; title `0/80`; people quick buttons `[2, 4, 6, 8, 10, 15, 20]` up to the seats + − / +, "Up to 24"; emails as chips (Enter or comma), bad email message `Write a full email address.`; private reason only on private rooms with `Only Pitika and the room owner read this.`; notes; "Booked by" row; − / + do not select text (`user-select: none`).

- [ ] **Step 1: Write the failing tests:** empty title → `Write a title for the meeting.` and Next stays on step 2; typing `30` people in a 14-seat room → `This room has 14 seats.` and Next blocked (Review Focus 4); quick `10` sets people to 10; External + Governor makes `toCreateBody().meeting_type === 'EXTERNAL_WITH_GOVERNOR'`; private room without a reason → `Tell the room owner why you need this room.`
- [ ] **Step 2: Run** → FAIL; implement; → PASS.
- [ ] **Step 3: Commit** `Dashboard: booking step 2, meeting details in soft fields with meeting type`.

### Task 10: Dashboard — step 3 Food & IT

**Files:**
- Create: `admin_dashboard/src/views/staff/book/ServicesStep.vue`, `admin_dashboard/src/views/staff/book/ServiceList.vue`
- Test: `admin_dashboard/src/views/staff/__tests__/book-services.spec.ts`

**Interfaces:**
- Consumes: `listActiveServices('catering' | 'it')`, `groupServices`, `foodGroupFirst`, `matchesWords`.
- Produces: `ServiceList` props `{ title: string; items: ServiceOut[]; groupOrder: string[]; groupLabels: Record<string, string>; picked: number[]; searchLabel: string }`, emits `toggle: number`.

Group labels: food `BREAKFAST` Breakfast, `MEALS` Meals, `BREAKS` Breaks & drinks; IT `SCREENS` Screens & video, `SOUND` Sound & language, `DEVICES` Devices & network, `SUPPORT` Support; `OTHER` Other. Flat headers (title + `None` / `2 picked`), no sub-line, no "Good for" label; icons from each item's `icon` (lucide name; fallback `utensils` / `headset`); kitchen and IT notes under each list when something is picked; food shows `× {people} · served at HH:MM`; quiet thin scrollbars.

- [ ] **Step 1: Write the failing tests:** a session at 08:00 puts Breakfast first; an item with `group: null` shows under `Other` last; search `tea` hides an item described as "steamed"; `zzz` shows `No food matches “zzz”.` and Clear search brings all back; picking while searching updates `1 picked`.
- [ ] **Step 2: Run** → FAIL; implement; → PASS.
- [ ] **Step 3: Commit** `Dashboard: booking step 3, food and IT grouped with search`.

### Task 11: Dashboard — step 4 Review, check and send

**Files:**
- Create: `admin_dashboard/src/views/staff/book/ReviewStep.vue`
- Modify: `admin_dashboard/src/views/staff/BookView.vue`, `book/SideCard.vue`
- Test: `admin_dashboard/src/views/staff/__tests__/book-review.spec.ts`

Behaviour: spec "step 4" (room row, date tile + big time or "N sessions" chips, four click-to-change tiles with a pencil, Booked by). On entering step 4 call `checkBooking(draft.toCheckBody())`: `steps` feed the side card's path after `You send it · Now`; `warnings` with `code: 'PUBLIC_HOLIDAY'` show as amber notes above the tiles (`Fri 13 Nov is <name>`); a `problem` shows on the step it names and Send is off. Send → `sendBooking`; success → `my-bookings` with a toast `Request sent. Pitika checks it next.` (private: `Request sent. Pitika and the room owner check it next.`); an API error with `fields` goes back to the step that owns the field with the message next to it, the draft kept.

- [ ] **Step 1: Write the failing tests:** check answer steps render in order; a `PUBLIC_HOLIDAY` warning renders and Send stays on; a check `problem` with code for a busy slot disables Send and shows the message; a 409 on send whose fields name `sessions` returns to step 1 with the message and every session still listed (Review Focus 1); success routes to `my-bookings` and shows the toast.
- [ ] **Step 2: Run** → FAIL; implement; → PASS.
- [ ] **Step 3: Commit** `Dashboard: booking step 4, review tiles, API check and send`.

### Task 12: Dashboard — My bookings, details, door pass, cancel, calendar

**Files:**
- Modify: `admin_dashboard/src/views/staff/MyBookingsView.vue`
- Create: `admin_dashboard/src/views/staff/BookingDetailDialog.vue`
- Test: `admin_dashboard/src/views/staff/__tests__/my-bookings.spec.ts`

Behaviour: spec "My bookings" (Coming up / Past & cancelled with counts from `display_status` and the first session; date block, photo, title, time + "n more", room, status pill, `Door pass` when confirmed; details window with status, progress track, times, people, food, IT, notes; `Cancel booking` through the existing confirm dialog (`useConfirm`), optional reason ≥ 5 characters, sends `version`; Door pass dialog with Copy; `Add to calendar` link to `bookingCalendarUrl`). Query `booking=<id>` opens the details (used after Send).

- [ ] **Step 1: Write the failing tests:** confirmed bookings show `Door pass`; Past tab lists cancelled and completed; cancel posts the current `version` and the card moves to Past; a 409 stale version shows `This item changed. Reload it.`; `?booking=7` opens booking 7.
- [ ] **Step 2: Run** → FAIL; implement; → PASS.
- [ ] **Step 3: Commit** `Dashboard: My bookings with details, door pass, cancel and calendar`.

### Task 13: Dashboard — Admin sets group and icon in the Service catalog

**Files:**
- Modify: `admin_dashboard/src/views/catalog/ServiceFormPanel.vue`, `admin_dashboard/src/views/ServiceCatalogView.vue`
- Test: `admin_dashboard/src/views/__tests__/` (the existing service catalog spec)

Behaviour: the form gets a **Group** search picker (the kind's groups + "No group") and an **Icon** field using `IconPicker.vue` (same as Equipment); the list shows the group in a column. Saving sends `group` and `icon`.

- [ ] **Step 1: Write the failing tests:** a catering form offers Breakfast / Meals / Breaks & drinks / No group and an IT form its four groups; saving sends `{ group: 'MEALS', icon: 'utensils' }`; the list shows `Meals`.
- [ ] **Step 2: Run** → FAIL; implement; → PASS.
- [ ] **Step 3: Commit** `Dashboard: Admin picks a group and an icon for food packages and IT services`.

### Task 14: Docs, end-to-end test and full check

**Files:**
- Modify: `DESIGN.md` (new "Staff pages" section: Calm look on Staff pages only, the pages and the owner decisions of 12 Nov 2026)
- Create: `admin_dashboard/e2e/staff.spec.ts` (needs `E2E_STAFF_EMAIL` / `E2E_STAFF_PASSWORD`, skipped without them, like `bookings.spec.ts`)

- [ ] **Step 1: Write `staff.spec.ts`:** sign in as Staff → lands on Find a room → Book on a shared room → pick a free cell tomorrow → title `E2E staff <timestamp>` → pick one food item → Review → Send → My bookings lists the title as `Waiting for Pitika` → open it → Cancel booking → it moves to Past.
- [ ] **Step 2: Run** `npx vitest run` → all PASS; `npm run type-check` and `npm run lint` → clean; `pytest -q` (alone) → all PASS; then `npx playwright test e2e/staff.spec.ts` (alone, API running) → PASS.
- [ ] **Step 3:** Look at real screenshots of every Staff page in light, night and phone size and compare with the demo; fix what differs.
- [ ] **Step 4: Commit** `Docs: Staff pages in DESIGN.md; e2e: book and cancel as Staff`, push the branch, open the PR through the GitHub API with a plain description (no attribution line). Do not merge.
