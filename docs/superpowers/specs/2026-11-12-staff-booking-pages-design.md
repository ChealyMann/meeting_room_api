# Staff booking pages in the dashboard — design

Date: 12 Nov 2026. Status: approved by the owner (12 Nov 2026), with public holidays as a warning.

## Why

Staff book rooms today only in `frontend_mockup/`, which is a mockup with fake data. The owner wants
staff to book in the real system: same login as Pitika, room owners and IT, real API, real data.
The look was chosen over many rounds of demos (12 Nov 2026): **Design 1 "Calm"** with the
**Soft fields** form, the **4-step booking with the week table**, Food & IT **grouped with search**,
and **review tiles**. The demo that shows every screen and interaction is kept at
`.superpowers/staff-new-site/` (git-ignored; serve the folder and open `index.html`), with its source in
the session scratchpad. Treat the demo as the visual and behaviour reference.

Success: a staff member signs in, finds a room, books one or several sessions with food and IT,
sends it, and sees it in My bookings with its status, door pass and cancel, all against the real API,
looking like the demo inside the dashboard.

## Goals

- Staff pages inside `admin_dashboard/` (Vue 3 + TS + Vite), in the same shell: the crimson
  **sidebar** stays (owner decision: "dashboard with the sidebar").
- Sidebar: a **Find a room** and a **My bookings** item for everyone with the `STAFF` role. Pitika,
  room owners and IT staff also have `STAFF`, so they see them too.
- A Staff-only user, who today lands on **No access**, lands on **Find a room**.
- Pages: Find a room · Room details · Book (4 steps) · My bookings (+ booking details, door pass,
  cancel, add to calendar).
- All data from the API; the API's own rules and error messages decide what is allowed.
- Light and night theme, phone sizes, keyboard use, reduced motion, as the rest of the dashboard.

## Non-goals

- Editing a sent booking (the API has `PATCH /bookings/{id}`; not in this design).
- Changing how Pitika, owners, IT or Admin pages look.
- The old mockup: it stays as it is and is not used.
- New approval rules. The approval path comes from the API (`POST /bookings/check`).

## Anti-goals (would be a failure even if it works)

- Showing a choice the API will refuse (a busy or past time, a closed day, more seats than the room has).
- Saving something different from what the screen showed (for example servings).
- Boxy, crowded screens. The owner rejected many demos for "too many boxes", "massive scrollbar",
  red borders that look like errors, and extra helper text. Keep the demo's calm: white space, soft
  surfaces, one accent (crimson) only for the main button and what was picked.

## Pages (from the demo)

**Find a room.** Title "Find a room", today's date and room count. Filters: search (name or
equipment), building, Shared / Private, "Free now". Photo cards (4:3, rounded), name, Khmer name,
seats · floor · main equipment, a live line "Free until 14:00" / "In use until 15:30" / "Free all day",
a "Private" tag on private rooms. Each card has **Details** and **Book** (shared) or **Request** (private).
Book/Request opens the booking on the week table with nothing picked.

**Room details.** The photo fills the page (photos fade, dots, arrows on hover), name, Khmer name,
facts, equipment with icons on the photo. A floating white card "Book a time": day strip (next 7
working days, from today), "How long" (30 min · 1 h · 1 h 30 · 2 h · 3 h), only the **free start
times** as buttons, then "Continue · 09:00–10:00, Fri 13 Nov", plus "Several days? Pick on the
calendar". Continue opens the booking on the week table with that time already picked.

**Book — step 1 Schedule.** A week table: the next **5 working days from today** (not Monday to
Friday, so past days do not fill it); arrows move 5 working days. Half-hour rows. Click a free cell =
1 hour; press and drag down = any length; several days allowed; touching picks join; click a picked
block (or × in the side card) to remove it. Busy grey with "Busy", past striped, closed days shown as
closed; public holidays stay bookable with an amber "Holiday" mark (see calls below). Each day shows
"8 h free". No page scroll on a computer.

**Side card (all steps).** Full height, level with the main pane: room photo on top. Step 1: "Your
sessions" (sticky heading, list scrolls) and a sticky "Total · 2 sessions · 2 h" above the buttons.
Steps 2–3: the real sessions (up to 4 + "n more") with Edit, then People / Food / IT help with icons.
Step 4: "After you send" path starting with "You send it · Now", then the API's steps, then "You can
cancel any time before it starts". Back / Next always visible at the bottom.

**Book — step 2 Meeting details (Soft fields).** Grey fields with a floating label inside; icon on the
left; the field being typed in turns white with a dark outline (red only for real errors). Fields:
Meeting title (0/80 counter while typing) · **Meeting type** (new, see below) · People coming
("Up to 24" hint, quick buttons 2 · 4 · 6 · 8 · 10 · 15 · 20 up to the seats, and − / +) · Invite by
email (chips with first letter, Enter or comma adds) · Why this private room (private rooms only;
"Only Pitika and the room owner read this.") · Agenda or notes. "Booked by" row at the bottom.
No heading, no seat meter (owner removed both). Fast − / + clicks must not select text.

**Book — step 3 Food & IT.** Two columns, flat headers (title + "None" / "2 picked", no icon, no
sub-line). Each has a search box (matches the start of words: "tea" must not find "steamed"), × to
clear, "No match" + Clear search. Items grouped under small sticky headings; food groups ordered by
the first session's start time (Breakfast before 10:30, Meals before 13:30, otherwise Breaks & drinks)
**without** a "Good for" label (owner removed it). Click a row to pick; tick circle. Notes for the
kitchen and for IT under each list when something is picked. Food shows "× 8 · served at 09:00".

**Book — step 4 Review & confirm.** One full-height card: room row (photo, names, Private pill); a big
time block with a date tile (FRI 13 NOV) and "12:00–13:00 · Friday 13 Nov · 1 h", or "N sessions"
with chips; click = back to step 1. Four tiles you click to change: Meeting · Food & drinks · IT help ·
Why this room / Notes, each with a quiet pencil. Booked by at the bottom. Send request in the side card.

**My bookings.** "Coming up" / "Past & cancelled" tabs with counts, "Book a room" button. Cards: date
block (THU 12 NOV), room photo, title, time (+n more), room, status pill, "Door pass" when confirmed.
Click opens a details window: photo, status, progress track (Sent · Pitika · Room owner · IT setup ·
Confirmed, from the API), times, people, food, IT, notes; Cancel booking (confirm dialog), Door pass
dialog (code + Copy), Add to calendar (the API's calendar file).

## Decisions taken with the owner

1. **Inside the dashboard with the sidebar**; same login.
2. **Meeting type** (API requires one of 4 values): a choice **Internal / External** plus a switch
   **"The Governor attends"** → INTERNAL, EXTERNAL, INTERNAL_WITH_GOVERNOR, EXTERNAL_WITH_GOVERNOR.
   Place: on step 2 under the title (builder's call on exact look; Soft-field style).
3. **No food numbers** (API rule B-25, owner decision 17 Nov 2026): no servings stepper and no "× {people}"; only the package names.
4. **Food and IT groups and icons come from the API**: add `group` and `icon` to catering packages and
   IT services, set by the Admin in the Service catalog page (reuse the Equipment icon picker).
   Groups — food: Breakfast, Meals, Breaks & drinks; IT: Screens & video, Sound & language,
   Devices & network, Support. No group = "Other", shown last. Existing rows start with no group.
5. **One new endpoint** for the room cards: every room's busy times for one day, with the same
   private-room masking as `GET /rooms/{id}/schedule`, so a page of cards needs one request and
   "Free now" is right across the whole list (not only loaded cards).

## Calls I made (owner can overrule)

- Week table rows and "Free until" use each **room's own hours** (`rooms.start_time`/`end_time`), not a
  fixed 08:00–18:00.
- **Public holidays are a warning, not closed** (owner decision, 12 Nov 2026; the API already answers a
  holiday with a `PUBLIC_HOLIDAY` warning in `POST /bookings/check`, not a problem). The day still
  books normally. Show it softly in amber: the table's day head says "Holiday" with the name on hover;
  the room page's day strip marks it; a picked session on a holiday gets a small amber note in the side
  card ("Fri 13 Nov is Khmer New Year"); Review shows the API's holiday warnings above the tiles. Holidays
  come from `GET /public-holidays`.
- Before Send, call `POST /bookings/check`; its `steps` feed "After you send", its `problem` shows on the
  step it belongs to, and Send stays off while the check has a problem. API errors on `POST /bookings`
  show next to the field they name (`fields`), else as a message above the buttons.
- Session limits, weekends, how far ahead, lead time: whatever the API answers; the UI does not invent
  its own rules beyond hiding obviously impossible choices (past, busy, closed).
- Sidebar: the two Staff items go first in the "Daily" group ("Find a room", "My bookings"), above the
  role items. Staff-only home = Find a room.
- Look: use the dashboard's existing colour tokens, fonts, night theme and focus ring; build the Calm
  pieces (photo cards, soft fields, tiles, week table) as dashboard components. Where the dashboard's
  DESIGN.md rules (open sheets, no rounded cards) conflict with the chosen Calm look, the Calm look wins
  for the Staff pages only, and DESIGN.md gets a "Staff pages" section saying so.
- Motion follows the demo (Emil Kowalski's rules, as elsewhere in the dashboard): press scale 0.97,
  named transitions, under 300 ms, nothing on reduced motion.
- Booking draft lives in the page (and the address for room id and step); leaving the flow drops it.

## Left to the builder

Component split, store shape, query caching, exact endpoint path and response shape for the
one-day availability endpoint, migration details for `group`/`icon`, test layout (API tests in
`tests/`, Vitest unit tests and Playwright e2e in `admin_dashboard/`), and the order of work.

## Constraints

- API: FastAPI + SQLAlchemy + Alembic (MySQL), pip + requirements files. Dashboard: Vue 3, TS, Vite,
  Pinia, Vitest, Playwright, generated `src/api/schema.d.ts` (regenerate after API changes).
- One class per file for models; one file per resource for schemas, routers, services.
- Don't run pytest and Playwright at the same time (CPU load breaks the panel-motion test).
- Commits and PRs without Claude attribution lines (owner rule); work on a feature branch; PRs are
  opened via the GitHub API (no `gh`); the owner merges.
