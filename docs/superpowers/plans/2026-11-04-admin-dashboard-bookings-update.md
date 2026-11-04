# Admin Dashboard: Booking API Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Admin dashboard up to the new room booking API. Step A adds the new catalog pages and the new rules on the current pages, with no API change. Step B adds one Admin endpoint, `GET /bookings`, and a read-only Bookings page.

**Architecture:** Every page reuses the parts the Phase 2–6 pages already use: `useResourceList`, `usePanelParam`, `usePanelRecord`, `ListSearch`, `StatusFilter`, `PagingFoot`, `StateMarks`, `ActiveToggle`, `SidePanel`, `useFieldErrors`, drafts, `serial`, `listPage.css`. Catering packages and IT services have the same shape, so they share one view and one form panel, set up by a `kind` route prop. Step B adds one API function next to the Pitika and owner lists (`_list_in_rooms`), then the dashboard pages on top of it.

**Tech Stack:** API: FastAPI, SQLAlchemy, pytest. Dashboard: Vue 3 `<script setup lang="ts">`, TypeScript, Vue Router, Pinia, Tailwind v4 tokens, `lucide-vue-next`, Vitest + `@vue/test-utils`, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-03-room-booking-api-design.md` (the API, sections 9.2, 9.6, 9.9, 9.10, 9.12, 9.15, 12) and `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (DSH-G01 to G10, the look). Scope chosen by the owner on 4 Nov 2026: "option 2, in two steps", where the Admin can see bookings but cannot act on them.

## Global Constraints

- Branch `feature/dashboard-bookings`, made from `feature/room-booking-api`. Commit messages carry **no** AI attribution lines (owner rule).
- API: one schema, service and router file per resource. Rules live in services and routers stay thin. No new Python or npm packages. Tests first. `pytest` and `ruff check .` stay green.
- Dashboard types come only from `src/api/schema.d.ts`. Run `npm run gen:api` (API running) after Task 6, and add every new alias to `src/api/types.ts`.
- All Phase 2–6 rules apply: G01 paging (20 / 50 / 100), G02 filters in the address, G03 side panel with PATCH of changed fields only, G04/G05 API messages under the field and at the top, G06 client checks use the API limits, G07 confirm before making something inactive, G09 toast and list refresh, G10 empty states and skeleton rows.
- API limits (G06): catering package / IT service `name` 2–200 characters after trimming, `description` ≤ 1000, `sort_order` 0–9999. HTML is refused by the API ("HTML is not allowed."), so show that message under the field. Do not add a client check for it.
- Catalog PATCH must send the `version` that was read. An old version → 409 `STALE_VERSION`.
- Booking times: `date` + `start_time`/`end_time` are already Phnom Penh local time, so show them as they are. Fields ending in `_at` are UTC with `Z`, so show them with `formatPhnomPenh`.
- Door pass: never in a list. It shows only after the Admin clicks "Show door pass" (same rule as the room door code, DSH-R05).
- The Admin cannot approve, reject, cancel or edit a booking. The API refuses it, so the dashboard has no buttons for it.
- Serials: catering package `CP·0003`, IT service `IS·0003`, booking: the `reference_code` (`NBC-26-48213`) in mono, no serial.
- Labels. Display status: `PENDING_PITIKA` "Waiting for Pitika", `PENDING_OWNER` "Waiting for owner", `SETUP_IN_PROGRESS` "IT setup", `CONFIRMED` "Confirmed", `COMPLETED` "Completed", `REJECTED` "Rejected", `CANCELLED` "Cancelled". Meeting type: `INTERNAL` "Internal", `EXTERNAL` "External", `INTERNAL_WITH_GOVERNOR` "Internal, with Governor", `EXTERNAL_WITH_GOVERNOR` "External, with Governor". Route: `R1` "Shared room", `R2` "Private room, owner approves", `R3` "Owner's own room", `R4` "Owner's own room, with services".
- English UI, no emoji, Lucide icons at stroke 1.75, colour tokens only (day and night themes).

## Review Focus

- A user is turned off while they have open bookings → the panel lists the cancelled bookings (`bookings_cancelled`) next to the rooms that lost their owner. Neither list hides the other (test in Task 3).
- A catering package is saved while another Admin saved it first → 409 `STALE_VERSION`. The panel shows the API message and a "Reload" button that loads the new record. Typed changes are not sent again silently (test in Task 1).
- A schedule or food list row whose booking is masked (`is_masked: true`, no `booking_id`) → it shows "Reserved (Private Session)" with a lock icon, no link, and no crash on the null fields (test in Task 4; link test in Task 9).
- Bookings filters with `from` after `to`, or an unknown `status` in the address → the API's 422 field message shows above the table, and the filters stay editable (test in Task 7).
- A confirmed booking whose meeting has ended → the door pass shows with an "Expired" mark (`expired: true`), and a booking that is not confirmed shows no "Show door pass" button (test in Task 8).

---

## Step A: no API change

### Task 1: Catering packages and IT services pages

**Files:**
- Create: `admin_dashboard/src/api/services.ts`, `admin_dashboard/src/utils/serviceForms.ts`, `admin_dashboard/src/views/ServiceCatalogView.vue`, `admin_dashboard/src/views/catalog/ServiceFormPanel.vue`
- Modify: `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/router/index.ts`, `admin_dashboard/src/layouts/nav.ts`, `admin_dashboard/src/components/list/ActiveToggle.vue`
- Test: `admin_dashboard/src/api/__tests__/services.spec.ts`, `admin_dashboard/src/utils/__tests__/serviceForms.spec.ts`, `admin_dashboard/src/views/__tests__/service-catalog.spec.ts`, `admin_dashboard/src/components/list/__tests__/active-toggle.spec.ts`

**Interfaces:**
- Consumes: `CatalogFilters` from `api/catalog.ts`; `orderProblem`, `orderValue` from `utils/sortOrder.ts`.
- Produces:
  - `types.ts`: `CateringPackageOut`, `CateringPackageCreate`, `CateringPackageUpdate`, `ITServiceOut`, `ITServiceCreate`, `ITServiceUpdate`.
  - `services.ts`: `type ServiceKind = 'catering' | 'it'`; `type ServiceOut = CateringPackageOut | ITServiceOut` (same fields). `listServicePage(client, kind, f: CatalogFilters): Promise<Page<ServiceOut>>`, `getService(client, kind, id)`, `createService(client, kind, body)`, `updateService(client, kind, id, changes)`. `catering` → `/api/v1/catering-packages`, `it` → `/api/v1/it-services`. The API has no GET by id, so `getService` looks through the list pages, as `getHoliday` does.
  - `serviceForms.ts`: `type ServiceForm = { name: string; description: string; sort_order: string }`; `emptyServiceForm()`, `serviceFormOf(s: ServiceOut)`, `serviceProblems(f)` → `"Enter the name."`, `"Use 2 to 200 characters."`, `"Max 1000 characters."` (description), the order message; `serviceCreateBody(f)` (trimmed; empty description left out; empty order → 0); `serviceChanges(f, s)` → only the changed fields **plus `version: s.version`**, or `{}` when nothing changed.
  - `SERVICE_KINDS: Record<ServiceKind, { title: string; one: string; many: string; serial: 'CP' | 'IS'; newLabel: string; empty: string }>` in `serviceForms.ts`: catering `{ 'Catering packages', 'package', 'packages', 'CP', 'New package', 'No catering packages yet' }`; it `{ 'IT services', 'service', 'services', 'IS', 'New service', 'No IT services yet' }`.
  - Routes (children of `shell`): `catering-packages` at `/catering-packages`, props `{ kind: 'catering' }`, title "Catering packages"; `it-services` at `/it-services`, props `{ kind: 'it' }`, title "IT services". Nav, in the Catalog group after Equipment: "Catering packages" (icon `utensils`), "IT services" (icon `monitor-cog`). Add both to `NAV_ICONS`.
  - `ServiceCatalogView` props `{ kind: ServiceKind }`: title, mono count (`004 packages`), primary "New package" / "New service"; search ("Search name") and `StatusFilter`; table: Serial, Name, Description (one line, cut with an ellipsis), Order, State. Row → `?id=3`.
  - `ServiceFormPanel` props `{ kind: ServiceKind; item: ServiceOut | null }`, emits `saved`, `close`. Fields: Name (`n/200`), Description (textarea, `n/1000`), Order. Foot: `ActiveToggle` (edit only), "Cancel", "Create package" / "Save changes". Drafts `catering:new`, `catering:{id}`, `it:new`, `it:{id}`. Toast "{name} saved", detail `CP·0003`. On `STALE_VERSION`: the API message at the top, plus a "Reload" button that calls `getService`, resets the form to the new record and clears the draft.
  - `ActiveToggle` `kind` adds `'catering package' | 'IT service'`. Both use no count. Text: `Bookings that have it keep it, but it cannot be chosen for new bookings. You can make it active again.` The page's `turn` sends `{ is_active, version }`.

- [ ] **Step 1: Write failing tests.**
  - `services.spec.ts`: `listServicePage(api, 'it', { search: 'mic', is_active: true, page: 1, size: 20 })` calls `/api/v1/it-services?search=mic&is_active=true&page=1&size=20`; `updateService(api, 'catering', 3, { version: 2, is_active: false })` sends `PATCH /api/v1/catering-packages/3` with `{"version":2,"is_active":false}`.
  - `serviceForms.spec.ts`: empty → `{ name: 'Enter the name.' }`; `'A'` → `'Use 2 to 200 characters.'`; a 1001-character description → `'Max 1000 characters.'`; `serviceChanges(serviceFormOf(s), s)` → `{}`; name changed on `s.version = 4` → `{ name: 'Lunch box', version: 4 }`; description cleared → `{ description: null, version: 4 }`.
  - `active-toggle.spec.ts`: kind `'catering package'` → the dialog says "cannot be chosen for new bookings".
  - `service-catalog.spec.ts`: `/catering-packages?search=tea` calls `/api/v1/catering-packages?search=tea&is_active=true&page=1&size=20`; a row shows `CP·0003`; `.count` says `002 packages`; create POSTs `{"name":"Coffee break","sort_order":0}`; 409 `DUPLICATE` with `fields.name` shows under Name; 409 `STALE_VERSION` shows its message and a "Reload" button, and clicking it fetches the list again and shows the new name; `/it-services` shows "IT services" and "New service"; the nav has both items with their routes.
- [ ] **Step 2: Run** `npx vitest run src/api/__tests__/services.spec.ts src/utils/__tests__/serviceForms.spec.ts src/views/__tests__/service-catalog.spec.ts src/components/list/__tests__/active-toggle.spec.ts`. Expected: FAIL (modules missing).
- [ ] **Step 3: Implement** the files above. Copy the structure of `EquipmentView.vue` and `EquipmentFormPanel.vue`, without the icon picker.
- [ ] **Step 4: Run** the same command, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: catering packages and IT services pages"`.

### Task 2: Rooms and places follow the booking rules

**Files:**
- Modify: `admin_dashboard/src/utils/roomForm.ts`, `admin_dashboard/src/views/rooms/RoomFormPanel.vue` (show `errors.is_private` under the Private switch)
- Test: `admin_dashboard/src/utils/__tests__/roomForm.spec.ts`, `admin_dashboard/src/views/__tests__/room-form.spec.ts`, `admin_dashboard/src/views/__tests__/floors.spec.ts`, `admin_dashboard/src/views/__tests__/offices.spec.ts`

**Interfaces:**
- Consumes: none new.
- Produces: `roomProblems(form)` adds `room_owner_id: 'A private room needs an owner.'` when `form.is_private && form.room_owner_id === null` (the API's text, OWNER_REQUIRED).

The API's other new refusals already carry a field the forms show. These tests pin that:
| Code | Field | Shown under |
| --- | --- | --- |
| `HAS_FUTURE_BOOKINGS` | `floor_id` (room), `building_id` (floor), `location_id` (building), `province` (office) | the parent picker |
| `HAS_FUTURE_BOOKINGS` | `is_active` | the `ActiveToggle` error (its `err.message`) |
| `HAS_PENDING_OWNER_BOOKINGS` | `is_private` | the Private switch |

- [ ] **Step 1: Write failing tests.**
  - `roomForm.spec.ts`: private with no owner → `room_owner_id: 'A private room needs an owner.'`; private with owner 7 → no `room_owner_id` problem; shared with no owner → none.
  - `room-form.spec.ts`: private ticked, no owner, Save → the message under Owner and no request sent; edit answer 409 `HAS_PENDING_OWNER_BOOKINGS`, `fields.is_private: "Resolve 3 bookings waiting for the room owner first."` → that text under the Private switch; 409 `HAS_FUTURE_BOOKINGS`, `fields.floor_id` → the text under Floor.
  - `floors.spec.ts`: 409 `HAS_FUTURE_BOOKINGS`, `fields.building_id` → under Building.
  - `offices.spec.ts`: 409 `HAS_FUTURE_BOOKINGS`, `fields.province` → under Province; making it inactive answers 409 `HAS_FUTURE_BOOKINGS`, `fields.is_active: "This office has 2 future bookings. Ask the bookers to cancel first."` → that text next to the switch, and the switch stays Active.
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/roomForm.spec.ts src/views/__tests__/room-form.spec.ts src/views/__tests__/floors.spec.ts src/views/__tests__/offices.spec.ts`. Expected: FAIL on the owner check and the `is_private` line. The other new tests may already pass; keep them.
- [ ] **Step 3: Implement** the owner check and the `is_private` error line.
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: private room needs an owner; booking guard messages on rooms and places"`.

### Task 3: Users follow the booking rules

**Files:**
- Modify: `admin_dashboard/src/components/list/ActiveToggle.vue` (`user` text), `admin_dashboard/src/views/people/UserPanel.vue`, `admin_dashboard/src/api/users.ts` (doc comments)
- Test: `admin_dashboard/src/components/list/__tests__/active-toggle.spec.ts`, `admin_dashboard/src/views/__tests__/user-panel.spec.ts`

**Interfaces:**
- Consumes: `UserChanged.bookings_cancelled: number[]` (B-27).
- Produces:
  - `ActiveToggle` kind `user`. Count 0: `They cannot sign in, and their bookings that have not ended are cancelled. You can make them active again.` Count n: `They cannot sign in, their bookings that have not ended are cancelled, and {n rooms lose their / 1 room loses its} owner. You can make them active again.`
  - `UserPanel`: `cancelled = ref<number[]>([])`, set from `user.bookings_cancelled` in `changed()`. When it is not empty, a second status box under the rooms box: "These bookings were cancelled:" and one mono item per id (`#12`). Task 9 turns them into links.

- [ ] **Step 1: Write failing tests.**
  - `active-toggle.spec.ts`: kind `user`, count 0 → the dialog has "their bookings that have not ended are cancelled"; count 2 → it also has "2 rooms lose their owner".
  - `user-panel.spec.ts`: turning off answers `{ ..., rooms_unassigned: [4], bookings_cancelled: [12, 15] }` → both boxes show, with `RM·0004`, `#12` and `#15`; it answers 409 `OWNER_HAS_PRIVATE_ROOMS`, `fields.is_active: "Assign a new owner for 2 private rooms first."` → that text next to the switch; saving roles answers 409 `OWNER_HAS_PRIVATE_ROOMS` → the text in the roles alert.
- [ ] **Step 2: Run** `npx vitest run src/components/list/__tests__/active-toggle.spec.ts src/views/__tests__/user-panel.spec.ts`. Expected: FAIL (old text, no cancelled box).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: turning a user off shows the bookings it cancelled"`.

### Task 4: Room schedule tab

**Files:**
- Create: `admin_dashboard/src/api/bookings.ts` (schedule part), `admin_dashboard/src/views/rooms/RoomSchedule.vue`, `admin_dashboard/src/utils/bookingLabels.ts`
- Modify: `admin_dashboard/src/utils/time.ts`, `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/views/rooms/RoomDetailPanel.vue`
- Test: `admin_dashboard/src/utils/__tests__/time.spec.ts`, `admin_dashboard/src/utils/__tests__/bookingLabels.spec.ts`, `admin_dashboard/src/views/__tests__/room-schedule.spec.ts`

**Interfaces:**
- Produces:
  - `time.ts`: `phnomPenhDate(now: Date): string` → `"2026-11-04"` (Phnom Penh day); `addDays(day: string, days: number): string` (plain calendar maths on `YYYY-MM-DD`); `formatDay(day: string): string` → `"Wed 4 Nov 2026"`.
  - `bookingLabels.ts`: `STATUS_LABELS`, `MEETING_TYPE_LABELS`, `ROUTE_LABELS` (texts in Global Constraints); `statusLabel(code: string): string` (unknown → the code itself).
  - `types.ts`: `ScheduleItem`.
  - `bookings.ts`: `getRoomSchedule(client, roomId: number, from: string, to: string): Promise<ItemList<ScheduleItem>>` → `GET /api/v1/rooms/{id}/schedule?from=&to=`.
  - `RoomStep` adds `'schedule'`. Tab label "Schedule", after Equipment.
  - `RoomSchedule.vue` props `{ roomId: number }`: a week starting today (`from` = `phnomPenhDate(new Date())`, `to` = from + 6). Buttons "Previous week", "Next week", "This week". Rows grouped by day (`formatDay` heading), each row: `09:00–10:30` (mono), title, reference code (mono), booker, status label. A masked row: lock icon, "Reserved (Private Session)", no reference and no booker. No rows: "No bookings this week." Error: the API message and "Try again".

- [ ] **Step 1: Write failing tests.**
  - `time.spec.ts`: `phnomPenhDate(new Date('2026-11-03T18:30:00Z'))` → `'2026-11-04'`; `addDays('2026-12-29', 6)` → `'2027-01-04'`; `formatDay('2026-11-04')` → `'Wed 4 Nov 2026'`.
  - `bookingLabels.spec.ts`: `statusLabel('PENDING_OWNER')` → `'Waiting for owner'`; `statusLabel('NEW_THING')` → `'NEW_THING'`.
  - `room-schedule.spec.ts` (time frozen at `2026-11-04T01:00:00Z`): opening the tab calls `/api/v1/rooms/12/schedule?from=2026-11-04&to=2026-11-10`; "Next week" calls `from=2026-11-11&to=2026-11-17`; two rows on one day show under one heading; a masked row (`booking_id: null`, `reference_code: null`, `requester_name: null`, `is_masked: true`) shows the lock and the masked title; an empty list shows "No bookings this week."; `?room=12&step=schedule` opens on the tab.
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/time.spec.ts src/utils/__tests__/bookingLabels.spec.ts src/views/__tests__/room-schedule.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.** The schedule loads only when its tab is first opened.
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: room schedule tab"`.

### Task 5: Food list page

**Files:**
- Create: `admin_dashboard/src/views/FoodListView.vue`
- Modify: `admin_dashboard/src/api/bookings.ts`, `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/router/index.ts`, `admin_dashboard/src/layouts/nav.ts`
- Test: `admin_dashboard/src/views/__tests__/food-list.spec.ts`

**Interfaces:**
- Consumes: Task 4 (`phnomPenhDate`, `addDays`, `formatDay`, `statusLabel`).
- Produces:
  - `types.ts`: `CateringOrderItem`.
  - `bookings.ts`: `getFoodList(client, day: string): Promise<ItemList<CateringOrderItem>>` → `GET /api/v1/pitika/catering?date=`.
  - Nav: a new group **"Bookings"** placed after Rooms, with "Food list" (icon `utensils-crossed`, route `food-list`). Route `food-list` at `/food-list`, title "Food list". The day lives in the address (`?date=2026-11-04`); no date means today.
  - `FoodListView`: heading "Food list" + `formatDay(day)`; "Previous day", "Today", "Next day" and a date input. Table (the API sorts it): Time (`delivery_time`, mono), Room (Khmer over English, office below), Meeting (title + reference code), Servings (mono, right), Packages (names joined with ", "), Remarks, Pitika notes (`approver_notes`), Status. Empty: "No food orders on this day." No paging (the answer is an `ItemList`).

- [ ] **Step 1: Write failing tests** in `food-list.spec.ts` (time frozen at `2026-11-04T01:00:00Z`): `/food-list` calls `/api/v1/pitika/catering?date=2026-11-04`; "Next day" changes the address to `?date=2026-11-05` and calls again; a row shows `12:00`, the packages `"Coffee break, Lunch box"`, servings `25` and "Confirmed"; empty → "No food orders on this day."; the nav group "Bookings" has "Food list".
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/food-list.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: the day's food list"`.

---

## Step B: Admin bookings

### Task 6: API `GET /bookings` for the Admin

**Files:**
- Modify: `app/services/booking_review.py`, `app/routers/bookings.py`, `docs/superpowers/specs/2026-11-03-room-booking-api-design.md` (add B-32 to section 2 and a 9.5b section), `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (section 4: bookings read-only for Admin; section 10: a "Phase 7: Bookings" table with DSH-B01 list, DSH-B02 detail, DSH-B03 door pass on request, DSH-B04 calendar file)
- Test: `tests/test_admin_bookings.py`

**Interfaces:**
- Consumes: `_list_in_rooms(session, room_ids, page, size, status, date_from, date_to, room_id, q)`, `booking_access.room_ids_in_province(code)`, `booking_view.build_booking_list_items`, `AdminUser`, `ProvinceQuery`, `IdQuery`, `SearchQuery`, `PageParams`.
- Produces:
  - `booking_review.list_admin_bookings(session, page, size, status, province, date_from, date_to, room_id, q) -> dict`: room ids = `select(Room.id)` when `province` is None or blank, else `room_ids_in_province(province)`. Then `_list_in_rooms`. Put it in a new `# --- Admin` section.
  - `GET /api/v1/bookings` in `bookings.py`, summary "List all bookings (Admin)", `AdminUser`, query `status`, `from`, `to` (aliases as in `pitika_bookings.py`), `province`, `room_id`, `q`, paging. Answer `Page[BookingListItem]`. Docstring: every province; sort by first start, then id; `q` matches title, reference code, booker name.
  - Spec B-32: "Admin list. `GET /bookings` lists every booking for the Admin, with the Pitika list's filters plus `province`. Read only: the Admin still cannot approve, reject, cancel or edit (decided Nov 4, 2026)."

- [ ] **Step 1: Write failing tests** in `tests/test_admin_bookings.py` (use the `frozen`, `make_booking`, `make_bookable_room`, `make_user`, `auth_headers` fixtures; Admin = `make_user(roles=["ADMIN"])`):
  - `test_admin_sees_every_province`: one booking in a `PHNOM_PENH` room, one in `SIEM_REAP` → both ids, `total == 2`.
  - `test_province_filter`: `?province=SIEM_REAP` → only that one.
  - `test_status_filter_uses_display_status`: a CONFIRMED booking that has ended and one that has not → `?status=COMPLETED` gives the ended one, `?status=CONFIRMED` gives the other.
  - `test_bad_status_422`: `?status=NOPE` → 422 with `fields.status`.
  - `test_from_to_room_and_q`: copy the Pitika `test_list_from_to_match_any_session`, `test_list_filters` and `test_list_q_matches_requester_name` cases on `/bookings`.
  - `test_sorted_by_first_start`: two bookings → earliest first start first.
  - `test_not_admin_403`: STAFF and PITIKA users → 403.
  - `test_query_count_does_not_grow`: copy `test_list_query_count_does_not_grow` from `tests/test_pitika_bookings.py`.
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_admin_bookings.py -q`. Expected: FAIL (405 Method Not Allowed on `GET /bookings`).
- [ ] **Step 3: Implement** the service function, the route, and the two spec notes.
- [ ] **Step 4: Run** `.venv/Scripts/python -m pytest -q` and `.venv/Scripts/ruff check .`. Expected: all pass.
- [ ] **Step 5: Regenerate types:** start the API, run `npm run gen:api` in `admin_dashboard/`. `git diff src/api/schema.d.ts` shows a `get` on `"/api/v1/bookings"`.
- [ ] **Step 6: Commit** `git commit -m "Booking: Admin list of all bookings (B-32)"`, including `schema.d.ts` and both specs.

### Task 7: Bookings list page

**Files:**
- Create: `admin_dashboard/src/views/BookingsView.vue`, `admin_dashboard/src/views/bookings/BookingFilters.vue`, `admin_dashboard/src/views/bookings/bookingFilters.ts`
- Modify: `admin_dashboard/src/api/bookings.ts`, `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/router/index.ts`, `admin_dashboard/src/layouts/nav.ts`
- Test: `admin_dashboard/src/api/__tests__/bookings.spec.ts`, `admin_dashboard/src/views/__tests__/bookings-list.spec.ts`

**Interfaces:**
- Consumes: Tasks 4–6; `listProvinces(client)` from `api/references.ts` for the Province select; `SearchPicker` over `listRooms` for the Room filter (as the Rooms page's owner filter does).
- Produces:
  - `types.ts`: `BookingListItem`, `BookingDetail`, `DoorPassOut`.
  - `bookings.ts`: `interface BookingFilters { status?: string; province?: string; room_id?: number; from?: string; to?: string; q?: string; page?: number; size?: number }`; `listBookingPage(client, f): Promise<Page<BookingListItem>>` → `GET /api/v1/bookings`.
  - `bookingFilters.ts`: `BOOKING_FILTERS`, the address keys and their parsers, in the same shape as `views/rooms/roomFilters.ts`.
  - Nav group "Bookings": "Bookings" (icon `calendar-check`, route `bookings`) first, then "Food list". Route `bookings` at `/bookings`, title "Bookings".
  - `BookingsView`: title + mono count (`012 bookings`). Filters: search ("Search title, reference or booker"), Status (All + the seven labels), Province, Room, From, To. "Clear filters" when any is set. Table: Reference (mono), Meeting (title; meeting type label below), Room (Khmer over English; office below), Booker, First session (`formatDay` + `09:00–10:30`; `+2 more` when `session_count > 1`), Status, Services (small `utensils` / `monitor` marks when `has_catering` / `has_it`). Row → `?id=12`. Empty: "No bookings yet" and "No bookings match" with "Clear filters". A 422 answer shows the field message above the table, and the filters stay usable.

- [ ] **Step 1: Write failing tests.**
  - `bookings.spec.ts`: `listBookingPage(api, { status: 'CONFIRMED', province: 'SIEM_REAP', from: '2026-11-01', to: '2026-11-30', q: 'NBC-26', page: 1, size: 20 })` calls `/api/v1/bookings?status=CONFIRMED&province=SIEM_REAP&from=2026-11-01&to=2026-11-30&q=NBC-26&page=1&size=20`.
  - `bookings-list.spec.ts`: `/bookings?status=PENDING_OWNER` sends that status and the select shows "Waiting for owner"; a row shows `NBC-26-48213`, "Internal", `+2 more` for `session_count: 3`, and the food mark; `.count` says `001 booking` for 1; a 422 with `fields.to: "..."` shows that text above the table; clicking a row puts `?id=12` in the address; the nav item "Bookings" has route `bookings`.
- [ ] **Step 2: Run** `npx vitest run src/api/__tests__/bookings.spec.ts src/views/__tests__/bookings-list.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.** Copy the structure of `RoomsView.vue` and `RoomFilters.vue`.
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: bookings list for the Admin"`.

### Task 8: Booking detail panel, door pass and calendar file

**Files:**
- Create: `admin_dashboard/src/views/bookings/BookingPanel.vue`
- Modify: `admin_dashboard/src/api/bookings.ts`, `admin_dashboard/src/views/BookingsView.vue`
- Test: `admin_dashboard/src/views/__tests__/booking-panel.spec.ts`

**Interfaces:**
- Consumes: Task 7; `client.requestBlob(path)`.
- Produces:
  - `bookings.ts`: `getBooking(client, id): Promise<BookingDetail>`, `getDoorPass(client, id): Promise<DoorPassOut>`, `getBookingIcs(client, id): Promise<Blob>` (`requestBlob('/api/v1/bookings/{id}/ics')`).
  - `BookingPanel` props `{ bookingId: number }`, emits `close`. Read only: no form, no save. Title = meeting title, subtitle = reference code, status label in the header. Tabs:
    - "Details": room (link to `?room=` on the Rooms page), route label, meeting type, purpose, attendees, private reason, participants, booker (`requester_info`: names, staff ID, position, division, department, office, email, phone).
    - "Sessions {n}": one line per session (`formatDay`, `09:00–10:30`), and "Ends {formatDay(last_end.date)} {last_end.time}".
    - "Services": food (packages, servings, delivery day and time, remarks, Pitika notes, decided by / at) and IT (items, special needs, status, staff, setup day and time, technician notes, forwarded / assigned / ready at). "No food ordered." / "No IT help asked." when null.
    - "History": the reviews in order (stage, decision, reviewer, notes, time), then the rejection (by, actor, reason, time) or the cancel (time, reason). Every `_at` value goes through `formatPhnomPenh`.
  - Header buttons: "Calendar file" downloads `{reference_code}.ics` from the blob (object URL, then revoke it). "Show door pass" only when `status === 'CONFIRMED'` (the stored status, so also for COMPLETED): click → `getDoorPass` → the passcode in mono + "Valid until {formatPhnomPenh(expires_at)}" + an "Expired" mark when `expired`. "Hide" clears it. A 403/404 shows the API message in place of the code.

- [ ] **Step 1: Write failing tests** in `booking-panel.spec.ts`: `/bookings?id=12` calls `/api/v1/bookings/12` and shows the title and `NBC-26-48213`; the Sessions tab lists 3 lines; a booking with `catering: null` shows "No food ordered."; History shows "Rejected by Pitika" and the reason; the door pass is not in the page until clicked, and clicking calls `/api/v1/bookings/12/door-pass` and shows `NBC-48213`; `expired: true` shows "Expired"; a `PENDING_PITIKA` booking has no "Show door pass" button; "Calendar file" calls `/api/v1/bookings/12/ics`; the panel has no Save, Approve, Reject or Cancel button.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/booking-panel.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.** Use `usePanelRecord` so the booking loads before the panel opens, as on the other pages.
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: booking detail, door pass on request, calendar file"`.

### Task 9: Links, end-to-end checks and notes

**Files:**
- Modify: `admin_dashboard/src/views/rooms/RoomSchedule.vue`, `admin_dashboard/src/views/FoodListView.vue`, `admin_dashboard/src/views/people/UserPanel.vue`, `admin_dashboard/e2e/panel-motion.spec.ts`, `admin_dashboard/README.md`, `DESIGN.md`
- Create: `admin_dashboard/e2e/bookings.spec.ts` (real API), `admin_dashboard/e2e/bookings-layout.spec.ts` (mocked)
- Test: `room-schedule.spec.ts`, `food-list.spec.ts`, `user-panel.spec.ts`

**Interfaces:**
- Consumes: route `bookings` with `?id=`.
- Produces: links to `{ name: 'bookings', query: { id } }` from schedule rows with a `booking_id`, from food list rows (`booking_id`), and from the cancelled-bookings box in `UserPanel`. Masked rows stay plain text.

- [ ] **Step 1: Write failing tests:** a schedule row with `booking_id: 7` links to `/bookings?id=7`, and a masked row has no link; a food row links to `/bookings?id=7`; the user panel's `#12` links to `/bookings?id=12`.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/room-schedule.spec.ts src/views/__tests__/food-list.spec.ts src/views/__tests__/user-panel.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the links.
- [ ] **Step 4: E2E.**
  - Real API (skipped without `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD`): sign in → Catalog → "New package" with a unique name → it shows in the list → Bookings → the list loads → open the first row if there is one → the Sessions tab shows at least one line.
  - Mocked layout: `/catering-packages`, `/food-list` and `/bookings` at 1366, 900 and 390 px have no sideways page scroll; at 390 px the open booking panel has no sideways scroll. Add `/catering-packages`, `/it-services` and `/bookings` to the slide-in-once cases in `panel-motion.spec.ts`.
- [ ] **Step 5: Notes.** `README.md`: Catalog (packages, services), Bookings (list, detail, food list, read only). `DESIGN.md`: serials CP and IS; the status labels; the "door pass on request" rule next to the door code rule.
- [ ] **Step 6: Full verification.** In `admin_dashboard/`: `npm run lint`, `npm run type-check`, `npx vitest run`, `npm run build`, `npx playwright test`. Expected: all pass (real-API tests may be skipped). In the repo root: `.venv/Scripts/python -m pytest -q` and `.venv/Scripts/ruff check .` pass.
- [ ] **Step 7: Commit** `git commit -m "Dashboard: booking links, end-to-end checks and notes"`.
