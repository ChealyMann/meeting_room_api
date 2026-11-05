# Room owner and IT pages in the admin dashboard: design

Owner decisions, 5 Nov 2026. "I want like Pitika": both roles get pages built the same way as
the Pitika's To review (`2026-11-05-pitika-review-design.md`) and its "Decided by me" tabs
(`2026-11-05-pitika-decided-design.md`). Read those first; this spec only says what differs.

## Why

The Room owner and the IT team still work outside the dashboard. The goal is the same as for
the Pitika: their work is easier, they see what is urgent first, they can find what they did,
and they feel safe and not stressed about the day.

## Goals

- **Room owner:** decide bookings of their private rooms (after the Pitika) from one queue,
  most urgent first, seeing what an owner checks; find what they decided; see every booking in
  their rooms.
- **IT Lead:** see every IT setup, pick IT Staff for each one, mark it ready; most urgent first.
- **IT Staff:** see the setups they are assigned to, by day, with what to set up and where.

## Non-goals

- No new booking rules. No undo, no reject after approve, no cancel (BR-CAN-01). No IT Staff
  action (only the IT Lead marks ready, T11).
- No calendar view. The owner's Bookings list is the "all bookings in my rooms" view.
- No Food list for owners or IT.

## Anti-goals

- A busy, stressful screen. Same "modern and clean" look as the Pitika pages: soft cards,
  space, few lines, red only for what is late or over.

## Delivery

Two parts, two PRs, in this order: **A. Room owner**, then **B. IT**. Each part works alone.

## Shared: roles, menu, home

- `DASHBOARD_ROLES` becomes `ADMIN, PITIKA, ROOM_OWNER, IT_LEAD, IT_STAFF`. Staff only (no other
  role) still sees "No access".
- Home (first page after sign-in), first match wins: Admin → Rooms; Pitika → To review;
  Room owner → owner To review; IT Lead → IT setup; IT Staff → My tasks.
- Menu ("Daily" group), each item only for its roles:
  - Pitika: To review, Bookings, Food list (as today).
  - Room owner: **To review** (route `owner-review`, `/owner-review`), **Bookings**.
  - IT Lead: **IT setup** (`it-setup`, `/it-setup`). IT Staff: **My tasks** (`my-tasks`, `/my-tasks`).
  - A user with several roles sees every item. When a user is Pitika **and** Room owner, the
    owner item is labelled **My rooms** (so there are not two "To review"). Bookings shows once.
- The rail subtitle names the first dashboard role in the home order ("Room owner", "IT Lead",
  "IT Staff").
- The menu count badge (crimson) works like the Pitika's: waiting for me now. Room owner:
  `waiting`; IT Lead: `to_assign`; IT Staff: the My tasks total.

## Part A: Room owner

### To review (`/owner-review`)

The Pitika page with these differences:

- **Waiting:** `GET /owner/bookings?status=PENDING_OWNER` (all on one page, like the Pitika's
  queue), grouped Today / Tomorrow / This week / Later by the first session's day. Same row:
  room photo, reference, title, Khmer · English room, day and time, booker, people.
- **What to check** labels on a row (from the booking detail):
  - "Private · reason given" (crimson) with the reason in the panel, or "Private · no reason".
  - "With Governor" when the meeting type is `INTERNAL_WITH_GOVERNOR` or `EXTERNAL_WITH_GOVERNOR`.
  - People vs seats: "25 people · 20 seats", crimson when people > the room's capacity, plain
    otherwise. Capacity comes from the rooms list.
  - "Pitika notes" when the Pitika's approval has notes (the text shows in the panel).
  - No food or IT labels (not the owner's job); the panel still shows Food and IT help.
- **Row bar ("gap is you"):** Sent ✓, Pitika ✓, then the dashed gap (the owner's decision, no
  owner circle), then IT setup when IT help was asked, then Confirmed.
- **Panel:** as the Pitika's review panel; subtitle "Waiting for room owner"; a note on amber
  wash with the Pitika's notes when there are some ("The Pitika wrote: “…”").
- **Approve / Reject:** the same Ledger pop-up. Approve: notes optional (≤1000), what happens next
  ("It goes to IT setup next." / "It is confirmed, with a door pass."). Reject: reason 5–1000
  characters, Reject off until 5. Calls `POST /owner/bookings/{id}/approve|reject`.
- **Head, ring and tabs:** exactly the Pitika's (ring "6/9", "Today you decided 6 · 3 still
  waiting", Waiting · Approved · Rejected, filters kept across tabs).
- **Approved / Rejected tabs:** the Pitika's decided cards, from the owner's own decisions.
- **Filters:** search, room picker (**only the rooms this user owns**), From / To (meeting day).

### Bookings (owner)

The existing Bookings page, fed by `GET /owner/bookings` (every status) for a user whose only
list role is Room owner. Filters: search, status, room (my rooms), From / To. Read only, no
Admin actions. Order of sources when a user has several roles: Admin list, else Pitika list,
else owner list.

### API (Part A)

1. `GET /owner/bookings` gains `from` / `to` (any session in the range; `to` before `from` → 422),
   like the Pitika list.
2. `GET /owner/bookings/decided?decision=APPROVED|REJECTED` (+ `q`, `room_id`, `from`, `to`,
   `page`, `size`): bookings with a review `stage = OWNER`, `reviewer_id = me`,
   `by_admin = false`, in rooms the user owns **now** (same rule as the owner list), newest
   decision first; item = `DecidedBookingItem` (same schema as the Pitika's).
3. `GET /owner/bookings/summary` → `{ waiting, approved_today, rejected_today }`, same rules
   (Phnom Penh day; waiting = PENDING_OWNER in my rooms).

## Part B: IT

### IT setup (`/it-setup`, IT Lead)

- **Missed setup** (owner, 5 Nov 2026): a ticket not Ready whose meeting has already started
  (the expiry job confirms the booking at the start, T17, and the ticket can no longer change).
  Missed tickets leave To assign and In progress and show on the **Ready** tab with a crimson
  "Missed · not marked ready" pill and no buttons.
- **Tabs:** **To assign** (ticket `RECEIVED`, not missed) · **In progress** (`ASSIGNED`, not
  missed) · **Ready** (`READY`, plus missed). Tab numbers: To assign and In progress = all of
  them now; Ready = made ready today. To assign and In progress load on one page (like the
  Pitika queue); Ready is paged, 20 a page.
- **Head ring:** today's setups (setup day = today in Phnom Penh): ready / all. Line:
  "Today 4 of 6 setups ready · 2 to assign" (when nothing is due today: "No setups today ·
  2 to assign"; nothing at all: "No setups today · nothing to assign").
- **To assign / In progress:** grouped Today / Tomorrow / This week / Later by the **setup day**,
  earliest setup first. Ready: grouped by the day it was made ready (a missed one: its meeting
  day), newest first.
- **Row:** room photo, reference, title, Khmer · English room, building · floor; **"Set up by
  07:30"** (setup time) and the meeting start; the IT items as labels; special needs (one line,
  full in the panel); the assigned staff as small name chips (none: "No staff yet").
  Today and not ready: a crimson "Starts in 1 h 20 min" pill (from the meeting start).
  Buttons: To assign → **Assign staff** (primary). In progress → **Change staff** (quiet) and
  **Mark ready** (primary). Ready → none.
- **Panel** (click a row): photo header, the booking's full process bar (loaded with
  `GET /bookings/{id}`, which the IT Lead and assigned IT Staff may read), Setup (day, time,
  items, special needs, technician notes, staff), Meeting (when, room, people, booker).
  Foot: Close, plus the row's buttons.
- **Assign staff pop-up** (Ledger style): a searchable multi-pick of active IT Staff (at least
  one), technician notes optional (≤1000), the current staff pre-picked. Saves with
  `PUT /it/tickets/{id}/staff` (`user_ids`, `technician_notes`, `version` = the booking's).
- **Mark ready pop-up:** "Mark this setup ready?", "The booking is confirmed and the booker gets
  the door pass." Calls `POST /it/tickets/{id}/ready`.
- Refusals (409 stale, wrong status, inactive staff) show in the pop-up and the list reloads.
- **Filters:** search (title, reference), From / To (**setup** day).

### My tasks (`/my-tasks`, IT Staff)

- The setups assigned **to me** that are not ready and not missed
  (`GET /it/tickets?state=in_progress&mine=true`; also right for a user who is IT Lead and IT
  Staff), grouped Today / Tomorrow / This week / Later by setup day, earliest first, one page.
  Same row as the Lead's, no buttons, no ring, no tabs.
- Head: "My tasks" and one line "3 setups to do · next: today 07:30, Mekong Room".
- Click opens the same panel, read only (Close only).
- Empty: "Nothing to set up" / "Setups assigned to you show here."

### API (Part B)

1. `GET /it/tickets` gains `from` / `to` (setup day range; `to` before `from` → 422),
   `state` (`to_assign` | `in_progress` | `done`, the three tabs, missed rules above; `done` is
   sorted newest first by ready time, or meeting start for a missed one), and `mine=true`
   (only tickets with me as assigned staff). Each item gains `missed: bool`. The old `status`
   filter stays.
2. `GET /it/staff` (IT Lead only): active IT Staff users `{ id, name_en, name_kh }`, by name.
3. `GET /it/tickets/summary` (IT Lead only): `{ to_assign, in_progress, ready_today,
   due_today, due_today_ready }` (Phnom Penh day; to_assign and in_progress leave missed out;
   due_today counts every setup of today, missed included).

## Constraints

- One file per resource for schemas, routers and services; one class per model file.
- Tailwind is global and `main.css` has global classes: never use class names like `grid`,
  `table`, `flex`, `hidden`, `ring`, `border`, `shadow`, `switch`, `sheet`; check new names.
- Days and times in Phnom Penh time. Commit messages with no Claude attribution lines.
- All checks pass: ruff, pytest, vitest, vue-tsc, eslint, Playwright layout checks at 1366,
  900 and 390 px for every new page.

## Calls I made (owner can change)

- Owner rows show no food/IT labels (the panel still shows them).
- A Pitika who is also a Room owner sees the owner page as "My rooms".
- IT gets no separate Bookings page: the three tabs together are every IT setup.
- IT Staff see only setups not ready yet; done ones leave their list.
- The IT ring counts today's setups (ready of all due today), not today's actions.
- IT lists filter by setup day; owner lists by meeting day.
- My tasks shows only my own tickets, also for a user who is IT Lead too (`mine=true`).
- The IT panel loads the full booking (one call) so its process bar is the full one.
- Ready tab: 20 a page, newest first; the other IT tabs on one page.

## Left to the builder

Component sharing between the three queues (reuse the Pitika parts where it keeps them simple),
query shapes, test names, exact copy of empty states not given here.
