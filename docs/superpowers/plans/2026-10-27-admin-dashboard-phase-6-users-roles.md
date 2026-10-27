# Admin Dashboard Phase 6 (Users and roles) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The People pages: Users (list with filters; create with a temporary password; edit; turn off/on; roles; reset password; signature) and Roles (rename only), with the Admin protected from locking themselves out.

**Architecture:** Same shape as Phases 3–5: `useResourceList`, `usePanelParam`, `usePanelRecord` (a record loads before its panel opens), `ListSearch`, `StatusFilter`, `PagingFoot`, `SearchPicker` (filter and field modes, `FIELD_WORDS`/`FILTER_WORDS`), `ActiveToggle`, `SidePanel` + `panelMotion`, drafts, `formChecks`. A saved user opens in a panel with four tabs (Details, Roles, Password, Signature), like the room panel; a new user is one form. `SignatureField` learns to upload and remove for any user. The signed-in Admin's id comes from the session store.

**Tech Stack:** Vue 3 (`<script setup lang="ts">`), TypeScript, Vue Router, Pinia, scoped CSS on the Tailwind v4 tokens, `lucide-vue-next`, Vitest + `@vue/test-utils` + jsdom, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (DSH-U01 to DSH-U08 in section 10; DSH-G01 to DSH-G10). API: `app/routers/users.py`, `app/routers/roles.py`, `app/schemas/user.py`, `app/schemas/role.py`, `app/services/user.py` (R5, R6, R9, R10, R11, R18).

## Global Constraints

- Branch `feature/dashboard-phase-6` from `main` (already created). Commit messages carry no AI attribution lines.
- API types only from `src/api/schema.d.ts`: `UserListItem`, `UserDetail`, `UserCreate`, `UserUpdate`, `UserChanged`, `ResetPasswordRequest`, `SetRolesRequest`, `RoleOut`, `RoleUpdate`, `DivisionOut`, `PositionOut`.
- Every Phase 2–5 rule applies (G01–G10; record loads before its panel; Turn off/on refuse while the form has unsaved changes; every dropdown is a `SearchPicker`).
- User limits (G06): `staff_id` 1–20; `name_en`, `name_kh` 1–100; `email` a valid address ≤ 254 (saved lower-case); `secondary_email` optional, valid, not the same as `email`; `phone` optional ≤ 20; `title` empty or one of `Mr.`, `Ms.`, `Mrs.`, `Dr.`; `position_id` required; `division_id` optional; passwords 8–128 characters, never trimmed. Role names 1–100.
- `GET /users` filters: `division_id`, `department_id`, `position_id`, `role` (a code), `province`, `is_active`, `search` (English name, Khmer name, staff ID, email). Admin only.
- A new user has no roles and must change the temporary password at first sign-in. Unique: `staff_id` ("This staff ID already exists."), `email` ("This email already exists.") → 409 `DUPLICATE` under that field.
- Roles: the 6 codes in seed order `ADMIN, ROOM_OWNER, STAFF, PITIKA, IT_LEAD, IT_STAFF`; `PITIKA`, `IT_LEAD`, `IT_STAFF` need a division (409 `DIVISION_REQUIRED`); `PUT /users/{id}/roles` replaces all.
- R9: turning a user off, or removing `ROOM_OWNER`, clears the rooms they own; the answer's `rooms_unassigned` lists their ids. R10: the last active Admin cannot be removed or turned off (409 `LAST_ADMIN`). R11: an Admin cannot turn themselves off or change their own roles' Admin (409 `SELF_ACTION_NOT_ALLOWED`) — DSH-U08 disables those buttons with a short reason.
- Reset password signs the user out everywhere; they must change it at next sign-in.
- Serials: users `US·0007`. Names: Khmer over English (owner decision); the title goes before the English name ("Ms. Sok Dara").
- Passwords are never put in the address, a draft, a toast or a log.

## Review Focus

- The signed-in Admin opens their own user → "Turn off" disabled with "You cannot turn yourself off.", the Admin role box disabled with "You cannot remove your own Admin role." (test in Task 3).
- Ticking Pitika, IT Lead or IT Staff for a user with no division → the warning "Pitika, IT Lead and IT Staff need a division. Choose one on the Details tab first." shows and "Save roles" stays off (test in Task 3).
- Removing Room owner from, or turning off, a user who owns rooms → the panel lists the rooms that lost their owner as `RM·0012` links (test in Task 3).
- A temporary password of 7 characters, or of 8 with spaces only at the ends → 7 is refused before sending ("Password must be 8 to 128 characters."); the spaces are kept, never trimmed (test in Task 1).
- Leaving the create form after "Generate" → the password is not kept in the draft (test in Task 2).

---

### Task 1: Shared parts — users and roles API, references, password helper, signature field for any user, user turn-off text

**Files:**
- Create: `admin_dashboard/src/api/users.ts`, `admin_dashboard/src/utils/password.ts`, `admin_dashboard/src/utils/userForms.ts`
- Modify: `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/api/references.ts` (`listDivisions`, `listPositions`, `listRoles`), `admin_dashboard/src/components/SignatureField.vue`, `admin_dashboard/src/components/list/ActiveToggle.vue`, `admin_dashboard/src/utils/pickerWords.ts`
- Test: `admin_dashboard/src/api/__tests__/users.spec.ts`, `admin_dashboard/src/utils/__tests__/password.spec.ts`, `admin_dashboard/src/utils/__tests__/userForms.spec.ts`, `admin_dashboard/src/components/__tests__/signature.spec.ts`, `admin_dashboard/src/components/list/__tests__/active-toggle.spec.ts`

**Interfaces:**
- Produces:
  - `users.ts`: `interface UserFilters { division_id?; department_id?; position_id?: number; role?: string; province?: string; is_active?: boolean; search?: string; page?: number; size?: number }`; `listUserPage(client, f): Promise<Page<UserListItem>>`, `getUser(client, id): Promise<UserDetail>`, `createUser(client, body: UserCreate): Promise<UserDetail>`, `updateUser(client, id, changes: UserUpdate): Promise<UserChanged>`, `setUserRoles(client, id, codes: string[]): Promise<UserChanged>`, `resetPassword(client, id, temporary: string): Promise<void>`, `uploadUserSignature(client, id, file: File): Promise<UserDetail>`, `deleteUserSignature(client, id): Promise<void>`, `listRoles(client): Promise<RoleOut[]>`, `updateRole(client, id, changes: RoleUpdate): Promise<RoleOut>`, `countUsersWithRole(client, code: string): Promise<number>` (active users, `size=1`).
  - `references.ts`: `listDivisions(client): Promise<DivisionOut[]>`, `listPositions(client): Promise<PositionOut[]>` (every status, all pages).
  - `password.ts`: `generatePassword(length = 14): string` — from `crypto.getRandomValues`, at least one lower-case letter, upper-case letter, digit and one of `!@#$%^&*-_=+?`, no look-alikes (`0 O o 1 l I`); `passwordProblem(text: string): string | null` → `"Password must be 8 to 128 characters."` when the length (not trimmed) is outside 8–128.
  - `userForms.ts`: `type UserForm = { staff_id; title: string | null; name_kh; name_en; email; secondary_email; phone: string; division_id: number | null; position_id: number | null; email_notifications: boolean; temporary_password: string }`; `emptyUserForm()`, `userFormOf(u: UserDetail)` (password `''`), `userProblems(f, creating: boolean)` (`"Enter the staff ID."`, `"Max 20 characters."`, the name messages, `"Enter the email."`, `"Enter a valid email."`, `"Use a different email from the main one."`, `"Max 20 characters."` (phone), `"Choose a position."`, the password message when creating), `userCreateBody(f): UserCreate` (trimmed; empty optional text left out; password as typed), `userChanges(f, u): UserUpdate` (only changed; cleared optional text → `null`; email compared lower-case).
  - `SignatureField`: new optional props `upload?: (file: File) => Promise<UserDetail>` and `remove?: () => Promise<void>`, defaulting to the signed-in user's own (`uploadMySignature`, `deleteMySignature`); everything else unchanged.
  - `ActiveToggle`: kind adds `'user'` (the count is the number of rooms the user owns); new optional prop `locked?: string` — the button is disabled and the reason shows beside it (linked with `aria-describedby`). User texts: 0 → "They cannot sign in until you turn them on again."; 1 → "They cannot sign in, and 1 room loses its owner. You can turn them on again."; n → "They cannot sign in, and 3 rooms lose their owner. You can turn them on again."
  - `pickerWords.ts`: `FIELD_WORDS.title` (`all: 'No title'`), `FIELD_WORDS.division` (`all: 'No division'`), `FIELD_WORDS.position` (`all: 'Choose a position'`); `FILTER_WORDS.division`, `.position`, `.role` (`all: 'All roles'`).

- [ ] **Step 1: Write failing tests.**
  - `users.spec.ts`: `listUserPage(api, { department_id: 4, role: 'PITIKA', is_active: true, page: 1, size: 20 })` → `/api/v1/users?department_id=4&role=PITIKA&is_active=true&page=1&size=20` (the query keeps the order it is given; the Users page's filter spec lists division, department, position, role, province, search); `setUserRoles(api, 7, ['STAFF'])` → `PUT /api/v1/users/7/roles` body `{"role_codes":["STAFF"]}`; `resetPassword(api, 7, ' secret12 ')` → body `{"temporary_password":" secret12 "}`; `uploadUserSignature` sends `PUT /api/v1/users/7/signature` as form data with field `file`.
  - `password.spec.ts`: 200 generated passwords are all 14 long, each has the four kinds, none has a look-alike; `passwordProblem('1234567')` → the message; `passwordProblem(' 123456 ')` → `null` (8 with spaces).
  - `userForms.spec.ts`: empty form while creating → staff ID, both names, email, position and password problems; `secondary_email` equal to `email` (different case) → "Use a different email from the main one."; `userCreateBody` leaves out empty `title`, `secondary_email`, `phone`, `division_id`; `userChanges` of an unchanged form → `{}`, a cleared phone → `{ phone: null }`, `title: null` from `'Ms.'` → `{ title: null }`.
  - `signature.spec.ts`: mounted with `upload` and `remove` props, choosing a file calls `upload` (not `/me/signature`) and Remove (after the confirm) calls `remove`.
  - `active-toggle.spec.ts`: kind `'user'` with count 3 → "They cannot sign in, and 3 rooms lose their owner."; `locked: 'You cannot turn yourself off.'` → the button is disabled and the reason is visible.
- [ ] **Step 2: Run** `npx vitest run src/api/__tests__/users.spec.ts src/utils/__tests__/password.spec.ts src/utils/__tests__/userForms.spec.ts src/components/__tests__/signature.spec.ts src/components/list/__tests__/active-toggle.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the files above.
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: users and roles API, password helper, user form checks, signature field for any user"`.

### Task 2: Users list and the new-user form

**Files:**
- Create: `admin_dashboard/src/views/UsersView.vue`, `admin_dashboard/src/views/people/UserFilters.vue`, `admin_dashboard/src/views/people/NewUserPanel.vue`, `admin_dashboard/src/views/people/UserDetailsForm.vue` (the shared fields)
- Modify: router (`users` at `/users`, title "Users"), `nav.ts`, `shell.spec.ts` (route; the "not yet built" test uses "Roles")
- Test: `admin_dashboard/src/views/__tests__/users.spec.ts`

**Interfaces:**
- Consumes: Task 1; `DepartmentPicker`, `SearchPicker`, `listDepartments`, `listOffices`, `listProvinces`.
- Produces:
  - `UsersView` (route `users`): "Users" + count (`012 users`) + "New user"; first filter row: search ("Search name, staff ID or email"), Role picker (the 6 role names), Department picker (filter mode), `StatusFilter`, "More filters"; second row: Division picker (grouped by department), Position picker, Province picker. Table: Serial `US·0007`, Name (Khmer over English with title), Staff ID (mono), Email, Division and position (two lines), Province, Roles (small chips with the role's English name, "No roles" in off ink), State (`StateMarks`), Last sign-in (`formatPhnomPenh`, "Never" in off ink). Row → `?id=7`.
  - `UserDetailsForm` props `{ form: UserForm; errors: Record<string, string>; creating: boolean; divisions; departments; positions }` — groups "Name" (Title picker, Khmer name, English name, Staff ID), "Contact" (Email, Second email, Phone, Email notifications switch), "Work" (Division picker grouped by department, nullable "No division"; Position picker), and when `creating` "First password" (temporary password `PasswordInput` with "Generate" and "Copy" buttons, hint "They must change it when they first sign in."). It edits `form` in place.
  - `NewUserPanel`: the create form (`UserDetailsForm creating`); "Create user"; toast "{name_en} added", detail `US·0007 · no roles yet`; then opens the new user's panel on the Roles tab (`?id=7&tab=roles`). Draft `user:new` keeps every field except `temporary_password`.

- [ ] **Step 1: Write failing view tests:** `/users?role=PITIKA&department_id=4` calls `/api/v1/users?department_id=4&role=PITIKA&is_active=true&page=1&size=20`; a row shows `US·0007`, Khmer over English with "Ms." before the English name, the staff ID, role chips "Pitika" and "Staff", and "Never" for no sign-in; choosing the role picker's "IT Lead" sets `role=IT_LEAD` in the address; "New user" → "Generate" fills a 14-character password; creating POSTs the form (password as typed) and then the address is `?id=9&tab=roles`; a 409 `DUPLICATE` with `fields.email` shows under Email; after typing and "Generate", closing and reopening "New user" keeps the typed name but not the password; the nav item "Users" has route `users`.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/users.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** (list like Departments; filters like Rooms).
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: users list with filters, and create a user with a temporary password"`.

### Task 3: The user panel — details, roles, password, signature, turn off/on

**Files:**
- Create: `admin_dashboard/src/views/people/UserPanel.vue`, `admin_dashboard/src/views/people/UserRoles.vue`, `admin_dashboard/src/views/people/UserPassword.vue`
- Modify: `UsersView.vue` (open `UserPanel` for `?id=7`, tab from `?tab=details|roles|password|signature`)
- Test: `admin_dashboard/src/views/__tests__/user-panel.spec.ts`

**Interfaces:**
- Consumes: Tasks 1–2; `useSessionStore().user.id`.
- Produces:
  - `UserPanel` props `{ user: UserDetail; tab?: 'details' | 'roles' | 'password' | 'signature' }`, emits `saved(user)`, `close`, `tab(name)`. Head: Khmer name, "Ms. Sok Dara · US·0007". Tabs underlined in crimson (as the room panel). Foot: `ActiveToggle` kind `'user'` with `count: () => Promise.resolve(user.owned_room_ids.length)` and `locked` "You cannot turn yourself off." when it is the signed-in user; on Details also "Cancel" / "Save changes".
  - Details tab: `UserDetailsForm` (not creating); PATCH only changes; drafts `user:{id}` with `updatedAt`.
  - `UserRoles`: six check boxes in seed order with the role names (English, Khmer under it); "Needs a division" note under Pitika, IT Lead and IT Staff; "Save roles" sends `PUT … role_codes` in seed order; when a needing role is ticked and the user has no division: the warning "Pitika, IT Lead and IT Staff need a division. Choose one on the Details tab first." and "Save roles" off; the signed-in Admin's own Admin box disabled with "You cannot remove your own Admin role."; 409 `LAST_ADMIN` / `DIVISION_REQUIRED` messages show at the top.
  - `UserPassword`: `PasswordInput` + "Generate" + "Copy"; "Set temporary password" asks in the confirm dialog ("Set a temporary password for {name_en}?", "They are signed out everywhere and must choose a new password when they next sign in.", button "Set password"); then toast "Temporary password set" and the field empties.
  - Signature tab: `SignatureField` with `upload`/`remove` for this user.
  - After any answer with `rooms_unassigned` not empty: a notice in the panel "These rooms have no owner now:" with each as a link `RM·0012` to `/?room=12`.

- [ ] **Step 1: Write failing tests:** opening `?id=7` shows the Details tab with the user's values and "Save changes" off; changing the phone sends `{"phone":"012 345 678"}`; on Roles, ticking "IT Lead" for a user without a division shows the warning and keeps "Save roles" off; ticking "Room owner" off for a user who owns rooms 12 and 13, saving answers `rooms_unassigned: [12, 13]` → links `RM·0012`, `RM·0013` to `/?room=12` and `/?room=13`; with the session user id 7 the Admin box and "Turn off" are disabled with their reasons; "Set temporary password" after the confirm sends `POST /api/v1/users/7/reset-password` and empties the field; the Signature tab's upload calls `PUT /api/v1/users/7/signature`.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/user-panel.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: user panel with details, roles, temporary password, signature and turn off"`.

### Task 4: Roles page

**Files:**
- Create: `admin_dashboard/src/views/RolesView.vue`, `admin_dashboard/src/views/people/RolePanel.vue`
- Modify: router (`roles` at `/roles`, title "Roles"), `nav.ts`, `shell.spec.ts` (route; the "not yet built" test is removed — every page is built)
- Test: `admin_dashboard/src/views/__tests__/roles.spec.ts`

**Interfaces:**
- Produces: `RolesView` (route `roles`): "Roles" + count (`006 roles`), no "New" button, no filters, no paging (6 roles); table: Code (mono), Role (Khmer over English), Users (active users with it, from `countUsersWithRole`, mono, "–" while loading), "Needs a division" for Pitika, IT Lead, IT Staff. Row → `?id=3`. `RolePanel` props `{ role: RoleOut }`: Khmer name and English name only, "Save changes" (PATCH only changes), toast "{name_en} saved"; a note "The code and the rules of a role never change.".

- [ ] **Step 1: Write failing tests:** the page lists the 6 roles in the API order with codes and Khmer over English; the Users column shows the counts from `/api/v1/users?role=CODE&is_active=true&page=1&size=1`; renaming "Staff" to "Employee" sends `PATCH /api/v1/roles/3` `{"name_en":"Employee"}`; an empty English name shows "Enter the English name." and sends nothing; the nav item "Roles" has route `roles`.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/roles.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again, then `npx vitest run`. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: roles page, rename only"`.

### Task 5: End-to-end, notes and verification

**Files:**
- Create: `admin_dashboard/e2e/people.spec.ts` (real API), `admin_dashboard/e2e/people-layout.spec.ts` (mocked)
- Modify: `admin_dashboard/e2e/panel-motion.spec.ts` (add `/users`, `/roles`), `admin_dashboard/README.md` (People section), `DESIGN.md` (serial US; user panel tabs; the user turn-off text; the "locked" reason style)

- [ ] **Step 1: Real-API e2e** (skipped without `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD`): sign in → Users → "New user" with a unique staff ID and email, the first position, "Generate" → "Create user" → the Roles tab opens → tick "Staff" → "Save roles" → the row shows the "Staff" chip → Password tab → "Generate" → "Set temporary password" → confirm → "Temporary password set" → open your own user → "Turn off" is disabled. Roles → rename nothing; the six rows show.
- [ ] **Step 2: Mocked layout e2e:** `/users` (20 users, long names and many roles) and `/roles` at 1366, 900 and 390 px: no sideways page scroll; `/users` shows the paging foot.
- [ ] **Step 3: Full verification** in `admin_dashboard/`: `npm run lint`, `npm run type-check`, `npx vitest run`, `npm run build`, `npx playwright test`; in the repo root `.venv/Scripts/python -m pytest -q`. Expected: all pass (real-API tests may be skipped).
- [ ] **Step 4: Commit** `git commit -m "Dashboard: phase 6 end-to-end checks and notes"`.
