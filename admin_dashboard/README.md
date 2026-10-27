# NBC Meeting Rooms · Admin dashboard

The admin dashboard for the meeting-room booking API in this repository.
Vue 3 (Composition API, `<script setup>`), TypeScript, Vite, Pinia, Vue Router, Tailwind CSS 4.

Phase 1 has: sign-in, the first password change, Admin-only access, the app shell, and My profile (with my photo and signature).
Phase 2 has: Rooms — the list with filters and paging, room detail, create and edit, the Active switch, door code on request, photos and equipment.
The design rules are in [`../DESIGN.md`](../DESIGN.md).

## Setup

You need Node.js 22.18+ (or 24.12+) and the API running (`run.bat` in the repository root).

```sh
npm install
cp .env.example .env.local   # VITE_API_URL=http://localhost:8000
npm run dev                  # http://localhost:5173
```

The API must allow this origin. In the API `.env`:

```
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## API types

`src/api/schema.d.ts` is made from the API's OpenAPI document. Run this after the API changes (the API must be running):

```sh
npm run gen:api
```

## Tests and checks

```sh
npm run test:unit -- --run   # unit tests (Vitest)
npm run type-check
npm run lint
npm run build
```

End-to-end test (Playwright, Chromium). It needs the API running and an Admin account whose password is already changed. Without the two variables it is skipped.

```sh
npx playwright install chromium   # first time only
E2E_ADMIN_EMAIL=admin@company.com E2E_ADMIN_PASSWORD='...' npm run test:e2e
```

The test changes the account's phone, checks it after a reload, then puts it back.

## Rooms

- The list's filters, page, page size and status live in the address (`/?location_id=3&search=board&page=2`), so a filtered list can be reloaded or shared.
- The open room lives in the address too: `?room=12` (detail), `?room=12&edit=1` (edit), `?room=new` (create), `&step=photos|equipment` (the steps after creating a room).
- The door code is never loaded with a room; "Show door code" asks the API for it.
- The real-API test for rooms (`e2e/rooms.spec.ts`) needs at least one active office with a building, a floor, a room type and an equipment item.

## Places

- Offices (`/offices`), Buildings (`/buildings`) and Floors (`/floors`) work like Rooms: filters, page and status live in the address, and the open record is `?id=3` (edit) or `?id=new` (create).
- An office is a "location" in the API. Buildings and floors only carry their parent's id, so the lists look up the office and building names; a parent the list cannot find shows as `#id`.
- Changing a building's office moves the building with its floors and rooms; changing a floor's building moves the floor with its rooms.
- Every record panel has an "Active" switch in its foot. Making a record inactive first counts the active rooms inside and says how many stop being bookable; making it active does not ask. The API refuses to make a building or floor active while its parent is inactive, and the panel shows why.
- The real-API test for places (`e2e/places.spec.ts`) adds an office, a building and a floor with unique names each run, and leaves them on.

## Catalog

- Room types (`/room-types`) and Equipment (`/equipment`) work like the place pages: search and status in the address, `?id=2` (edit) or `?id=new` (create), and a saved record loads before its panel opens.
- The API searches room types by English and Khmer name, and equipment by name; there are no other filters.
- Making a room type or an item inactive leaves rooms as they are (still bookable); it only stops it being chosen for other rooms. The warning counts the active rooms that use it.
- An item's icon is a Lucide name from the picker's list in `src/utils/equipmentIcons.ts`. A name not on that list (set elsewhere) is kept and shown as "Unknown icon"; add it to the list to show it.
- The real-API test for the catalog (`e2e/catalog.spec.ts`) adds a room type and an item with unique names each run, and turns the item off.

## Organisation

- Departments (`/departments`), Divisions (`/divisions`) and Positions (`/positions`) work like the other record pages: filters in the address, `?id=3` or `?id=new`, and a saved record loads before its panel opens.
- The API filters departments by office and divisions by department only; the department select is grouped by office so the right one is easy to find.
- Moving a department to another office moves the province of every user in its divisions (the API does it).
- Making a department, division or position inactive changes nobody; it only stops new divisions or users from using it. The warning counts the active users (`GET /users`, Admin only).
- The real-API test (`e2e/organisation.spec.ts`) adds a department, a division and a position with unique names each run, and turns the position off.

## People

- Users (`/users`) filter by role, department, status and search on the first row; division, position and province sit under "More filters". All of them live in the address.
- The open user is `?id=7`, with `&tab=roles`, `&tab=password` or `&tab=signature` for the other tabs; `?id=new` creates one. A new user has no roles, so their panel then opens on the Roles tab.
- The temporary password (create, or the Password tab) is never kept: not in the address, a draft, a toast or a log. "Generate" makes a 14-character one; "Copy" puts it on the clipboard.
- Setting a temporary password signs the user out everywhere, and they must choose a new one when they next sign in.
- The user panel stays open after a save. Making a user inactive, or taking away Room owner, clears the rooms they own; the panel lists them with links to each room.
- Pitika, IT Lead and IT Staff need a division: choose one on the Details tab, then tick the role.
- You cannot make yourself inactive or remove your own Admin role. The API also refuses to remove the last Admin.
- Roles (`/roles`) are the six fixed roles. Only their Khmer and English names can change; the counts are active users with each role.
- The real-API test (`e2e/people.spec.ts`) adds a user with a unique staff ID and email each run, gives them Staff and sets a temporary password. It needs at least one active position.

## How sign-in works

- **Access token:** in memory only. It lasts 15 minutes.
- **Refresh token:** in `sessionStorage` (`nbc.admin.refresh`), so a reload keeps you signed in and closing the browser signs you out. Nothing goes to `localStorage`.
- When a call gets 401, the app refreshes the token once and repeats the call. Calls that fail at the same time share one refresh. If the refresh is refused, you go to sign-in and come back to the same page after.
- A user with `must_change_password` can open only the "Choose a new password" page.
- A user without the `ADMIN` role sees "You do not have access" and a Sign out button.
- Unsaved profile changes are kept in memory while you sign in again.
- Times from the API are UTC; the dashboard shows Phnom Penh time.
