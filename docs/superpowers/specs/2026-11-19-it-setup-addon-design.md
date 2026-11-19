# IT setup as an add-on: design

Owner decision, 19 Nov 2026 (demo look **F · IT setup after Confirmed**).

## Why

IT cannot stop a booking: IT has no reject, and when nobody marks a setup ready the expiry job
confirms the booking at its start anyway (T17). So the IT step only **delays** the confirmation:
the booker waits with no door pass and a "Tentative" calendar file for something that cannot say
no. From now on the booking is **confirmed as soon as the last reviewer approves**, and the IT
setup runs beside it.

## Goals

- The last approval (Pitika, or the room owner on R2) confirms the booking at once: status
  `CONFIRMED`, door pass, confirm time, the request slip's signers, exactly as a booking without
  IT. A booking with IT help also sends its ticket to IT at that moment (`forwarded_at`).
- The IT flow stays as it is: the IT Lead sees the ticket in **To assign**, assigns staff,
  **Mark ready**; IT Staff see it in **My tasks**; missed setups go to **Ready** as missed.
- **Mark ready** marks only the setup (`ticket.status = READY`, `ready_at`) and moves the
  booking's version on; it no longer changes the booking's status or door pass.
- The booker sees IT as a **fourth step after Confirmed** (look F):
  `Sent · Pitika (· Room owner) · Confirmed · IT setup`. The step uses the step bar's own colours:
  amber while IT works (Sent to IT, Setting up), green when the room is ready, **crimson only when
  IT missed it** (not marked ready before the meeting started). The line under the bar says
  "Step 3 of 4" and, on the right, "IT setup · Setting up" (clock), "Room ready" (circle check) or
  "IT setup · Not marked ready" (triangle); a click opens the Food & IT tab. The green band
  "Confirmed · the room is yours" stays on top.
- History's process bar gets the same fourth circle; its timeline is in time order, so
  "Confirmed · door pass ready" now comes before "Sent to IT", "Staff assigned" and "IT ready".

## Non-goals

- No way for IT to refuse a setup (unchanged: IT never could).
- No new email or notification when IT is ready (there are none today).
- No change to the IT pages' tabs, rows, buttons or the assign pop-up, apart from the words below.

## Anti-goals

- The IT step must never look like it blocks the booking: never crimson while IT simply works.
- The booker must never lose a door pass or a confirmed status because of IT.

## What changes

### API

1. `after_last_review`: with an IT ticket, confirm the booking (`make_confirmed`) **and** set
   `forwarded_at`; without one, confirm as today. `forward_it` (status `SETUP_IN_PROGRESS`) is no
   longer used for new bookings.
2. `mark_ready`: allowed on a `CONFIRMED` booking whose setup is `ASSIGNED` with active staff,
   **before the meeting starts** (after the start the setup is missed and cannot change, as
   today); it sets the ticket Ready and moves the version on (`advance`), nothing else.
3. Assign / change staff on a confirmed booking: allowed while the setup is not Ready and the
   meeting has not started (new), and still while later sessions remain (as today).
4. Legacy rows: a booking already in `SETUP_IN_PROGRESS` when this ships keeps working the old
   way (Mark ready confirms it; the expiry job confirms it at the start). A one-off script,
   `scripts/confirm_it_setup_bookings.py`, confirms them all now with `make_confirmed`
   (my call: the owner's earlier pick "move them to Confirmed when this goes live").
5. The `SETUP_IN_PROGRESS` status stays in the enum for those rows and old data; nothing new
   enters it.
6. Files (`ATTACHMENTS_OPEN`): unchanged list; since a booking with IT is now confirmed at the
   last approval, its files lock then, like any confirmed booking (my call).

### Dashboard

1. `buildHistory` (`utils/bookingHistory.ts`): the IT step moves after Confirmed. Its state:
   `done` when `it.ready_at`; `stop` when the booking is confirmed, the setup is not ready and the
   first session has started (missed); `now` while confirmed and waiting; `todo` before the
   booking is confirmed. Legacy `SETUP_IN_PROGRESS` rows: IT `now`, Confirmed `todo`, as today.
   A cancelled booking keeps only the steps it reached (unchanged rule).
2. `StepProgress`: the booker's panel shows the IT words on the right while the IT step is the
   one that is not done, and a click on them opens Food & IT (look F). Other panels keep their
   labels.
3. IT help card (`BookingServices`): the pill also shows "Not marked ready" (crimson) for a missed
   setup; "Setting up" / "Sent to IT" / "Room ready" as today, now also on a confirmed booking.
4. Words:
   - Pitika / room owner approve pop-up: "It is confirmed, with a door pass. IT gets the setup
     to do." (+ "The food is approved with it.").
   - The review row's "Next:" for a booking with IT: "Confirmed".
   - Mark ready pop-up: "The room is ready for the meeting. The booking is already confirmed."
   - A missed setup on the IT pages: unchanged "Missed · not marked ready".

## Constraints

- One branch, stacked on `feature/holiday-booker-contact` (both change the review page).
- TDD: every rule above gets a failing test first. Backend `pytest`, dashboard `vitest`,
  `vue-tsc`, lint.
- Owner rules kept: no status dots (icon + word), no food numbers, no Claude attribution.

## Left to the builder

- Exact test names and where each test lives.
- Whether the legacy script is also safe to run twice (it must be: it only touches
  `SETUP_IN_PROGRESS` rows).
