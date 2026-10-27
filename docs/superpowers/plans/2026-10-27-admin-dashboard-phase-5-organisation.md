# Admin Dashboard Phase 5 (Organisation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Organisation pages: Departments (by office), Divisions (by department) and Positions — each a searchable, paged list with create, edit, move (department to another office, division to another department), sort order and turn off/on, warning before a turn-off how many users it touches.

**Architecture:** Same shape as the Phase 3–4 pages, reusing `useResourceList`, `usePanelParam`, `usePanelRecord` (a record loads before its panel opens), `ListSearch`, `StatusFilter`, `PagingFoot`, `StateMarks`, `ActiveToggle` (blocked while the form has unsaved changes), `SidePanel` + `panelMotion`, drafts, `selectOptions`, `formChecks`/`sortOrder`, `listPage.css`. `ActiveToggle` stops knowing about rooms: the page passes the counting function, so it can count rooms or users.

**Tech Stack:** Vue 3 (`<script setup lang="ts">`), TypeScript, Vue Router, Pinia, scoped CSS on the Tailwind v4 tokens, `lucide-vue-next`, Vitest + `@vue/test-utils` + jsdom, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (DSH-O01 to DSH-O03 in section 10; DSH-G01 to DSH-G10 in section 9). API: `app/routers/{departments,divisions,positions,users}.py`, `app/schemas/{department,division,position}.py`, `app/services/{department,division,position,user}.py`.

## Global Constraints

- Branch `feature/dashboard-phase-5` from `main` (already created). Commit messages carry no AI attribution lines.
- API types only from `src/api/schema.d.ts`: `DepartmentOut`, `DepartmentCreate`, `DepartmentUpdate`, `DivisionOut`, `DivisionCreate`, `DivisionUpdate`, `PositionOut`, `PositionCreate`, `PositionUpdate`, `LocationOut`.
- Every Phase 2–4 rule applies (G01 paging, G02 filters in the address, G03 PATCH only changed fields, G04/G05 API messages, G06 client checks with the API limits, G07 turn off in the confirm dialog, G08 parent selects hide inactive items except the chosen one, G09 toast + refresh, G10 empty and loading states). A saved record loads before its panel opens; Turn off/on refuse while the form has unsaved changes.
- API limits (G06): all three `name_en` and `name_kh` 1–100; division `short_name` ≤ 20; `sort_order` 0–9999.
- List filters the API has: departments `location_id`, `is_active`, `search` (English and Khmer name); divisions `department_id`, `is_active`, `search` (English, Khmer and short name); positions `is_active`, `search`. Lists answer only parent ids (`location_id`, `department_id`).
- Unique (409 `DUPLICATE` under `name_en`): department `name_en` per office; division `name_en` per department; position `name_en`.
- R2/R3: a department needs an active office and a division an active department (on create and move); turning one on under an inactive parent → 409 `INACTIVE_REFERENCE`, the record stays off, the panel shows the API message.
- Turning off changes nobody: users stay in their division and keep their position, but no new division can be added to an off department, no new user can join an off division or get an off position. Moving a department moves the province of every user in its divisions (computed by the API).
- Serials: departments `DP·0003`, divisions `DV·0012`, positions `PS·0004`.
- Names: Khmer over English everywhere (owner decision). Day and night themes: colour tokens only. English UI, no emoji.

## Review Focus

- A division whose department is off, or no longer in the department list → the Department select still shows it ("(off)" or "Unknown department") and an edit of other fields does not send `department_id` (test in Task 3).
- Moving a department to an office that already has a department with that English name → 409 `DUPLICATE` under English name, nothing else changes (test in Task 2).
- Turning on a division whose department is off → 409 `INACTIVE_REFERENCE`, the message shows in the panel, the row stays "Inactive" (test in Task 3).
- The users count failing when turning off → the confirm still opens with the general text for that kind (test in Task 1).
- `?department_id=99` (gone) on the Divisions page → the list loads and the filter shows "Unknown department" (test in Task 3).

---

### Task 1: Shared parts — organisation API, users count, turn-off texts, department options

**Files:**
- Create: `admin_dashboard/src/api/organisation.ts`, `admin_dashboard/src/utils/departmentOptions.ts`
- Modify: `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/api/references.ts` (`listDepartments`), `admin_dashboard/src/components/list/ActiveToggle.vue`, the five panels that use it (`views/places/{Office,Building,Floor}FormPanel.vue`, `views/catalog/{RoomType,Equipment}FormPanel.vue`)
- Test: `admin_dashboard/src/api/__tests__/organisation.spec.ts`, `admin_dashboard/src/utils/__tests__/departmentOptions.spec.ts`, `admin_dashboard/src/components/list/__tests__/active-toggle.spec.ts`

**Interfaces:**
- Produces:
  - `types.ts`: the nine organisation types above.
  - `organisation.ts`: `interface DepartmentFilters { location_id?: number; is_active?: boolean; search?: string; page?: number; size?: number }`, `DivisionFilters` (with `department_id`), `PositionFilters`; `listDepartmentPage`, `getDepartment`, `createDepartment`, `updateDepartment` (`/api/v1/departments`); `listDivisionPage`, `getDivision`, `createDivision`, `updateDivision` (`/api/v1/divisions`); `listPositionPage`, `getPosition`, `createPosition`, `updatePosition` (`/api/v1/positions`); `countActiveUsers(client, where: { department_id?: number; division_id?: number; position_id?: number }): Promise<number>` → `GET /api/v1/users?…&is_active=true&page=1&size=1`, the answer's `total`.
  - `references.ts`: `listDepartments(client): Promise<DepartmentOut[]>` (every status, all pages, like `listOffices`).
  - `departmentOptions.ts`: `departmentGroups(departments: DepartmentOut[], offices: LocationOut[], chosen: number | null): Array<{ label: string; options: SelectOption[] }>` — one group per office that has departments to show (office `name_en`, " (off)" when the office is off), in the office list's order; inside, `selectOptions` rules (active ones, the chosen one marked "(off)"); a chosen id not in `departments` → a first group with label `''` holding `{ value: chosen, label: 'Unknown department' }`.
  - `ActiveToggle`: the `rooms` prop is replaced by `count: () => Promise<number>`; `kind` adds `'department' | 'division' | 'position'`. The five existing panels pass `count: () => countActiveRooms(api, { … })` with the same filters as before. Texts for the new kinds (n = count, null = count failed; "You can turn it on again." ends each):

| kind | null | 0 | 1 | n |
| --- | --- | --- | --- | --- |
| department | Its users stay where they are, but no new division can be added to it. | No users work in it. | 1 user works in this department and stays. No new division can be added to it. | 12 users work in this department and stay. No new division can be added to it. |
| division | Its users stay in it, but no new user can join it. | No users work in it. | 1 user works in this division and stays in it. No new user can join it. | 12 users work in this division and stay in it. No new user can join it. |
| position | Users with it keep it, but no new user can get it. | No users have it. | 1 user has this position and keeps it. No new user can get it. | 12 users have this position and keep it. No new user can get it. |

- [ ] **Step 1: Write failing tests.**
  - `organisation.spec.ts` (style of `catalog.spec.ts`): `listDivisionPage(api, { department_id: 4, search: 'it', is_active: true, page: 1, size: 20 })` → `/api/v1/divisions?department_id=4&search=it&is_active=true&page=1&size=20`; `updateDepartment(api, 3, { location_id: 5 })` → `PATCH /api/v1/departments/3` body `{"location_id":5}`; `countActiveUsers(api, { position_id: 2 })` calls `/api/v1/users?position_id=2&is_active=true&page=1&size=1` and returns the `total`.
  - `departmentOptions.spec.ts`: two offices (Head Office active, Old Branch off), departments IT (office 3, active), HR (office 3, off), Audit (office 6, active) → with `chosen` null: `[{ label: 'Head Office', options: [IT] }, { label: 'Old Branch (off)', options: [Audit] }]`; with `chosen` = HR id: Head Office holds IT and "HR (off)"; with `chosen` 99: first group `{ label: '', options: [{ value: 99, label: 'Unknown department' }] }`.
  - `active-toggle.spec.ts`: change the mounts to pass `count` (a `vi.fn` returning 12, 1, 0 or rejecting) instead of `rooms` and keep every existing expectation except the `/api/v1/rooms?…` URL check (that moves to the panels); add: kind `'department'` with 12 → "12 users work in this department and stay. No new division can be added to it."; kind `'division'` with 1 → "1 user works in this division and stays in it."; kind `'position'` with a rejecting count → "Users with it keep it, but no new user can get it."
- [ ] **Step 2: Run** `npx vitest run src/api/__tests__/organisation.spec.ts src/utils/__tests__/departmentOptions.spec.ts src/components/list/__tests__/active-toggle.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the files above and update the five panels.
- [ ] **Step 4: Run** the same command, then `npx vitest run` (the place and catalog view tests still pass: they check the turn-off text through the panels). Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: organisation API functions, users count, turn-off texts for organisation"`.

### Task 2: Departments page

**Files:**
- Create: `admin_dashboard/src/utils/orgForms.ts` (department part), `admin_dashboard/src/views/DepartmentsView.vue`, `admin_dashboard/src/views/organisation/DepartmentFormPanel.vue`
- Modify: router (`departments` at `/departments`, title "Departments"), `nav.ts`, `shell.spec.ts` (route added; the "not yet built" test uses "Users")
- Test: `admin_dashboard/src/utils/__tests__/orgForms.spec.ts`, `admin_dashboard/src/views/__tests__/departments.spec.ts`

**Interfaces:**
- Consumes: Task 1; `listOffices`, `selectOptions`, `formChecks` (`nameProblems`, `checkOrder`), `orderValue`.
- Produces:
  - `orgForms.ts`: `type DepartmentForm = { location_id: number | null; name_kh: string; name_en: string; sort_order: string }`; `emptyDepartmentForm(locationId?: number | null)`, `departmentFormOf(d)`, `departmentProblems(f)` (`"Choose an office."`, the name and order messages), `departmentCreateBody(f): DepartmentCreate` (empty order → 0), `departmentChanges(f, d): DepartmentUpdate` (a new `location_id` = move).
  - `DepartmentsView` (route `departments`): "Departments" + count (`004 departments`) + "New department" (pre-fills the office filter); filters: search ("Search Khmer or English name"), Office select (G08, "Unknown office"), `StatusFilter`; table: Serial `DP·0003`, Department (Khmer over English), Office (name from the office list, `#id` when unknown), Order, State.
  - `DepartmentFormPanel` props `{ department: DepartmentOut | null; defaultOfficeId?: number | null }`. Groups: "Where" (Office; on edit the hint "Change to move the department. Its users' province changes with it."), "Names", "Order". `ActiveToggle` kind `'department'`, `count: () => countActiveUsers(api, { department_id })`. Drafts `department:new` / `department:{id}`. Toast "{name_en} saved", detail `DP·0003 · {office}`.

- [ ] **Step 1: Write failing tests** for the department helpers: empty → office and both name problems; moving `{ ...departmentFormOf(d), location_id: 5 }` → `{ location_id: 5 }`; unchanged → `{}`; order `'10000'` → the order message.
- [ ] **Step 2: Write failing view tests:** `/departments?location_id=3` calls `/api/v1/departments?location_id=3&is_active=true&page=1&size=20`; a row shows `DP·0003`, Khmer over English and the office name, and `#99` for an unknown office; "New department" pre-sets the office; a move answered with 409 `DUPLICATE` (`fields.name_en`) shows under English name and the list is not reloaded; the nav item "Departments" has route `departments`.
- [ ] **Step 3: Run** `npx vitest run src/utils/__tests__/orgForms.spec.ts src/views/__tests__/departments.spec.ts`. Expected: FAIL.
- [ ] **Step 4: Implement** (copy the Buildings page structure).
- [ ] **Step 5: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: departments list, create, edit, move, turn off and on"`.

### Task 3: Divisions page

**Files:**
- Create: `admin_dashboard/src/views/DivisionsView.vue`, `admin_dashboard/src/views/organisation/DivisionFormPanel.vue`
- Modify: `orgForms.ts` (division part), router (`divisions`), `nav.ts`, `shell.spec.ts` router
- Test: `orgForms.spec.ts` (division part), `admin_dashboard/src/views/__tests__/divisions.spec.ts`

**Interfaces:**
- Consumes: Tasks 1–2; `departmentGroups`, `listDepartments`, `listOffices`.
- Produces:
  - `orgForms.ts`: `type DivisionForm = { department_id: number | null; name_kh: string; name_en: string; short_name: string; sort_order: string }`; `emptyDivisionForm(departmentId?)`, `divisionFormOf(d)`, `divisionProblems(f)` (`"Choose a department."`, names, `"Max 20 characters."` for the short name, order), `divisionCreateBody(f)` (empty short name left out), `divisionChanges(f, d)` (new `department_id` = move; cleared short name → `null`).
  - `DivisionsView` (route `divisions`): "Divisions" + count + "New division" (pre-fills the department filter); filters: search ("Search name or short name"), Department select with one `<optgroup>` per office (`departmentGroups`), `StatusFilter`; table: Serial `DV·0012`, Division (Khmer over English, short name in mono after the English name), Department, Office (from the department's office; "Unknown" in off ink when the department is not in the list), Order, State.
  - `DivisionFormPanel` props `{ division: DivisionOut | null; defaultDepartmentId?: number | null }`. Groups: "Where" (Department select with office groups; on edit hint "Change to move the division"), "Names" (Khmer, English, Short name `n/20` with placeholder "optional, e.g. IT", Order). `ActiveToggle` kind `'division'`, `count: () => countActiveUsers(api, { division_id })`. Drafts `division:new` / `division:{id}`. Toast detail `DV·0012 · {department}`.

- [ ] **Step 1: Write failing tests** for the division helpers: empty → department and name problems; short name of 21 → "Max 20 characters."; clearing the short name → `{ short_name: null }`; a new department → `{ department_id: 8 }`.
- [ ] **Step 2: Write failing view tests:** `/divisions?department_id=4` calls `/api/v1/divisions?department_id=4&is_active=true&page=1&size=20`; the Department filter has an optgroup labelled with the office name; `?department_id=99` loads and the filter shows "Unknown department"; a row shows `DV·0012`, the department and the office names; an edit of a division whose department is off keeps "(off)" in the select and saving a new English name sends only `{ name_en }`; turning on a division whose department is off answered with 409 `INACTIVE_REFERENCE` shows the message and the row stays "Inactive"; the nav item "Divisions" has route `divisions`.
- [ ] **Step 3: Run** `npx vitest run src/utils/__tests__/orgForms.spec.ts src/views/__tests__/divisions.spec.ts`. Expected: FAIL.
- [ ] **Step 4: Implement.**
- [ ] **Step 5: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: divisions list, create, edit, move, turn off and on"`.

### Task 4: Positions page

**Files:**
- Create: `admin_dashboard/src/views/PositionsView.vue`, `admin_dashboard/src/views/organisation/PositionFormPanel.vue`
- Modify: `orgForms.ts` (position part), router (`positions`), `nav.ts`, `shell.spec.ts` router
- Test: `orgForms.spec.ts` (position part), `admin_dashboard/src/views/__tests__/positions.spec.ts`

**Interfaces:**
- Produces: `type PositionForm = { name_kh; name_en; sort_order }` with `emptyPositionForm`, `positionFormOf`, `positionProblems`, `positionCreateBody`, `positionChanges` (same rules as room types); `PositionsView` (route `positions`): "Positions" + count + "New position"; filters: search, `StatusFilter`; table: Serial `PS·0004`, Position (Khmer over English), Order, State. `PositionFormPanel` props `{ position: PositionOut | null }`, groups "Names", "Order"; `ActiveToggle` kind `'position'`, `count: () => countActiveUsers(api, { position_id })`. Drafts `position:new` / `position:{id}`.

- [ ] **Step 1: Write failing tests:** the position helpers (empty → both name problems; only the order changed → `{ sort_order: 3 }`); view: `/positions?search=lead` calls `/api/v1/positions?search=lead&is_active=true&page=1&size=20`; a row shows `PS·0004` and Khmer over English; create POSTs `{"name_kh":…,"name_en":…,"sort_order":0}`; 409 `DUPLICATE` under English name; the nav item "Positions" has route `positions`.
- [ ] **Step 2: Run** `npx vitest run src/utils/__tests__/orgForms.spec.ts src/views/__tests__/positions.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** (copy the Room types page).
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: positions list, create, edit, turn off and on"`.

### Task 5: End-to-end, notes and verification

**Files:**
- Create: `admin_dashboard/e2e/organisation.spec.ts` (real API), `admin_dashboard/e2e/organisation-layout.spec.ts` (mocked)
- Modify: `admin_dashboard/e2e/panel-motion.spec.ts` (add `/departments`, `/divisions`, `/positions`), `admin_dashboard/README.md` (Organisation section), `DESIGN.md` (serial prefixes DP, DV, PS; the users-count turn-off texts under "Record Panels"; grouped department select)

- [ ] **Step 1: Real-API e2e** (skipped without `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD`): sign in → Departments → "New department" in the first office with unique names → Divisions → "New division" in that department → it appears in the list → Positions → "New position" → open it → "Turn off" → the dialog says "No users have it." → confirm → status "All" → the row says "Inactive".
- [ ] **Step 2: Mocked layout e2e:** the three pages at 1366, 900 and 390 px: no sideways page scroll, the paging foot visible.
- [ ] **Step 3: Full verification** in `admin_dashboard/`: `npm run lint`, `npm run type-check`, `npx vitest run`, `npm run build`, `npx playwright test`; in the repo root `.venv/Scripts/python -m pytest -q`. Expected: all pass (real-API tests may be skipped).
- [ ] **Step 4: Commit** `git commit -m "Dashboard: phase 5 end-to-end checks and notes"`.
