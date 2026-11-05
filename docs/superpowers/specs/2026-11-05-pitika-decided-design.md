# Pitika "Decided by me": design

Owner decisions, 5 Nov 2026, from mockups the owner iterated on (picked version "G").

## Why

A Pitika approves or rejects a booking, and it leaves To review. Today they cannot find it again
except on Bookings, by date, often without the booking number. The owner's goal: the Pitika's
work is easier, they can find what they decided, and they **feel safe and not stressed** about
how much they did today.

## Goals

- See every booking this Pitika approved or rejected, newest decision first, grouped by day.
- See **where each booking is now** (Room owner next, IT setup, Confirmed, Cancelled, ...).
- Find one quickly: search by title, booking number or booker, filter by room and dates.
- A calm "today" summary: how many I decided today and how many still wait.

## Non-goals

- No undo, no reject after approve, no cancel by the Pitika. The rules stay as they are
  (BR-CAN-01: only the booker cancels; an Admin can too). The decided list is **read only**.
- No list of other Pitikas' decisions. This is "by me" only.
- No change to the Waiting list itself (urgency groups, photos, row bar stay as built).

## Anti-goals

- A busy, stressful screen: many lines, red everywhere, big warnings. The owner asked for
  "modern and clean": soft cards, more space, few lines.

## The page (version G)

The To review page gets a new head and three tabs. Same route `/review`; the open tab is in the
address (`/review?tab=approved`, `?tab=rejected`; no `tab` = Waiting), so reload and Back keep it.

**Head (all tabs):**
- A small ring (60px) left of the title. Text in the middle: `{decided today}/{decided today + waiting}`,
  e.g. "6/9". The ring fills green for approved today, crimson for rejected today, and stays
  light for waiting. When both numbers are 0 the ring shows "0/0" in light colours.
- Title "To review". Under it one line: "Today you decided 6 · 3 still waiting".
  When nothing waits: "Today you decided 6 · nothing waiting". When nothing is decided yet today:
  "Nothing decided yet today · 3 waiting".
- A segmented switch on the right: **Waiting 3 · Approved 5 · Rejected 1**. Waiting's number is
  every booking waiting in the province now. Approved and Rejected numbers are **today's**
  (Phnom Penh day), matching the line under the title.

**Filters (all tabs, one bar):** search ("Search title, booking number or booker"; matches
title, reference, booker English or Khmer name), room picker (rooms of the province), From / To
date pickers (the **meeting** day, like the Waiting tab and Bookings), Clear when any is set.
Filters stay when switching tabs.

**Waiting tab:** the list as built today.

**Approved / Rejected tabs:** a list of soft cards (white, 12px radius, light shadow, 8px gap),
grouped under small upper-case day heads: "Today · Thu 5 Nov", "Yesterday · Wed 4 Nov", then
"Mon 2 Nov". The day is the **decision** day (Phnom Penh). The head's right side shows the count
of cards under it on this page ("5 approved").

A card:
- A round icon: green ✓ (approved) or crimson ✕ (rejected).
- Title, then the booking number in a small mono chip right after it.
- Second line: room (English) · first meeting day and time · booker name.
- Rejected cards: a third line "Reason: “…”". Approved cards with notes: "Notes: “…”".
- Right side: a soft status pill of where the booking is **now**:
  Room owner next (amber), IT setup (neutral), Confirmed (green), Completed (neutral),
  Cancelled (neutral), Rejected (crimson; on the Rejected tab, and if the room owner rejected
  after the Pitika approved). Then the decision time in mono ("13:38").
- Click or Enter opens the booking panel **read only** (the same details as the review panel,
  no Approve/Reject in the foot, only Close).

**Empty states:** Approved: "No approved bookings yet" / "Bookings you approve show here."
Rejected: "No rejected bookings" / "Bookings you reject show here." With filters set: the usual
"No bookings match" + Clear filters.

**Paging:** 20 cards a page with the existing paging control under the list.

## API

1. `GET /api/v1/pitika/bookings/decided` — Pitika only (same access as `/pitika/bookings`).
   Query: `decision` (`APPROVED` | `REJECTED`, required), `q`, `room_id`, `from`, `to`, `page`,
   `size`. Rows: bookings that have a review with `stage = PITIKA`, `reviewer_id = me`,
   `by_admin = false` and that `decision`. Sorted by that review's `reviewed_at`, newest first,
   then booking id. Each item = `BookingListItem` + `decided_at` (UTC) + `decision_note`
   (the review's notes on approve; the rejection reason on reject). `from` / `to` keep bookings
   with any session in the range (same as the other lists; `to` before `from` → 422).
   Only rooms in the Pitika's **current** province (same rule as `/pitika/bookings` and
   `booking_access.can_view`, B-08), so every card opens with `GET /bookings/{id}` and the
   room picker (province rooms) covers every card. No province → empty list, summary all 0.
2. `GET /api/v1/pitika/bookings/summary` (same router file as the Pitika list) — `{ "waiting": n, "approved_today": n, "rejected_today": n }`.
   `waiting` = PENDING_PITIKA bookings in the Pitika's province (same as the Waiting list total,
   no filters). Today = the Phnom Penh day of now (`clock`).
   The page loads it on open, after every decision, and when the Phnom Penh day changes.

No database change. No new indexes unless a test shows the query is slow
(`booking_reviews` has `booking_id`; a reviewer index can come later).

## Constraints

- One file per resource for schemas, routers and services; one class per model file.
- Tailwind is global: never name a class `grid`, `table`, `flex`, `hidden`, etc.
- Ruff, pytest, vitest, vue-tsc, eslint and Playwright layout checks (1366, 900, 390 px) pass.

## Calls I made (owner can change)

- Tab numbers for Approved/Rejected are today's, not all time.
- Date filters mean the meeting day, not the decision day (same as everywhere else).
- Decisions an Admin made as a backup are not in "my" list.
- Only rooms in the Pitika's current province, like every other Pitika list. If a Pitika moves
  province, their old decisions are not shown (rare; keeps the B-08 view rule unchanged).
- The summary counts use the same rules as the list (`by_admin = false`, current province).
- A booking has at most one PITIKA review (it cannot come back to PENDING_PITIKA), so it shows
  once, on one tab.
- The read-only panel head says where the booking is now (e.g. "Confirmed · NBC-26-…") and
  shows no "expires" note.

## Left to the builder

Component split, query shape, test names, how the ring is drawn (SVG or conic gradient), exact
spacing inside the design tokens.
