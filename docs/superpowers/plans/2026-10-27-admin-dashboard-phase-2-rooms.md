# Admin Dashboard Phase 2 (Rooms) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Rooms pages of the admin dashboard: a filtered, paged room list, room detail, create and edit in a side panel, turn off/on, door code on request, photos (upload, reorder, delete) and equipment.

**Architecture:** Builds on Phase 1 (`feature/dashboard-phase-1`): the `api` client, `ApiError`, session store, shell, base components, `useFieldErrors`, `useToast`, drafts store and `usePrivateImage`. New code adds typed API functions for rooms and their reference lists, a URL-synced list query composable, reusable list parts (paging foot, status filter, state marks, empty state, skeleton, side panel), and the Rooms view with its panels. Every page in later phases reuses the list parts and the side panel.

**Tech Stack:** Vue 3 (`<script setup lang="ts">`), TypeScript, Vue Router, Pinia, Tailwind CSS v4 tokens + scoped CSS, `lucide-vue-next`, Vitest + `@vue/test-utils` + jsdom, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (DSH-R01 to DSH-R08 in section 10, DSH-G01 to DSH-G10 in section 9). API contract: `spec.md` section 13 (rooms, photos, equipment) and the live `/openapi.json`. Visual source: `docs/design/admin-direction.html` (rooms table, filter row, paging foot, side panel form, empty and loading states) and `DESIGN.md`.

## Global Constraints

- Work on a new branch `feature/dashboard-phase-2`, created from the tip of `feature/dashboard-phase-1`. Commit messages carry no AI attribution lines.
- API types come only from `src/api/schema.d.ts` (`npm run gen:api`, API running); no hand-written API shapes.
- Lists: `page` and `size` (20 by default, choices 20 / 50 / 100, API max 100); always show the total (G01).
- Every list filter lives in the page address (route query), so a list can be reloaded or shared (G02). Default values are left out of the address.
- Create and edit open in a 440px side panel over the list; save sends only changed fields (PATCH) (G03).
- API errors: each `fields` message under its field; `message` at the top of the form (G04). Codes in plain words (G05): 409 `DUPLICATE`, 409 `INACTIVE_REFERENCE`, 422 `VALIDATION_ERROR` — show the API's own `message` text.
- Client checks before sending use the API limits (G06): names 1–100, short description ≤ 200, description ≤ 1000, door code ≤ 50, capacity 1–10000, size 1–100000 m², times `HH:MM` with opening before closing.
- "Turn off / Turn on", never delete, confirmed inline on the page (G07). Turning on can be refused by the API (its floor, building or office is off): show the API message.
- Parent selects (office, building, floor, room type, owner) load from the API and hide inactive items, except the one already chosen (G08).
- After a save: toast + refresh the list (G09). Empty list: say what is missing + an "Add" button. Loading: skeleton rows, not a spinner (G10).
- Door code never appears in a list, detail or log; only after "Show door code" calls `GET /rooms/{id}/door-code` (DSH-R05).
- Room name plate shows **Khmer over English** (owner decision, DESIGN.md "Two Names Rule"). Record ids show as serials: crimson prefix, middle dot, 4 zero-padded digits, e.g. `RM·0012`.
- State is shown by shape + word, never coloured pills: Active = 8px solid ok-green dot + "Active"; Inactive = 7px ring (1.5px off-ring) + "Inactive"; Private = 13px Lucide `Lock` + "Private" in warn; Not bookable = 13px Lucide `CalendarX` + "Not bookable" in off ink.
- Time values from the API (`start_time`, `end_time`) are Cambodia local `HH:MM` already — show as given (`08:00–17:00`), do not convert. Timestamps (`created_at`, `updated_at`) are UTC: show with `formatPhnomPenh`.
- Photos are public files: show `PhotoOut.thumbnail_url` / `url` as `${apiBaseUrl}${path}` in a plain `<img>` (no token needed).
- Day and night themes must both work: use colour tokens only (`var(--color-…)`), no new hard-coded colours.
- English UI, no emoji, Lucide icons at stroke 1.75.

## Review Focus

- A list address with a filter id that no longer exists or is now inactive (`?location_id=999`) → the list still loads (the API filters by id); the office select shows "Unknown office" for that value instead of a blank or a crash (test in Task 5).
- Changing the office after a building and floor were chosen → building and floor reset (in the filter row and in the form), never a floor from another office sent to the API (tests in Tasks 5 and 6).
- Editing a room and changing nothing but typing then clearing the door code → no `door_code` is sent (an empty door-code box means "keep the current one", it does not erase it) (test in Task 6).
- A photo upload where some files are refused (413 / 415 / 409 limit reached after 20) → the good files still upload, each refused file shows its API message by name, the grid stays correct (test in Task 8).
- Reorder fails on the server (422 because another admin added a photo) → the grid goes back to the server's order and shows the message, never a silently wrong order (test in Task 8).

---

### Task 1: Room and reference API functions

**Files:**
- Modify: `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/api/schema.d.ts` (regenerate)
- Create: `admin_dashboard/src/api/query.ts`, `admin_dashboard/src/api/rooms.ts`, `admin_dashboard/src/api/references.ts`
- Test: `admin_dashboard/src/api/__tests__/rooms.spec.ts`

**Interfaces:**
- Consumes: `ApiClient` from `api/client.ts` (`request<T>(method, path, body?)`).
- Produces:
  - `types.ts` adds: `RoomListItem`, `RoomDetail`, `RoomCreate`, `RoomUpdate`, `DoorCode`, `PhotoOut`, `EquipmentOut`, `CategoryOut`, `LocationOut`, `BuildingOut`, `FloorOut`, `UserListItem`, `ProvinceRef`, `NamedRef`, and `Page<T> = { items: T[]; page: number; size: number; total: number }`, `ItemList<T> = { items: T[]; total: number }`.
  - `query.ts`: `toQuery(params: Record<string, string | number | boolean | number[] | null | undefined>): string` — drops `undefined`, `null`, `''` and empty arrays; arrays joined with commas (`equipment_ids=1,4`); booleans as `true`/`false`; returns `''` or `?a=1&b=2` (URL-encoded, keys in insertion order).
  - `rooms.ts`: `RoomFilters = { province?: string; location_id?: number; building_id?: number; floor_id?: number; category_id?: number; min_capacity?: number; equipment_ids?: number[]; owner_id?: number; has_owner?: boolean; is_active?: boolean; is_bookable?: boolean; is_private?: boolean; search?: string; page?: number; size?: number }`; `listRooms(client, f: RoomFilters): Promise<Page<RoomListItem>>` (GET `/api/v1/rooms`), `getRoom(client, id): Promise<RoomDetail>`, `createRoom(client, body: RoomCreate): Promise<RoomDetail>` (POST), `updateRoom(client, id, changes: RoomUpdate): Promise<RoomDetail>` (PATCH), `getDoorCode(client, id): Promise<DoorCode>`, `uploadRoomPhoto(client, id, file: File): Promise<PhotoOut>` (POST `/rooms/{id}/photos`, FormData field `file`), `reorderRoomPhotos(client, id, photoIds: number[]): Promise<ItemList<PhotoOut>>` (PUT `/rooms/{id}/photos/order`, body `{photo_ids}`), `deleteRoomPhoto(client, id, photoId): Promise<void>`, `setRoomEquipment(client, id, equipmentIds: number[]): Promise<ItemList<EquipmentOut>>` (PUT `/rooms/{id}/equipment`, body `{equipment_ids}`).
  - `references.ts`: `listAll<T>(client, path: string, params?): Promise<T[]>` — fetches `size=100` pages until `items` collected reach `total`; `listOffices(client)` → `LocationOut[]` (`/api/v1/locations`), `listBuildings(client, locationId?: number)` → `BuildingOut[]`, `listFloors(client, buildingId?: number)` → `FloorOut[]`, `listRoomTypes(client)` → `CategoryOut[]` (`/api/v1/categories`), `listEquipment(client)` → `EquipmentOut[]`, `listProvinces(client)` → `ProvinceRef[]` (`/api/v1/provinces`, an `ItemList`), `listRoomOwners(client)` → `UserListItem[]` (`/api/v1/users?role=ROOM_OWNER&is_active=true`). All reference lists ask for every status (no `is_active` filter) except owners, so the UI can show the chosen inactive item (G08).

- [ ] **Step 1: Regenerate types** — API running, `npm run gen:api`; confirm `schema.d.ts` has `RoomCreate` with `room_owner_id` and `door_code`.
- [ ] **Step 2: Write failing tests** in `rooms.spec.ts` (fake `fetchImpl` as in `endpoints.spec.ts`):
  - `toQuery({ search: 'board', location_id: 3, equipment_ids: [1, 4], has_owner: false, floor_id: undefined, owner_id: null, province: '' })` → `'?search=board&location_id=3&equipment_ids=1%2C4&has_owner=false'`; `toQuery({})` → `''`.
  - `listRooms(client, { is_active: true, page: 2, size: 50 })` calls `GET …/api/v1/rooms?is_active=true&page=2&size=50`.
  - `createRoom` sends POST with exactly the given JSON; `updateRoom(client, 12, { capacity: 14 })` sends PATCH `/api/v1/rooms/12` body `{"capacity":14}`.
  - `uploadRoomPhoto` sends a `FormData` whose `file` is the given `File`; `reorderRoomPhotos(client, 12, [33, 31])` sends PUT `/api/v1/rooms/12/photos/order` body `{"photo_ids":[33,31]}`; `setRoomEquipment(client, 12, [1, 4])` sends PUT body `{"equipment_ids":[1,4]}`.
  - `listAll` with a fake API answering `total: 150` in two pages calls `page=1&size=100` then `page=2&size=100` and returns 150 items; `listRoomOwners` asks `?role=ROOM_OWNER&is_active=true&page=1&size=100`.
- [ ] **Step 3: Run** `npx vitest run src/api/__tests__/rooms.spec.ts`. Expected: FAIL (modules missing).
- [ ] **Step 4: Implement** `query.ts`, `rooms.ts`, `references.ts`, the `types.ts` aliases.
- [ ] **Step 5: Run** the same command. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: room and reference API functions"`.

### Task 2: URL-synced list query

**Files:**
- Create: `admin_dashboard/src/composables/useListQuery.ts`
- Test: `admin_dashboard/src/composables/__tests__/useListQuery.spec.ts`

**Interfaces:**
- Consumes: Vue Router `useRoute`, `useRouter`.
- Produces: `type FilterSpec = Record<string, 'string' | 'int' | 'bool' | 'ints'>`; `useListQuery(spec: FilterSpec)` returns `{ filters: Readonly<Ref<Record<string, unknown>>>, page: Ref<number>, size: Ref<number>, status: Ref<'active' | 'inactive' | 'all'>, set(changes: Record<string, unknown>): void, reset(): void, apiParams: ComputedRef<Record<string, unknown>> }`.
  - Reads the route query on every change; bad values (`page=abc`, `location_id=x`, `size=7`) fall back to defaults (page 1, size 20, status `active`).
  - `status` maps to the API's `is_active`: `active` → `true`, `inactive` → `false`, `all` → omitted. Default `active` is left out of the address; `all` writes `status=all`.
  - `set()` merges changes, drops empty values, resets `page` to 1 unless `page` itself is in the changes, and writes with `router.replace` (no history entry per keystroke).
  - `apiParams` = filters + `is_active` + `page` + `size`, ready for `listRooms`.
  - The search box value is debounced by the view (Task 5), not here.

- [ ] **Step 1: Write failing tests** (router with `createMemoryHistory`): starting at `/?search=board&location_id=3&page=2` → `filters.value` = `{ search: 'board', location_id: 3 }`, `page.value === 2`, `apiParams.value` includes `is_active: true`; `set({ building_id: 5 })` → query has `building_id=5` and no `page`; `set({ page: 3 })` keeps other filters and sets `page=3`; `status.value = 'all'` writes `status=all` and `apiParams` has no `is_active`; `/?page=abc&size=7&location_id=x` → page 1, size 20, no `location_id`; `reset()` → empty query.
- [ ] **Step 2: Run** `npx vitest run src/composables/__tests__/useListQuery.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `useListQuery`.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: list filters kept in the page address"`.

### Task 3: Reusable list parts

**Files:**
- Create: `admin_dashboard/src/components/list/PagingFoot.vue`, `StatusFilter.vue`, `StateMarks.vue`, `EmptyState.vue`, `TableSkeleton.vue`; `admin_dashboard/src/utils/serial.ts`; styles for the open-sheet table in `admin_dashboard/src/styles/main.css` (`@layer components`: `.sheet`, `.table-scroll`, `table.list`, `th`, `td`, `.num`, `.name-plate`, `.place`, row hover) copied in spirit from `docs/design/admin-direction.html` and DESIGN.md "Table" / "Paging Foot" / "Empty State" / "Loading Skeleton".
- Test: `admin_dashboard/src/components/list/__tests__/list-parts.spec.ts`, `admin_dashboard/src/utils/__tests__/serial.spec.ts`

**Interfaces:**
- Produces:
  - `serial(prefix: string, id: number | null): string` → `serial('RM', 12) === 'RM·0012'`, `serial('RM', 123456) === 'RM·123456'`, `serial('RM', null) === 'RM·new'`.
  - `PagingFoot` props `{ page: number; size: number; total: number }`, emits `update:page(n)`, `update:size(n)`. Shows mono range `1–20 of 57` (`0 of 0` when empty), a "Rows" select (20/50/100), and a pager: previous, up to 5 page numbers around the current one with the first and last always shown and `…` gaps, next. Current page has `aria-current="page"`; previous/next are disabled at the ends.
  - `StatusFilter` `v-model: 'active' | 'inactive' | 'all'`; a segmented group (`role="group"`, `aria-label="Status"`), buttons "Active", "Inactive", "All" with `aria-pressed`.
  - `StateMarks` props `{ active: boolean; bookable?: boolean; private?: boolean }`; renders the marks exactly as in Global Constraints; "Not bookable" only when `active && bookable === false`.
  - `EmptyState` props `{ title: string; text: string }`, default slot = actions. Includes the guilloche rosette watermark (240px, two hypotrochoid strokes 0.5, crimson at 7% opacity, `aria-hidden`) per DESIGN.md "Empty State".
  - `TableSkeleton` props `{ columns: string[]; rows?: number }` (column CSS widths), `rows` default 8; `aria-hidden="true"`.

- [ ] **Step 1: Write failing tests:** the `serial` cases above; `PagingFoot` with `page 3, size 20, total 57` shows `41–57 of 57`, next disabled, clicking "2" emits `update:page` with 2, choosing 50 emits `update:size` 50; with `total 0` shows `0 of 0` and both arrows disabled; with `total 1000, page 25` shows `1 … 24 25 26 … 50`. `StatusFilter` click "All" emits `'all'` and only that button has `aria-pressed="true"`. `StateMarks` `{ active: false }` shows "Inactive" and not "Not bookable"; `{ active: true, bookable: false, private: true }` shows "Active", "Not bookable", "Private".
- [ ] **Step 2: Run** `npx vitest run src/components/list src/utils/__tests__/serial.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the five components, `serial.ts` and the table styles (tokens only).
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: paging, status filter, state marks, empty state, skeleton"`.

### Task 4: Side panel

**Files:**
- Create: `admin_dashboard/src/components/base/SidePanel.vue`
- Test: `admin_dashboard/src/components/base/__tests__/side-panel.spec.ts`

**Interfaces:**
- Produces: `SidePanel` props `{ open: boolean; title: string; serial?: string }`, emits `close`; slots `default` (scrolling body) and `foot` (right-aligned actions on paper). Per DESIGN.md "Side Panel": 440px wide (full width at ≤ 760px), anchored right under the top bar, sheet ground, panel shadow, 1px left hairline, over the scrim. Head: 17px title, mono serial, close icon button (aria-label "Close"). Escape and a scrim click emit `close`. On open, focus moves to the first `[aria-invalid="true"]` field, else the first input/select/textarea in the body, else the close button; on close, focus returns to the element focused before opening. `role="dialog"`, `aria-modal="false"`, `aria-labelledby` the title. Enter/exit: transform `translateX(100%)` → `0`, 280ms `var(--ease-out-quint)`; scrim fades 200ms `ease`.

- [ ] **Step 1: Write failing tests:** opening focuses the first input in the body; with an `aria-invalid="true"` input present, that one is focused; Escape emits `close`; clicking the scrim emits `close`; the close button emits `close`; after `open` goes false, focus is back on the button that opened it.
- [ ] **Step 2: Run** `npx vitest run src/components/base/__tests__/side-panel.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `SidePanel.vue` (`<Teleport to="body">` + `<Transition>`).
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: side panel"`.

### Task 5: Rooms list

**Files:**
- Create: `admin_dashboard/src/views/RoomsView.vue`, `admin_dashboard/src/views/rooms/RoomFilters.vue`, `admin_dashboard/src/views/rooms/RoomsTable.vue`
- Modify: `admin_dashboard/src/router/index.ts` (route `home` at `''` loads `RoomsView`, title "Rooms"); delete `admin_dashboard/src/views/HomeView.vue`
- Test: `admin_dashboard/src/views/__tests__/rooms-list.spec.ts`

**Interfaces:**
- Consumes: Tasks 1–4; `api` from `api/index.ts`.
- Produces: `RoomsView` (route `home`). The panels of Tasks 6–7 open from it through the route query: `?room=12` opens the detail panel for room 12, `?room=new` opens the create panel; closing removes the key. `RoomsView` exposes `refresh(): Promise<void>` to its panels through a `@saved` event.
- Layout per `docs/design/admin-direction.html`: headline "Rooms" + mono count (`057 rooms`, zero-padded to 3) + primary "New room" (opens `?room=new`); one filter row: search (Lucide `Search`, placeholder "Search name or description", 300ms debounce), Office, Building, Floor, Room type selects, `StatusFilter`, quiet "More filters" (Lucide `SlidersHorizontal`) that shows a second row with Province, Min. seats (number), Equipment (multi-select checklist popover, "Has all of"), Owner (owner list + "No owner" → `has_owner=false`), Bookable (All / Yes / No), Private (All / Private / Public). The second row opens on load when any of its filters is set.
- Cascades: choosing an office loads its buildings and clears building and floor; choosing a building loads its floors and clears floor. Selects show active items, plus the currently chosen one if inactive (suffix " (off)"), plus "Unknown office/building/floor/type" when the chosen id is not in the list.
- Table columns: Serial (`RM·0012`), Room (Khmer name over English), Type, Place (office over "Building · Floor"), Seats (right, mono), Hours (mono `08:00–17:00`), Owner ("No owner" in off tone when null), State (`StateMarks` with `is_active`, `is_bookable`, `is_private`), actions (ellipsis icon button, aria-label "Open {name_en}"). Inactive rows: every cell but State and actions in the off tone. A row click or Enter opens `?room={id}`. At ≤ 1100px hide Type and Owner; at ≤ 760px hide Serial and Hours.
- Loading: `TableSkeleton`. Empty with no filters: "No rooms yet" / "Add the first meeting room." + primary "New room". Empty with filters: "No rooms match" / a sentence naming the active filters, e.g. "Nothing in Head Office, Building A, active only." + secondary "Clear filters" (`reset()`) + primary "New room". API error: the message in a `.summary` alert with "Try again".

- [ ] **Step 1: Write failing tests** (router with memory history, stubbed `fetch` answering by path): at `/?location_id=3&search=board` the rooms call has `location_id=3&search=board&is_active=true&page=1&size=20`; rows render Khmer then English name, `RM·0012`, `08:00–17:00`, "No owner"; the count reads `002 rooms`; choosing a building, then a different office, leaves the query with the new `location_id` and no `building_id`/`floor_id`; `?location_id=999` (not in the offices list) still loads rooms and the Office select shows "Unknown office"; clicking a row sets `room=12` in the query; an empty answer with no filters shows "No rooms yet", with filters shows "No rooms match" and "Clear filters" empties the query; while the rooms call is pending a skeleton (`[aria-hidden="true"].skeleton`) shows; paging foot "2" changes the query to `page=2`.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/rooms-list.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the view, filters, table; switch the `home` route.
- [ ] **Step 4: Run** again, then the whole suite `npx vitest run`. Expected: PASS (update the Phase 1 shell/router tests only where they referenced `HomeView` text).
- [ ] **Step 5: Commit** `git commit -m "Dashboard: rooms list with filters, paging and empty states"`.

### Task 6: Room form (create and edit)

**Files:**
- Create: `admin_dashboard/src/views/rooms/RoomFormPanel.vue`, `admin_dashboard/src/utils/roomForm.ts`
- Test: `admin_dashboard/src/utils/__tests__/roomForm.spec.ts`, `admin_dashboard/src/views/__tests__/room-form.spec.ts`

**Interfaces:**
- Consumes: Tasks 1, 4; `useFieldErrors`, `FormErrorSummary`, `BaseField`, `BaseSwitch`, `PasswordInput`, `useDraftsStore`, `useToast`.
- Produces:
  - `roomForm.ts`: `type RoomForm = { name_kh: string; name_en: string; location_id: number | null; building_id: number | null; floor_id: number | null; category_id: number | null; capacity: string; size_sqm: string; start_time: string; end_time: string; short_desc: string; description: string; door_code: string; room_owner_id: number | null; is_private: boolean }`; `emptyRoomForm(): RoomForm` (times `08:00` / `17:00`, private false); `roomFormOf(room: RoomDetail): RoomForm` (door code always `''`); `roomProblems(form: RoomForm): Record<string, string>` with messages: `"Enter the Khmer name."`, `"Enter the English name."`, `"Max 100 characters."`, `"Choose an office."`, `"Choose a building."`, `"Choose a floor."`, `"Choose a room type."`, `"Seats must be a whole number from 1 to 10000."`, `"Size must be a whole number from 1 to 100000."`, `"Use HH:MM, for example 08:00."`, `"Opening must be before closing."` (on `end_time`), `"Max 200 characters."`, `"Max 1000 characters."`, `"Max 50 characters."`; `roomCreateBody(form): RoomCreate` (trims text, empty optional text → omitted, numbers parsed); `roomChanges(form, room: RoomDetail): RoomUpdate` (only changed fields; empty optional text → `null`; `door_code` only when the box is non-empty).
  - `RoomFormPanel` props `{ room: RoomDetail | null }` (null = create), emits `saved(room: RoomDetail)`, `close`. Field groups and order follow the design page panel: Names (Khmer, then English, each with a mono `n/100` counter), Place (Office → Building → Floor, cascading, G08), Room (Room type, Seats, Size m² with unit suffix, Opening, Closing — `input type="time"`), About (Short description with `n/200`, Description textarea with `n/1000`), Access (Door code — `PasswordInput`; on edit the hint "Leave empty to keep the current code"; Owner select from `listRoomOwners` + "No owner"; Private switch "Only a label: shows the room as private"). Foot: quiet "Cancel", primary "Create room" / "Save changes" (busy: "Creating" / "Saving"); edit disables save until something changed. Drafts kept under `room:new` and `room:{id}` (DSH-A06). On success: toast "{name_en} saved" with detail `RM·0012 · Office › Building › Floor`, emit `saved`.

- [ ] **Step 1: Write failing tests** for `roomForm.ts`: `roomProblems` on `emptyRoomForm()` lists the name/place/type/seats problems; capacity `'0'`, `'10001'`, `'2.5'` → the seats message; `start_time '17:00'`, `end_time '08:00'` → `end_time: "Opening must be before closing."`; `start_time '24:00'` → the HH:MM message; `roomCreateBody` trims names and omits empty `short_desc`, `door_code`, `size_sqm`; `roomChanges(roomFormOf(room), room)` → `{}`; after setting `door_code = ''` it is still `{}`; after `door_code = '4821#'` → `{ door_code: '4821#' }`; clearing `short_desc` → `{ short_desc: null }`; changing the floor → `{ floor_id: <new> }` only.
- [ ] **Step 2: Write failing panel tests:** create submit with problems sends nothing and the summary lists the fields; a valid create POSTs exactly the `roomCreateBody` JSON and emits `saved`; a 409 `DUPLICATE` with `fields.name_en` shows that message under English name; changing the office clears building and floor and reloads buildings for the new office; the owner select shows "No owner" plus active room owners; editing with no change keeps "Save changes" disabled.
- [ ] **Step 3: Run** `npx vitest run src/utils/__tests__/roomForm.spec.ts src/views/__tests__/room-form.spec.ts`. Expected: FAIL.
- [ ] **Step 4: Implement** `roomForm.ts` and `RoomFormPanel.vue`.
- [ ] **Step 5: Run** again. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: create and edit a room in the side panel"`.

### Task 7: Room detail, turn off/on, door code

**Files:**
- Create: `admin_dashboard/src/views/rooms/RoomDetailPanel.vue`
- Modify: `admin_dashboard/src/views/RoomsView.vue` (open detail for `?room={id}`, form for `?room=new` and for `?room={id}&edit=1`)
- Test: `admin_dashboard/src/views/__tests__/room-detail.spec.ts`

**Interfaces:**
- Consumes: Tasks 1, 3, 4, 6.
- Produces: `RoomDetailPanel` props `{ roomId: number; step?: 'details' | 'photos' | 'equipment' }`, emits `edit`, `changed(room: RoomDetail)`, `close`. Head: room name (Khmer over English) + serial. Three tabs (`role="tablist"`): Details, Photos (n/20), Equipment (n). Details tab: every `RoomDetail` field — place path, type, seats, size, hours, owner, private, short description, description, created/updated (Phnom Penh time), `StateMarks`. Door code row: "Hidden" + secondary "Show door code" (Lucide `Eye`) → `getDoorCode` → mono code with a quiet "Hide"; `null` shows "No door code set". The code is dropped when the panel closes or the room changes. Foot: secondary "Edit" and, by state, danger "Turn off" or secondary "Turn on" with the inline confirm (DESIGN.md "Inline Confirm"): "Turn off {name_en}?" / "People can no longer book it. You can turn it on again." with quiet "Keep on" and danger "Turn off"; turning on needs no confirm. PATCH `{ is_active }`; an API error (e.g. its floor is off) shows the API message above the foot.

- [ ] **Step 1: Write failing tests:** the detail call shows the Khmer name, `RM·0012`, `08:00–17:00`, and the door code is not in the page text; "Show door code" calls `/rooms/12/door-code` and shows `4821#`, "Hide" removes it; `door_code: null` shows "No door code set"; "Turn off" asks first, then PATCHes `{"is_active":false}` and emits `changed`; "Turn on" on an inactive room PATCHes `{"is_active":true}`, and a 409 answer shows the API message and keeps the room inactive.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/room-detail.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the panel and the `RoomsView` wiring.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: room detail, turn off and on, door code on request"`.

### Task 8: Room photos

**Files:**
- Create: `admin_dashboard/src/views/rooms/RoomPhotos.vue`
- Modify: `admin_dashboard/src/views/rooms/RoomDetailPanel.vue` (Photos tab)
- Test: `admin_dashboard/src/views/__tests__/room-photos.spec.ts`

**Interfaces:**
- Consumes: Task 1 photo functions, `apiBaseUrl`.
- Produces: `RoomPhotos` props `{ roomId: number; photos: PhotoOut[] }`, emits `change(photos: PhotoOut[])`. A grid of thumbnails (`thumbnail_url`), 4:3, the first marked "Cover" (label, not a pill: small caption under it). Upload: a label-button "Add photos" (`accept="image/jpeg,image/png,image/webp"`, `multiple`), hint "JPEG, PNG or WebP, up to 5 MB each. The first photo is the cover." and a mono counter `n/20`; files upload one after another; at 20 the button is disabled with "20 photos is the limit". Reorder: drag a thumbnail (HTML5 drag and drop) and, for keyboard, each thumbnail has "Move earlier" / "Move later" icon buttons; after a move the new order is sent with `reorderRoomPhotos`; on failure the grid goes back to the order the server returned (or the previous order) and shows the API message. Delete: icon button "Delete photo" → inline confirm "Delete this photo?" → `deleteRoomPhoto`.

- [ ] **Step 1: Write failing tests:** three files where the second answers 415 → first and third appear, the error list shows "photo-2.gif: Wrong file type." and `change` was emitted with both new photos; at 20 photos "Add photos" is disabled; "Move later" on the first photo PUTs `{"photo_ids":[b,a,c]}` and the first thumbnail becomes the cover; a reorder answering 422 puts the grid back in the old order and shows the message; delete asks first, then DELETEs `/rooms/12/photos/{id}` and removes it.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/room-photos.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `RoomPhotos.vue` and the tab.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: room photos upload, reorder and delete"`.

### Task 9: Room equipment and the create flow

**Files:**
- Create: `admin_dashboard/src/views/rooms/RoomEquipment.vue`
- Modify: `admin_dashboard/src/views/rooms/RoomDetailPanel.vue` (Equipment tab), `admin_dashboard/src/views/RoomsView.vue` (after create: open the new room at the Photos step)
- Test: `admin_dashboard/src/views/__tests__/room-equipment.spec.ts`

**Interfaces:**
- Consumes: Task 1 (`listEquipment`, `setRoomEquipment`), Tasks 6–8.
- Produces: `RoomEquipment` props `{ roomId: number; equipment: EquipmentOut[] }`, emits `change(list: EquipmentOut[])`. A checklist of all active equipment (icon + name, `sort_order`), plus any inactive item the room already has, shown checked with "(off)" — it can be unchecked but an unchecked inactive item disappears and cannot be re-added (R15). "Save equipment" PUTs the checked ids; disabled until the set changed; toast "Equipment saved". API 409 `INACTIVE_REFERENCE` or 422 shows the API message.
- Create flow (DSH-R08): after `createRoom` succeeds, `RoomsView` replaces the form with the detail panel of the new room at the Photos tab, showing a quiet step line "Step 2 of 3 · Photos" with "Next: equipment" and then "Step 3 of 3 · Equipment" with "Done" (closes the panel). The list refreshes and the new row is marked with the saved tint (DESIGN.md "Saved Row": saved-tint fading to transparent over 2.4s ease-out).

- [ ] **Step 1: Write failing tests:** the list shows active equipment and the room's inactive item checked with "(off)"; unchecking it and saving PUTs ids without it; after saving it is no longer offered; "Save equipment" is disabled until something changed; a 409 shows its message; in `RoomsView`, a successful create opens `?room={newId}&step=photos`, "Next: equipment" moves to `step=equipment`, "Done" closes the panel and the list reloads.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/room-equipment.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `RoomEquipment.vue`, the tab and the create flow.
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: room equipment and the create-room steps"`.

### Task 10: End-to-end, design notes and verification

**Files:**
- Create: `admin_dashboard/e2e/rooms.spec.ts`
- Modify: `admin_dashboard/README.md` (Rooms section), `DESIGN.md` (note: tabs in the detail panel, photo grid, step line)

- [ ] **Step 1: Write the e2e test** (real API, skipped without `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD`): sign in → Rooms list shows a count → "New room" → fill Khmer and English names (unique with a timestamp), first office/building/floor/type, seats 8 → "Create room" → the panel shows "Step 2 of 3 · Photos" → upload `admin_dashboard/public/nbc-logo.png` → it appears as "Cover" → "Next: equipment" → tick the first item → "Save equipment" → "Done" → search the name → one row → open it → "Turn off" → confirm → the row shows "Inactive".
- [ ] **Step 2: Add a mocked layout e2e** in `e2e/shell-layout.spec.ts` style: the Rooms list at 1366px, 900px and 390px has no horizontal scroll on the page and the paging foot is visible.
- [ ] **Step 3: Full verification** in `admin_dashboard/`: `npm run lint`, `npm run type-check`, `npx vitest run`, `npm run build`, `npx playwright test`. Expected: all pass (the real-API test may be skipped without credentials). In the repo root: `.venv/Scripts/python -m pytest -q` still passes (no API changes).
- [ ] **Step 4: Commit** `git commit -m "Dashboard: phase 2 end-to-end checks and notes"`.
