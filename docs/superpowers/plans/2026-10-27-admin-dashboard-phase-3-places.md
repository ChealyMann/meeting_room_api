# Admin Dashboard Phase 3 (Places) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Places pages: Offices, Buildings and Floors — each a filtered, paged list with create, edit, move (building to another office, floor to another building) and turn off/on, warning before a turn-off how many rooms stop being bookable.

**Architecture:** Builds on Phases 1–2 (`api` client, `useListQuery`, list parts, `SidePanel`, `useConfirm`, `useFieldErrors`, `useToast`, drafts store, `selectOptions`, `serial`). Three pages share one small list engine (`useResourceList`: load with a latest-answer guard, error, past-the-end page) and one address helper for the open panel (`usePanelParam`: `?id=12`, `?id=new`). Each page is a list view plus one form panel; turning off/on lives in the panel foot through a shared `ActiveToggle` that asks in the confirm dialog.

**Tech Stack:** Vue 3 (`<script setup lang="ts">`), TypeScript, Vue Router, Pinia, Tailwind CSS v4 tokens + scoped CSS, `lucide-vue-next`, Vitest + `@vue/test-utils` + jsdom, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (DSH-P01 to DSH-P05 in section 10, DSH-G01 to DSH-G10 in section 9). API contract: `spec.md` section 12 (locations, buildings, floors) and rules R1–R4; the live `/openapi.json`. Visual source: the Rooms pages built in Phase 2 and `DESIGN.md`.

## Global Constraints

- Work on a new branch `feature/dashboard-phase-3` from the tip of `feature/dashboard-phase-2`. Commit messages carry no AI attribution lines.
- API types only from `src/api/schema.d.ts` (`LocationOut`, `LocationCreate`, `LocationUpdate`, `BuildingOut`, `BuildingDetail`, `BuildingCreate`, `BuildingUpdate`, `FloorOut`, `FloorDetail`, `FloorCreate`, `FloorUpdate`, `ProvinceRef`).
- Every rule of Phase 2 applies: G01 paging (20 / 50 / 100, total shown), G02 filters in the address (defaults left out), G03 side panel + PATCH only changed fields, G04/G05 API messages under fields and at the top, G06 client checks with the API limits, G07 turn off/on confirmed in the app's confirm dialog (owner decision, never a browser pop-up), G08 parent selects hide inactive items except the chosen one, G09 toast + list refresh after save, G10 empty states and skeleton rows.
- API limits (G06): office `name_en`/`name_kh` 1–100, `province` required (a code from `GET /provinces`), `address` ≤ 200, `map_query` ≤ 500, `description` ≤ 1000; building `name_en`/`name_kh` 1–100, `short_name` ≤ 20, `sort_order` a whole number ≥ 0; floor `floor_label` 1–100, `sort_order` a whole number ≥ 0.
- R3: turning off never cascades; turning on a building under an inactive office, or a floor under an inactive building, is refused with 409 `INACTIVE_REFERENCE` — show the API message, the record stays off.
- R4: names are unique — office `name_en`; building `name_en` per office; floor `floor_label` per building — 409 `DUPLICATE` shows under that field.
- Serials: offices `OF·0003`, buildings `BL·0005`, floors `FL·0007` (crimson prefix, middle dot, 4 digits).
- Names: Khmer over English for offices and buildings (owner decision); floors have one label.
- Day and night themes: colour tokens only.
- English UI, no emoji, Lucide icons at stroke 1.75.

## Review Focus

- Turning off an office whose room count cannot be loaded (the rooms call fails) → the confirm still opens with the general warning ("Its rooms become not bookable."), never a blocked button or a crash (test in Task 3).
- Turning on a building whose office is off → 409 `INACTIVE_REFERENCE`; the API message shows in the panel and the building stays "Inactive" in the panel and the list (test in Task 5).
- Moving a building to another office that already has a building with the same English name → 409 `DUPLICATE` with `fields.name_en`; the message shows under English name and nothing else changes (test in Task 5).
- Floors list at `?location_id=3&building_id=99` where building 99 is gone → the list still loads and the Building select shows "Unknown building"; changing the office clears the building (test in Task 6).
- An office address with a province code that is not in the province list (`?province=XX`) → the list still loads; the Province select shows "Unknown province" (test in Task 4).

---

### Task 1: Places API functions

**Files:**
- Modify: `admin_dashboard/src/api/types.ts`
- Create: `admin_dashboard/src/api/places.ts`
- Test: `admin_dashboard/src/api/__tests__/places.spec.ts`

**Interfaces:**
- Consumes: `ApiClient`, `toQuery`, `Page<T>`, `listRooms` (Phase 2).
- Produces:
  - `types.ts` adds: `LocationCreate`, `LocationUpdate`, `BuildingDetail`, `BuildingCreate`, `BuildingUpdate`, `FloorDetail`, `FloorCreate`, `FloorUpdate`.
  - `places.ts`:
    - `OfficeFilters = { province?: string; is_active?: boolean; search?: string; page?: number; size?: number }`; `listOfficePage(client, f): Promise<Page<LocationOut>>` (GET `/api/v1/locations`), `getOffice(client, id): Promise<LocationOut>`, `createOffice(client, body: LocationCreate): Promise<LocationOut>`, `updateOffice(client, id, changes: LocationUpdate): Promise<LocationOut>`.
    - `BuildingFilters = { location_id?: number; is_active?: boolean; search?: string; page?: number; size?: number }`; `listBuildingPage`, `getBuilding(client, id): Promise<BuildingDetail>`, `createBuilding(client, body: BuildingCreate): Promise<BuildingDetail>`, `updateBuilding(client, id, changes: BuildingUpdate): Promise<BuildingDetail>` (`/api/v1/buildings`).
    - `FloorFilters = { location_id?: number; building_id?: number; is_active?: boolean; search?: string; page?: number; size?: number }`; `listFloorPage`, `getFloor(client, id): Promise<FloorDetail>`, `createFloor`, `updateFloor` (`/api/v1/floors`).
    - `countActiveRooms(client, where: { location_id?: number; building_id?: number; floor_id?: number }): Promise<number>` — `listRooms(client, { ...where, is_active: true, page: 1, size: 1 })` and returns `total`.

- [ ] **Step 1: Write failing tests** (fake `fetchImpl`): `listOfficePage(client, { province: 'PP', is_active: true, page: 2, size: 50 })` calls `GET …/api/v1/locations?province=PP&is_active=true&page=2&size=50`; `createOffice` POSTs exactly the body; `updateBuilding(client, 5, { location_id: 4 })` PATCHes `/api/v1/buildings/5` with `{"location_id":4}`; `listFloorPage(client, { location_id: 3, building_id: 5 })` calls `/api/v1/floors?location_id=3&building_id=5`; `countActiveRooms(client, { building_id: 5 })` calls `/api/v1/rooms?building_id=5&is_active=true&page=1&size=1` and returns the answer's `total` (e.g. 12).
- [ ] **Step 2: Run** `npx vitest run src/api/__tests__/places.spec.ts`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** `places.ts` and the type aliases.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: offices, buildings and floors API functions"`.

### Task 2: Shared list engine and panel address

**Files:**
- Create: `admin_dashboard/src/composables/useResourceList.ts`, `admin_dashboard/src/composables/usePanelParam.ts`
- Test: `admin_dashboard/src/composables/__tests__/useResourceList.spec.ts`, `admin_dashboard/src/composables/__tests__/usePanelParam.spec.ts`

**Interfaces:**
- Consumes: `useListQuery`, `Page<T>`, `ApiError`.
- Produces:
  - `useResourceList<T>(spec: FilterSpec, fetchPage: (params: Record<string, unknown>) => Promise<Page<T>>)` returns `{ list /* the useListQuery result */, result: Ref<Page<T> | null>, loading: Ref<boolean>, error: Ref<string>, filtered: ComputedRef<boolean>, savedId: Ref<number | null>, load(): Promise<void>, refresh(id?: number): Promise<void> }`. Loads whenever `list.apiParams` changes; only the newest answer counts; an empty page past the end moves to the last page (same as Phase 2 RoomsView); `filtered` is true when any filter is set or the status is not `active`; `refresh(id)` reloads and sets `savedId` (the row tint).
  - `usePanelParam(key = 'id')` returns `{ param: ComputedRef<string | undefined>, id: ComputedRef<number | null>, isNew: ComputedRef<boolean>, open(id: number | 'new'): void, close(): void }` — `open` pushes `?{key}=…` keeping the other address keys; `close` removes the key (push, so Back reopens).

- [ ] **Step 1: Write failing tests:** `useResourceList` calls `fetchPage` with `{ is_active: true, page: 1, size: 20 }` at `/`; an older answer that arrives after a newer one is ignored; a failed fetch sets `error` to the API message and `load()` again clears it; an empty page 3 with `total: 40` moves the address to `page=2`; `refresh(7)` reloads and sets `savedId` 7. `usePanelParam`: at `/?search=a`, `open(12)` gives `?search=a&id=12`, `id.value === 12`; `open('new')` gives `isNew === true`; `close()` leaves `?search=a`; `?id=abc` gives `id === null` and `isNew === false`.
- [ ] **Step 2: Run** `npx vitest run src/composables/__tests__/useResourceList.spec.ts src/composables/__tests__/usePanelParam.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** both composables.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: shared list engine and panel address"`.

### Task 3: Turn off / turn on with the rooms warning

**Files:**
- Create: `admin_dashboard/src/components/list/ActiveToggle.vue`
- Test: `admin_dashboard/src/components/list/__tests__/active-toggle.spec.ts`

**Interfaces:**
- Consumes: `useConfirm`, `countActiveRooms`.
- Produces: `ActiveToggle` props `{ active: boolean; name: string; kind: 'office' | 'building' | 'floor'; rooms: { location_id?: number; building_id?: number; floor_id?: number }; turn: (active: boolean) => Promise<void> }` (the page's PATCH; it throws `ApiError` on refusal). Renders, by state, danger "Turn off" (Lucide `Power`) or secondary "Turn on". Turn off: counts active rooms, then asks in the confirm dialog — title `Turn off {name}?`, text `{n} room(s) in this {kind} stop being bookable. You can turn it on again.` (`1 room`, `No rooms are affected.` for 0), and if the count fails `Its rooms stop being bookable. You can turn it on again.`; confirm label "Turn off", icon `power` (DSH-P05). Turn on: no confirm. Busy while working. On an API error shows the message in a `.summary` `role="alert"` right above itself; emits nothing (the page reloads its record after `turn` succeeds).

- [ ] **Step 1: Write failing tests:** with 12 active rooms, clicking "Turn off" opens the dialog "Turn off Head Office?" with "12 rooms in this office stop being bookable." and confirming calls `turn(false)` once; cancelling calls nothing; with 1 room the text says "1 room"; with 0 "No rooms are affected."; when the rooms call fails the dialog still opens with "Its rooms stop being bookable."; for an inactive record "Turn on" calls `turn(true)` with no dialog, and a `turn` that throws `ApiError(409, 'INACTIVE_REFERENCE', 'Turn on its office first.')` shows that message.
- [ ] **Step 2: Run** `npx vitest run src/components/list/__tests__/active-toggle.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `ActiveToggle.vue`.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: turn off and on with the rooms warning"`.

### Task 4: Offices page

**Files:**
- Create: `admin_dashboard/src/views/OfficesView.vue`, `admin_dashboard/src/views/places/OfficeFormPanel.vue`, `admin_dashboard/src/utils/placeForms.ts` (office part)
- Modify: `admin_dashboard/src/router/index.ts` (route `offices` at `/offices`, title "Offices", child of `shell`), `admin_dashboard/src/layouts/nav.ts` (Offices → route `offices`)
- Test: `admin_dashboard/src/utils/__tests__/placeForms.spec.ts`, `admin_dashboard/src/views/__tests__/offices.spec.ts`

**Interfaces:**
- Consumes: Tasks 1–3; `listProvinces`, `selectOptions`, list parts, `SidePanel`, `BaseField`, `FormErrorSummary`, `useFieldErrors`, `useToast`, drafts store.
- Produces:
  - `placeForms.ts` (office part): `type OfficeForm = { name_kh: string; name_en: string; province: string; address: string; map_query: string; description: string }`; `emptyOfficeForm()`, `officeFormOf(o: LocationOut)`, `officeProblems(f): Record<string, string>` (`"Enter the Khmer name."`, `"Enter the English name."`, `"Max 100 characters."`, `"Choose a province."`, `"Max 200 characters."`, `"Max 500 characters."`, `"Max 1000 characters."`), `officeCreateBody(f): LocationCreate` (trimmed; empty optional text left out), `officeChanges(f, o): LocationUpdate` (only changed; cleared optional text → `null`).
  - `OfficesView` (route `offices`): headline "Offices" + mono count (`004 offices`) + primary "New office"; filters: search ("Search name or address"), Province select (with "Unknown province" for a code not in the list), `StatusFilter`; table: Serial `OF·0003`, Office (Khmer over English), Province, Address (one line, ellipsis; "None" in off tone), State (`StateMarks` active only). Row click opens `?id=3`. Empty states: "No offices yet" / "Add the first office." and "No offices match" with "Clear filters". `PagingFoot`.
  - `OfficeFormPanel` props `{ office: LocationOut | null }`, emits `saved(o)`, `close`. Fields: Khmer name, English name (`n/100` counters), Province select (required), Address (`n/200`), Map text (`n/500`, hint "What to search on a map, e.g. National Bank of Cambodia, Phnom Penh"), Description textarea (`n/1000`). Foot: `ActiveToggle` (edit only, `kind: 'office'`, `rooms: { location_id }`), quiet "Cancel", primary "Create office" / "Save changes". Drafts `office:new` / `office:{id}` with `updatedAt`, cleared on Cancel/close (Phase 2 rule). Toast "{name_en} saved" with detail `OF·0003`.

- [ ] **Step 1: Write failing tests** for `placeForms` (office): empty form → the name and province problems; `address` of 201 characters → "Max 200 characters."; `officeCreateBody` trims and leaves out empty `address`, `map_query`, `description`; `officeChanges(officeFormOf(o), o)` → `{}`; clearing the address → `{ address: null }`.
- [ ] **Step 2: Write failing view tests:** at `/offices?province=PP&search=head` the call is `/api/v1/locations?province=PP&search=head&is_active=true&page=1&size=20`; rows show `OF·0003`, Khmer over English, the province name; `?province=XX` loads and the select shows "Unknown province"; "New office" opens `?id=new` and the panel; a valid create POSTs the body and the list reloads with the toast; a 409 `DUPLICATE` with `fields.name_en` shows under English name; editing with no change keeps "Save changes" disabled; the nav "Offices" link is a real link with `aria-current="page"` on this page.
- [ ] **Step 3: Run** `npx vitest run src/utils/__tests__/placeForms.spec.ts src/views/__tests__/offices.spec.ts`. Expected: FAIL.
- [ ] **Step 4: Implement** the form helpers, view, panel, route and nav link.
- [ ] **Step 5: Run** again, then `npx vitest run`. Expected: PASS (update the Phase 1 shell test that expected "Offices" to be disabled).
- [ ] **Step 6: Commit** `git commit -m "Dashboard: offices list, create, edit, turn off and on"`.

### Task 5: Buildings page

**Files:**
- Create: `admin_dashboard/src/views/BuildingsView.vue`, `admin_dashboard/src/views/places/BuildingFormPanel.vue`
- Modify: `admin_dashboard/src/utils/placeForms.ts` (building part), `admin_dashboard/src/router/index.ts` (route `buildings`), `admin_dashboard/src/layouts/nav.ts`
- Test: `admin_dashboard/src/utils/__tests__/placeForms.spec.ts` (building part), `admin_dashboard/src/views/__tests__/buildings.spec.ts`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces:
  - `placeForms.ts` (building part): `type BuildingForm = { location_id: number | null; name_kh: string; name_en: string; short_name: string; sort_order: string }`; `emptyBuildingForm(locationId?: number | null)` (sort order `''`), `buildingFormOf(b: BuildingDetail)`, `buildingProblems(f)` (`"Choose an office."`, the name messages, `"Max 20 characters."`, `"Order must be a whole number from 0."`), `buildingCreateBody(f): BuildingCreate` (empty `short_name` and `sort_order` left out), `buildingChanges(f, b): BuildingUpdate` (a new `location_id` = move; cleared `short_name` → `null`).
  - `BuildingsView` (route `buildings`): "Buildings" + count + "New building" (pre-fills the office filter's office); filters: search, Office select (G08, "Unknown office"), `StatusFilter`; table: Serial `BL·0005`, Building (Khmer over English, short name in mono after the English name when set), Office, Order (mono, right), State. Row → `?id=5`.
  - `BuildingFormPanel` props `{ building: BuildingDetail | null; defaultOfficeId?: number | null }`. Fields: Office select (create: "Office"; edit: label "Office" with hint "Change to move the building"), Khmer name, English name, Short name (`n/20`, hint "optional, e.g. A"), Order (number, hint "Lower comes first"). `ActiveToggle` `kind: 'building'`, `rooms: { building_id }`. Toast detail `BL·0005 · {office}`.

- [ ] **Step 1: Write failing tests** for the building helpers: problems for an empty form; `short_name` of 21 → "Max 20 characters."; `sort_order '-1'` / `'1.5'` → the order message; moving: `buildingChanges({ ...buildingFormOf(b), location_id: 4 }, b)` → `{ location_id: 4 }`.
- [ ] **Step 2: Write failing view tests:** `/buildings?location_id=3` calls `/api/v1/buildings?location_id=3&is_active=true&page=1&size=20`; rows show `BL·0005`, Khmer over English, the office name; "New building" opens the panel with Office pre-set to 3; moving to an office that already has that name: PATCH answers 409 `DUPLICATE` with `fields.name_en` → the message shows under English name and the building is not changed in the list; turning on a building whose office is off: PATCH answers 409 `INACTIVE_REFERENCE` → the panel shows the message and the list row still says "Inactive".
- [ ] **Step 3: Run** `npx vitest run src/utils/__tests__/placeForms.spec.ts src/views/__tests__/buildings.spec.ts`. Expected: FAIL.
- [ ] **Step 4: Implement.**
- [ ] **Step 5: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: buildings list, create, edit, move, turn off and on"`.

### Task 6: Floors page

**Files:**
- Create: `admin_dashboard/src/views/FloorsView.vue`, `admin_dashboard/src/views/places/FloorFormPanel.vue`
- Modify: `admin_dashboard/src/utils/placeForms.ts` (floor part), `admin_dashboard/src/router/index.ts` (route `floors`), `admin_dashboard/src/layouts/nav.ts`
- Test: `admin_dashboard/src/utils/__tests__/placeForms.spec.ts` (floor part), `admin_dashboard/src/views/__tests__/floors.spec.ts`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces:
  - `placeForms.ts` (floor part): `type FloorForm = { location_id: number | null; building_id: number | null; floor_label: string; sort_order: string }`; `emptyFloorForm(locationId?, buildingId?)`, `floorFormOf(f: FloorDetail)`, `floorProblems(f)` (`"Choose an office."`, `"Choose a building."`, `"Enter the floor name."`, `"Max 100 characters."`, the order message), `floorCreateBody(f): FloorCreate`, `floorChanges(f, floor): FloorUpdate` (a new `building_id` = move; office alone is not sent).
  - `FloorsView` (route `floors`): "Floors" + count + "New floor" (pre-fills office and building from the filters); filters: search ("Search floor name"), Office → Building cascade (choosing an office clears the building; answers out of order are ignored, as in Phase 2), `StatusFilter`; table: Serial `FL·0007`, Floor (label), Building, Office, Order, State. Row → `?id=7`.
  - `FloorFormPanel` props `{ floor: FloorDetail | null; defaultOfficeId?: number | null; defaultBuildingId?: number | null }`. Fields: Office → Building cascade (edit hint "Change to move the floor"), Floor name (`n/100`, placeholder "e.g. 3rd floor"), Order. `ActiveToggle` `kind: 'floor'`, `rooms: { floor_id }`.

- [ ] **Step 1: Write failing tests** for the floor helpers: problems for an empty form; changing only the office does not appear in `floorChanges`; changing the building → `{ building_id: <new> }`.
- [ ] **Step 2: Write failing view tests:** `/floors?location_id=3&building_id=5` calls `/api/v1/floors?location_id=3&building_id=5&is_active=true&page=1&size=20`; rows show `FL·0007`, the building and office names; `?location_id=3&building_id=99` loads and the Building select shows "Unknown building"; choosing another office clears `building_id` from the address; "New floor" pre-sets office 3 and building 5; a create POSTs `{building_id, floor_label, …}` without `location_id`.
- [ ] **Step 3: Run** `npx vitest run src/utils/__tests__/placeForms.spec.ts src/views/__tests__/floors.spec.ts`. Expected: FAIL.
- [ ] **Step 4: Implement.**
- [ ] **Step 5: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: floors list, create, edit, move, turn off and on"`.

### Task 7: End-to-end, notes and verification

**Files:**
- Create: `admin_dashboard/e2e/places.spec.ts`, `admin_dashboard/e2e/places-layout.spec.ts`
- Modify: `admin_dashboard/README.md` (Places section), `DESIGN.md` (serial prefixes OF/BL/FL; the turn-off warning text)

- [ ] **Step 1: Write the real-API e2e** (skipped without `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD`): sign in → Offices → "New office" with unique names and the first province → it appears in the list → Buildings → "New building" in that office → Floors → "New floor" in that building → open the office → "Turn off" → the dialog says "No rooms are affected." → confirm → "Inactive" → "Turn on".
- [ ] **Step 2: Write the mocked layout e2e:** Offices, Buildings and Floors at 1366px, 900px and 390px have no sideways page scroll and the paging foot is visible.
- [ ] **Step 3: Full verification** in `admin_dashboard/`: `npm run lint`, `npm run type-check`, `npx vitest run`, `npm run build`, `npx playwright test`. Expected: all pass (real-API tests may be skipped). In the repo root `.venv/Scripts/python -m pytest -q` still passes.
- [ ] **Step 4: Commit** `git commit -m "Dashboard: phase 3 end-to-end checks and notes"`.
