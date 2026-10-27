# Admin Dashboard Phase 4 (Catalog) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Catalog pages: Room types and Equipment — each a searchable, paged list with create, edit, sort order and turn off/on; equipment gets an icon picker with a preview.

**Architecture:** Same shape as the Phase 3 place pages, reusing their parts: `useResourceList` (list), `usePanelParam` (`?id=3`, `?id=new`), `usePanelRecord` (a record loads before its panel opens), `ListSearch`, `StatusFilter`, `PagingFoot`, `StateMarks`, `ActiveToggle` (blocked while the form has unsaved changes), `SidePanel` + `panelMotion`, drafts, `serial`. Each page is one list view plus one form panel. The icon picker is a small component over a fixed list of Lucide icons.

**Tech Stack:** Vue 3 (`<script setup lang="ts">`), TypeScript, Vue Router, Pinia, scoped CSS on the Tailwind v4 tokens, `lucide-vue-next` 1.0.0, Vitest + `@vue/test-utils` + jsdom, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (DSH-C01, DSH-C02 in section 10; DSH-G01 to DSH-G10 in section 9). API: `app/routers/categories.py`, `app/routers/equipment.py`, `app/schemas/category.py`, `app/schemas/equipment.py`. Visual source: the Phase 3 pages and `DESIGN.md`.

## Global Constraints

- Branch `feature/dashboard-phase-4` from `main` (already created). Commit messages carry no AI attribution lines.
- API types only from `src/api/schema.d.ts`: `CategoryOut`, `CategoryCreate`, `CategoryUpdate`, `EquipmentOut`, `EquipmentCreate`, `EquipmentUpdate`.
- Every Phase 2–3 rule applies: G01 paging (20 / 50 / 100), G02 filters in the address, G03 side panel + PATCH only changed fields, G04/G05 API messages under fields and at the top, G06 client checks with the API limits, G07 turn off confirmed in the app's confirm dialog, G09 toast + list refresh after save, G10 empty states and skeleton rows. A saved record loads before its panel opens (owner decision, 27 Oct 2026).
- API limits (G06): room type `name_en` and `name_kh` 1–100 characters after trimming; equipment `name` 1–200; equipment `icon` optional, ≤ 1000; `sort_order` a whole number 0–9999 (both).
- The API filters both lists by `is_active` and `search` only (search: room type English and Khmer names; equipment name). Both sort by order, then name.
- Unique: room type `name_en`, equipment `name` → 409 `DUPLICATE` with the message under that field.
- Turning a room type or an item off does not change whether rooms are bookable: rooms keep it, but it cannot be chosen for other rooms (API docstring of `update_category`; `room_equipment` refuses an inactive item with 409 `INACTIVE_REFERENCE`).
- Serials: room types `RT·0002`, equipment `EQ·0004`.
- Names: room types show Khmer over English (owner decision); equipment has one name (the API has no Khmer name).
- Day and night themes: colour tokens only. English UI, no emoji, Lucide icons at stroke 1.75.

## Review Focus

- An item whose `icon` is not in the picker's list (set by the mobile app, old data, or a URL) → the form shows a neutral "Unknown icon" preview with the stored text, keeps it unless the admin picks another or clears it, and an edit of other fields does not send `icon` (test in Task 3).
- Order `10000` or `-1` typed → "Order must be a whole number from 0 to 9999." before sending, for every page that has an order, the place pages included (test in Task 1).
- Turning off when the room count cannot be read → the confirm still opens with the general text for that kind (test in Task 1).
- Icon search with no match → "No icons match." and the current choice stays (test in Task 3).
- Clearing the icon of an item that had one → PATCH sends `{"icon": null}` (test in Task 3).

---

### Task 1: Shared parts — order check, catalog API, turn-off texts, list page styles

**Files:**
- Create: `admin_dashboard/src/utils/sortOrder.ts`, `admin_dashboard/src/api/catalog.ts`
- Move: `admin_dashboard/src/views/places/placePage.css` → `admin_dashboard/src/views/listPage.css` (update the three `<style scoped src>` paths in `OfficesView.vue`, `BuildingsView.vue`, `FloorsView.vue`)
- Modify: `admin_dashboard/src/utils/placeForms.ts` (use `sortOrder.ts`), `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/api/places.ts` (`countActiveRooms` filter type), `admin_dashboard/src/components/list/ActiveToggle.vue`
- Test: `admin_dashboard/src/utils/__tests__/sortOrder.spec.ts`, `admin_dashboard/src/api/__tests__/catalog.spec.ts`, `admin_dashboard/src/components/list/__tests__/active-toggle.spec.ts`, `admin_dashboard/src/utils/__tests__/placeForms.spec.ts` (message text)

**Interfaces:**
- Consumes: `listRooms(client, RoomFilters)` (`category_id`, `equipment_ids` already supported), `toQuery`.
- Produces:
  - `sortOrder.ts`: `orderProblem(text: string): string | null` → `null` for empty or a whole number 0–9999, else `"Order must be a whole number from 0 to 9999."`; `orderValue(text: string): number` (empty → 0).
  - `types.ts`: `CategoryCreate`, `CategoryUpdate`, `EquipmentCreate`, `EquipmentUpdate` (`CategoryOut`, `EquipmentOut` exist).
  - `catalog.ts`: `interface CatalogFilters { is_active?: boolean; search?: string; page?: number; size?: number }`; `listRoomTypePage(client, f): Promise<Page<CategoryOut>>`, `getRoomType(client, id)`, `createRoomType(client, body: CategoryCreate)`, `updateRoomType(client, id, changes: CategoryUpdate)` on `/api/v1/categories`; `listEquipmentPage`, `getEquipment`, `createEquipment(client, body: EquipmentCreate)`, `updateEquipment(client, id, changes: EquipmentUpdate)` on `/api/v1/equipment`.
  - `places.ts`: `export type RoomCount = { location_id?: number; building_id?: number; floor_id?: number; category_id?: number; equipment_ids?: number[] }`; `countActiveRooms(client, where: RoomCount)`.
  - `ActiveToggle`: `kind` widens to `'office' | 'building' | 'floor' | 'room type' | 'equipment'`; `rooms: RoomCount`. Texts for the new kinds (n = count, null = count failed):

| kind | null | 0 | 1 | n |
| --- | --- | --- | --- | --- |
| room type | Rooms that use it keep it, but it cannot be chosen for other rooms. You can turn it on again. | No rooms use it. You can turn it on again. | 1 room uses this room type and keeps it. It cannot be chosen for other rooms. You can turn it on again. | 12 rooms use this room type and keep it. It cannot be chosen for other rooms. You can turn it on again. |
| equipment | Rooms that have it keep it, but it cannot be added to other rooms. You can turn it on again. | No rooms have it. You can turn it on again. | 1 room has this item and keeps it. It cannot be added to other rooms. You can turn it on again. | 12 rooms have this item and keep it. It cannot be added to other rooms. You can turn it on again. |

- [ ] **Step 1: Write failing tests.**
  - `sortOrder.spec.ts`: `orderProblem('')`, `'0'`, `'9999'` → `null`; `'10000'`, `'-1'`, `'1.5'`, `'a'` → the message; `orderValue('')` → 0, `orderValue(' 12 ')` → 12.
  - `placeForms.spec.ts`: change the expected order message to `'Order must be a whole number from 0 to 9999.'` and add `sort_order: '10000'` → that message for buildings.
  - `catalog.spec.ts` (same style as `places.spec.ts`): `listRoomTypePage(api, { search: 'board', is_active: true, page: 2, size: 50 })` calls `/api/v1/categories?search=board&is_active=true&page=2&size=50`; `updateEquipment(api, 4, { icon: null })` sends `PATCH /api/v1/equipment/4` with body `{"icon":null}`.
  - `active-toggle.spec.ts`: kind `'room type'`, rooms `{ category_id: 2 }` → calls `/api/v1/rooms?category_id=2&is_active=true&page=1&size=1` and, for 12, the dialog says "12 rooms use this room type and keep it."; kind `'equipment'`, rooms `{ equipment_ids: [4] }`, count fails → "Rooms that have it keep it, but it cannot be added to other rooms."; kind `'equipment'`, 1 → "1 room has this item and keeps it."
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/sortOrder.spec.ts src/utils/__tests__/placeForms.spec.ts src/api/__tests__/catalog.spec.ts src/components/list/__tests__/active-toggle.spec.ts`. Expected: FAIL (missing modules, old message, missing texts).
- [ ] **Step 3: Implement** the files above; `placeForms` uses `orderProblem`/`orderValue` instead of its own; move the CSS file and fix its three paths.
- [ ] **Step 4: Run** the same command, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: catalog API functions, shared order check, turn-off texts for catalog"`.

### Task 2: Room types page

**Files:**
- Create: `admin_dashboard/src/utils/catalogForms.ts` (room type part), `admin_dashboard/src/views/RoomTypesView.vue`, `admin_dashboard/src/views/catalog/RoomTypeFormPanel.vue`
- Modify: `admin_dashboard/src/router/index.ts` (child of `shell`: path `room-types`, name `room-types`, title "Room types"), `admin_dashboard/src/layouts/nav.ts` (Room types → `room-types`), `admin_dashboard/src/layouts/__tests__/shell.spec.ts` (its router gets the route; the "not yet built" test uses "Departments")
- Test: `admin_dashboard/src/utils/__tests__/catalogForms.spec.ts`, `admin_dashboard/src/views/__tests__/room-types.spec.ts`

**Interfaces:**
- Consumes: Task 1; `useResourceList`, `usePanelParam`, `usePanelRecord`, `ListSearch`, `StatusFilter`, `PagingFoot`, `StateMarks`, `EmptyState`, `TableSkeleton`, `ActiveToggle` (`blocked` while dirty), `SidePanel`, `BaseField`, `FormErrorSummary`, `useFieldErrors`, `useToast`, drafts store, `serial`, `listPage.css`.
- Produces:
  - `catalogForms.ts`: `type RoomTypeForm = { name_kh: string; name_en: string; sort_order: string }`; `emptyRoomTypeForm()`, `roomTypeFormOf(c: CategoryOut)`, `roomTypeProblems(f)` (`"Enter the Khmer name."`, `"Enter the English name."`, `"Max 100 characters."`, the order message), `roomTypeCreateBody(f): CategoryCreate` (trimmed; empty order → 0), `roomTypeChanges(f, c): CategoryUpdate` (only changed).
  - `RoomTypesView` (route `room-types`): "Room types" + mono count (`004 room types`) + primary "New room type"; filters: search ("Search Khmer or English name") and `StatusFilter`; table: Serial `RT·0002`, Room type (Khmer over English), Order (mono, right), State. Row → `?id=2` (opens after the record loads; busy row as on the place pages). Empty: "No room types yet" / "Add the first room type." and "No room types match" with "Clear filters".
  - `RoomTypeFormPanel` props `{ roomType: CategoryOut | null }`, emits `saved`, `close`. Groups: "Names" (Khmer name, English name, `n/100`), "Order" (Order, hint "Lower comes first", placeholder `0`). Foot: `ActiveToggle` (edit only, kind `'room type'`, rooms `{ category_id }`), "Cancel", "Create room type" / "Save changes". Drafts `room-type:new` / `room-type:{id}`. Toast "{name_en} saved", detail `RT·0002`.

- [ ] **Step 1: Write failing tests** for the room type helpers: empty form → the two name problems; `name_en` of 101 → "Max 100 characters."; `roomTypeCreateBody` trims and sends `sort_order: 0` for an empty order; `roomTypeChanges(roomTypeFormOf(c), c)` → `{}`; order `'3'` on a type with order 1 → `{ sort_order: 3 }`.
- [ ] **Step 2: Write failing view tests:** `/room-types?search=board` calls `/api/v1/categories?search=board&is_active=true&page=1&size=20`; a row shows `RT·0002` and Khmer over English; `.count` says `002 room types`; "New room type" opens `?id=new` and a valid create POSTs `{"name_kh":…,"name_en":…,"sort_order":0}` with the toast; a 409 `DUPLICATE` with `fields.name_en` shows under English name; `?id=2` with no change keeps "Save changes" disabled and shows "Turn off"; the nav item "Room types" has route `room-types`.
- [ ] **Step 3: Run** `npx vitest run src/utils/__tests__/catalogForms.spec.ts src/views/__tests__/room-types.spec.ts`. Expected: FAIL.
- [ ] **Step 4: Implement** the helpers, view, panel, route and nav link (copy the Offices page structure).
- [ ] **Step 5: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: room types list, create, edit, turn off and on"`.

### Task 3: Equipment page with the icon picker

**Files:**
- Create: `admin_dashboard/src/utils/equipmentIcons.ts`, `admin_dashboard/src/components/IconPicker.vue`, `admin_dashboard/src/views/EquipmentView.vue`, `admin_dashboard/src/views/catalog/EquipmentFormPanel.vue`
- Modify: `admin_dashboard/src/utils/catalogForms.ts` (equipment part), router (`equipment` at `/equipment`, title "Equipment"), `nav.ts`, `shell.spec.ts` router
- Test: `admin_dashboard/src/utils/__tests__/equipmentIcons.spec.ts`, `admin_dashboard/src/components/__tests__/icon-picker.spec.ts`, `admin_dashboard/src/utils/__tests__/catalogForms.spec.ts` (equipment part), `admin_dashboard/src/views/__tests__/equipment.spec.ts`

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces:
  - `equipmentIcons.ts`: `EQUIPMENT_ICONS: ReadonlyArray<{ name: string; label: string; icon: Component }>` — the Lucide kebab-case name (what the API stores), a short English label for search, and the named import. Exactly these 50, in this order (all exist in lucide-vue-next 1.0.0): projector, presentation, monitor, tv, tv-minimal, airplay, cast, video, webcam, camera, mic, speaker, volume-2, headphones, phone, laptop, keyboard, mouse, printer, cable, plug, usb, wifi, router, battery-charging, lamp, lightbulb, air-vent, fan, snowflake, thermometer, armchair, sofa, coffee, cup-soda, utensils, droplets, clipboard, pen-line, notebook-pen, square-pen, accessibility, lock, key-round, package, clock, calendar, radio, gamepad-2, flip-horizontal. `iconFor(name: string | null): Component | null` → the component, or `null` when not in the list.
  - `IconPicker.vue`: `v-model: string | null`, prop `id: string`. Shows a preview row (the chosen icon at 32px in a 56px square, its name in mono, or "No icon", or a `CircleHelp` icon with "Unknown icon" and the stored text), a search box ("Search icons", filters by name and label), a grid of icon buttons (`role="radiogroup"`, each `role="radio"` with `aria-checked` and `aria-label` = label), and a "No icon" button. No match → "No icons match." Arrow keys move between icons.
  - `catalogForms.ts` (equipment): `type EquipmentForm = { name: string; icon: string | null; sort_order: string }`; `emptyEquipmentForm()`, `equipmentFormOf(e: EquipmentOut)`, `equipmentProblems(f)` (`"Enter the name."`, `"Max 200 characters."`, the order message), `equipmentCreateBody(f): EquipmentCreate` (icon left out when null), `equipmentChanges(f, e): EquipmentUpdate` (icon sent only when changed; cleared → `null`).
  - `EquipmentView` (route `equipment`): "Equipment" + count (`004 items`) + "New item"; filters: search ("Search name"), `StatusFilter`; table: Serial `EQ·0004`, Icon (24px preview, `CircleHelp` in off ink for unknown, empty for none), Name, Order, State. Empty: "No equipment yet" / "Add the first item." and "No equipment matches".
  - `EquipmentFormPanel` props `{ item: EquipmentOut | null }`. Groups: "Item" (Name `n/200`, Order), "Icon" (`IconPicker`). `ActiveToggle` kind `'equipment'`, rooms `{ equipment_ids: [id] }`. Drafts `equipment:new` / `equipment:{id}`. Toast "{name} saved", detail `EQ·0004`.

- [ ] **Step 1: Write failing tests.**
  - `equipmentIcons.spec.ts`: 50 entries, names unique, each `icon` is defined; `iconFor('projector')` is the `Projector` component; `iconFor('https://x/y.png')` and `iconFor(null)` → `null`.
  - `icon-picker.spec.ts`: with `modelValue: 'projector'` the preview says "projector" and that radio has `aria-checked="true"`; clicking the `tv` radio emits `update:modelValue` `'tv'`; "No icon" emits `null`; typing "zzz" shows "No icons match." and still previews "projector"; `modelValue: 'old-icon'` previews "Unknown icon" and "old-icon".
  - `catalogForms.spec.ts` (equipment): empty → `{ name: 'Enter the name.' }`; 201 characters → "Max 200 characters."; create without icon leaves `icon` out; for an item with the unknown icon `'old-icon'`: no change → `{}`, only the name changed → `{ name: 'Screen' }` (icon not sent); icon cleared → `{ icon: null }`.
  - `equipment.spec.ts`: `/equipment?search=mic` calls `/api/v1/equipment?search=mic&is_active=true&page=1&size=20`; a row shows `EQ·0004` and the name; `.count` `002 items`; create with an icon POSTs `{"name":"Projector","icon":"projector","sort_order":0}`; a 409 `DUPLICATE` with `fields.name` shows under Name; the nav item "Equipment" has route `equipment`.
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/equipmentIcons.spec.ts src/components/__tests__/icon-picker.spec.ts src/utils/__tests__/catalogForms.spec.ts src/views/__tests__/equipment.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the files above.
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: equipment list, create, edit, icon picker, turn off and on"`.

### Task 4: End-to-end, notes and verification

**Files:**
- Create: `admin_dashboard/e2e/catalog.spec.ts` (real API), `admin_dashboard/e2e/catalog-layout.spec.ts` (mocked)
- Modify: `admin_dashboard/e2e/panel-motion.spec.ts` (add `/room-types` and `/equipment` to the slide-in-once cases), `admin_dashboard/README.md` (Catalog section), `DESIGN.md` (serial prefixes RT and EQ; "Icon Picker" component section; the catalog turn-off texts under "Place Panels", renamed "Record Panels")

- [ ] **Step 1: Real-API e2e** (skipped without `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD`): sign in → Room types → "New room type" with unique names → it appears in the list → Equipment → "New item" with a unique name and the `projector` icon → the row shows it → open it → "Turn off" → the dialog says "No rooms have it." → confirm → status "All" → the row says "Inactive".
- [ ] **Step 2: Mocked layout e2e:** `/room-types` and `/equipment` at 1366, 900 and 390 px: no sideways page scroll and the paging foot visible (same as `places-layout.spec.ts`); at 390 px the open equipment panel's icon grid has no sideways scroll.
- [ ] **Step 3: Full verification** in `admin_dashboard/`: `npm run lint`, `npm run type-check`, `npx vitest run`, `npm run build`, `npx playwright test`. Expected: all pass (real-API tests may be skipped). In the repo root `.venv/Scripts/python -m pytest -q` still passes.
- [ ] **Step 4: Commit** `git commit -m "Dashboard: phase 4 end-to-end checks and notes"`.
