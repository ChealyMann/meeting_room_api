# Admin Dashboard: Requirements

A web dashboard for managing the Meeting Room Booking API: rooms, places, organisation, users and roles.

Status: approved (26 Oct 2026). Items marked **(my call)** were chosen by the writer and accepted by the owner; they can still be changed.

## 1. Why

The API for rooms, places, organisation and users is finished and tested. Today the only way to manage the data is `/docs` (Swagger), which is slow and easy to get wrong. The Admin needs real screens to set up offices, rooms and users before bookings start.

Bookings are not built yet. This dashboard does not need them. Booking pages are added later.

## 2. Who uses it

| Who | What they can do now |
| --- | --- |
| Admin | Everything in this document |
| Other roles (Room owner, Staff, Pitika, IT Lead, IT Staff) | Nothing yet. Their permissions are not decided. They see "You do not have access" after sign-in. **(my call)** |

Later, a Room owner may manage only their own rooms (the API already supports this). That is not part of this version.

## 3. Goals

- The Admin can do every create, edit, turn off/on task without `/docs`.
- The dashboard follows the API rules exactly and shows the API's own error messages next to the right field.
- It looks clean and designed for this bank, not like a generic template.

## 4. Not in this version

- Bookings, approvals, IT support pages.
- Reports and charts.
- Screens for roles other than Admin.
- A phone app. (The dashboard must still work on a tablet.)
- Deleting records. The API has no delete except room photos. Records are turned off instead.

## 5. Things that would make it a failure

- It looks like a generic AI admin template (purple gradients, emoji, cards everywhere, the same rounded box for everything).
- A door code shows in a list or on a page without the Admin asking for it.
- The dashboard has its own rules that differ from the API (for example, it allows a name the API refuses, or refuses a name the API allows).
- The Admin loses typed data because the access token expired while they were filling a form.

## 6. Technology

| Part | Choice |
| --- | --- |
| Framework | Vue 3, Composition API, `<script setup lang="ts">` |
| Language | TypeScript |
| Build tool | Vite |
| Pages | Vue Router |
| Shared state | Pinia (sign-in, current user, lookups like provinces) |
| Styles | Tailwind CSS with the NBC theme tokens (section 8) |
| Icons | Lucide (stroke icons) |
| API types | Generated from the API's `/openapi.json` with `openapi-typescript`. Re-run after every API change. |
| Folder | `admin_dashboard/` in the same Git repository as the API, with its own `package.json`. API and dashboard changes can go in one commit. |
| API address | `VITE_API_URL`, e.g. `http://localhost:8000` |

**API setting needed:** add the dashboard's address to `CORS_ORIGINS` in the API `.env`, e.g. `http://localhost:5173` (Vite's dev port). Without it the browser blocks every call.

## 7. Sign-in and session

| ID | Requirement |
| --- | --- |
| DSH-A01 | Sign-in page: email and password. Calls `POST /api/v1/auth/login`. |
| DSH-A02 | Wrong email or password: show the API message ("INVALID_CREDENTIALS"). Too many tries (429): show "Try again in N minutes" from the `Retry-After` header. |
| DSH-A03 | If the answer has `must_change_password: true`, go to the "Choose a new password" page first. Nothing else opens until it is done (`POST /auth/change-password`). |
| DSH-A04 | After sign-in, load `GET /me`. If the user does not have the `ADMIN` role, show "You do not have access" and a sign-out button. |
| DSH-A05 | The access token lasts 15 minutes. When a call returns 401, call `POST /auth/refresh` once, then repeat the call. If refresh fails, go to sign-in and come back to the same page after. |
| DSH-A06 | Forms keep what the user typed when the token is refreshed or when they must sign in again (draft kept in memory). |
| DSH-A07 | Tokens: access token in memory only; refresh token in `sessionStorage`, so closing the browser signs out. **(my call)** |
| DSH-A08 | Sign out: call `POST /auth/logout`, then delete both tokens. |
| DSH-A09 | "My profile" page: `GET/PATCH /me` (second email, phone, photo link, email notifications) and my signature (`PUT/DELETE /me/signature`). |

## 8. Look and feel

Same theme as the NBC mockup (`frontend_mockup/meeting_room_mockup`), redesigned to look better. A design skill is used at build time to make the final design.

| Token | Value |
| --- | --- |
| Page background | Warm cream `#F9F7F5` |
| Cards | White `#FFFFFF`, border `#E9E3DD` |
| Sidebar | Dark crimson `#260707`, borders `#3D0C0C`, gold accent `#FACC15` |
| Main action | NBC crimson `#991B1B`, hover `#7F1D1D`; white icons on red buttons |
| Text | Dark coffee `#3E2B1E` |
| Fonts | Poppins (UI), Kantumruy Pro (Khmer text), JetBrains Mono (numbers, codes, ids) |
| Radius | 8–16 px |

Rules:
- No emoji. Lucide stroke icons only.
- Khmer and English names always show together where both exist.
- Lists use tables, not card grids, so many records fit on one screen.
- Dates from the API are UTC. Show them in Cambodia time (`Asia/Phnom_Penh`). Room hours are already Cambodia time.
- Works on a laptop (1280 px) and a tablet (768 px).

## 9. Rules every page follows

| ID | Requirement |
| --- | --- |
| DSH-G01 | Lists use the API paging: `page` and `size` (20 by default, max 100). Show the total. |
| DSH-G02 | Every list has a search box and an "Active / Inactive / All" filter, plus the filters the API offers for that resource. Filters are kept in the page address, so a page can be shared or reloaded. |
| DSH-G03 | Create and edit open in a side panel over the list **(my call)**. Save sends only the fields that changed (PATCH). |
| DSH-G04 | Errors: the API returns `{error: {code, message, fields}}`. Show each `fields` message under its field. Show `message` at the top of the form. |
| DSH-G05 | Common codes: 409 `DUPLICATE` (name used), 409 `INACTIVE_REFERENCE` (parent is off), 422 `VALIDATION_ERROR`. Show them in plain words. |
| DSH-G06 | The form may check simple things before sending (required, max length, number range) using the API limits. The API is always the final judge. |
| DSH-G07 | "Turn off / Turn on" instead of delete, with a short confirm step on the page (not a browser pop-up). |
| DSH-G08 | Selects for parents (office, building, floor, department, division, position, room type, owner) load from the API and hide inactive items, except the one already chosen. |
| DSH-G09 | After a save, show a short success message and refresh the list. |
| DSH-G10 | Empty list: say what is missing and show the "Add" button. Loading: show a skeleton, not a spinner over the whole page. |

## 10. Pages, in build order

### Phase 1: Sign-in, layout, profile

DSH-A01 to DSH-A09, the sidebar, the top bar with the user's name and sign out.

### Phase 2: Rooms

| ID | Requirement | API |
| --- | --- | --- |
| DSH-R01 | Room list: name (English + Khmer), room type, place (office, building, floor), capacity, owner, private label, active, bookable. Filters: province, office, building, floor, room type, min capacity, equipment, owner, has owner, active, bookable, private. | `GET /rooms` |
| DSH-R02 | Room detail: all fields, photos, equipment. | `GET /rooms/{id}` |
| DSH-R03 | Create room: English and Khmer name, office → building → floor, room type, capacity (1–10000), size in m² (optional), opening and closing time (`HH:MM`, opening before closing), short description, description, door code, owner (users with Room owner role, or none), private. | `POST /rooms` |
| DSH-R04 | Edit room, turn off/on. Turning on is refused if its floor is off. | `PATCH /rooms/{id}` |
| DSH-R05 | Door code: hidden; a "Show door code" button calls the API and shows it. | `GET /rooms/{id}/door-code` |
| DSH-R06 | Photos: upload (JPEG, PNG or WebP, max 5 MB, max 20), drag to reorder, delete. The first photo is the cover. | `POST/PUT/DELETE /rooms/{id}/photos…` |
| DSH-R07 | Equipment: choose from the equipment list; inactive items can stay but cannot be added. | `PUT /rooms/{id}/equipment` |
| DSH-R08 | After creating a room, the page moves to its photos and equipment steps. | — |

### Phase 3: Places

| ID | Requirement | API |
| --- | --- | --- |
| DSH-P01 | Provinces: read-only list used in selects. | `GET /provinces` |
| DSH-P02 | Offices (locations): list, create, edit, turn off/on. Province, address, map text. | `/locations` |
| DSH-P03 | Buildings: list by office, create, edit, move to another office, turn off/on. | `/buildings` |
| DSH-P04 | Floors: list by building or office, create, edit, move, turn off/on. | `/floors` |
| DSH-P05 | Show a warning before turning off an office, building or floor: its rooms become not bookable. | — |

### Phase 4: Room types and equipment

| ID | Requirement | API |
| --- | --- | --- |
| DSH-C01 | Room types: list, create, edit, sort order, turn off/on. | `/categories` |
| DSH-C02 | Equipment: list, create, edit, sort order, turn off/on. The icon field holds a Lucide icon name; the form shows a picker with a preview. **(my call)** | `/equipment` |

### Phase 5: Organisation

| ID | Requirement | API |
| --- | --- | --- |
| DSH-O01 | Departments: list by office, create, edit, move, turn off/on. | `/departments` |
| DSH-O02 | Divisions: list by department, create, edit, move, turn off/on. | `/divisions` |
| DSH-O03 | Positions: list, create, edit, turn off/on. | `/positions` |

### Phase 6: Users and roles

| ID | Requirement | API |
| --- | --- | --- |
| DSH-U01 | User list: name, staff ID, email, division, position, province, roles, active, last sign-in. Filters: division, department, position, role, province, active. | `GET /users` |
| DSH-U02 | Create user: all fields and a temporary password (with a "Generate" button). The new user has no roles. | `POST /users` |
| DSH-U03 | Edit user, turn off/on. If rooms lost their owner, show the room list from `rooms_unassigned`. | `PATCH /users/{id}` |
| DSH-U04 | Roles: tick the roles. Pitika, IT Lead and IT Staff need a division; warn before saving. | `PUT /users/{id}/roles` |
| DSH-U05 | Reset password: Admin types or generates a temporary password. | `POST /users/{id}/reset-password` |
| DSH-U06 | Signature: upload, see, remove. The image needs a token, so load it with `fetch` and show it from a blob URL. | `/users/{id}/signature` |
| DSH-U07 | Roles page: the 6 roles; only the English and Khmer names can change. | `GET /roles`, `PATCH /roles/{id}` |
| DSH-U08 | The Admin cannot turn themselves off or remove their own Admin role; the buttons are disabled with a short reason. | — |

## 11. Done means

- Every page in phases 1–6 works against the real API, with the API errors shown in the right place.
- No door code and no password appear in any list, log or page unless asked for.
- Types come from `openapi.json`, with no hand-written copies of API shapes.
- Lint and type check pass (`vue-tsc`), and the main flows have tests (Vitest for logic, Playwright for sign-in and creating a room) **(my call)**.

## 12. Decisions

1. The page order in section 10 is confirmed.
2. The dashboard lives in the same Git repository as the API (`admin_dashboard/`).
3. The **(my call)** items are accepted.
