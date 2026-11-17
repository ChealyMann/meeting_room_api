# Room availability (Pitika): design

Owner decisions, 17 Nov 2026, from the demo the owner approved
(https://claude.ai/artifact/LTgYrFA6PZAtNPe4NL2dhb, version 2), after the mockup's Room
availability page (`frontend_mockup/.../js/views/approver/room-availability.view.js`) "in our
theme".

## Why

A Pitika is asked "is any room free at 2 pm?" and today has to open Bookings and work it out.
They also check a waiting booking against the room's day, and when they reject they want to say
which room is free instead. One look at every room's day answers all three.

It is a second tool: approving still lives in To review. The page must not crowd the screen
(the owner rejected summary cards above lists twice: the Food list's "To prepare" card, and the
4-number strip of this page's first demo).

## Goals

- One page, **Room availability**, in the Daily menu under Food list, for PITIKA and ADMIN.
- Every room of the Pitika's province (Admin: every active room), one row each, hours across.
- See at a glance what is booked, what waits for approval, what is free, and what is past.
- Answer "free at <time>?" in one step.
- Open any booking the reader may see; approve or reject a booking waiting for Pitika right
  there.

## Non-goals

- No booking from this page; no editing of rooms.
- No week view (one day at a time, with the day buttons).
- No new numbers or summary cards.
- No backend change.

## The page

Same frame as the Food list:

1. **Head:** `Room availability` + the day in mono, and the refresh button.
2. **Day buttons:** Previous day · Today · Next day, and the date picker. The day lives in the
   address (`?date=2026-11-18`; none = today in Phnom Penh), like the Food list.
3. **Filters, one row:** **Free at** first (green box; Any time · Now · 07:00 … 17:30 every half
   hour; default Now on today, Any time on other days), then search (room name in English or
   Khmer, floor, building), Shared and private / Shared rooms / Private rooms, All buildings /
   one building, and Clear filters when anything differs from the default.
4. **Result line** (only with Free at set): "9 of 14 rooms free at 14:00".
5. **The sheet:** a header row (Room · Kind · 07:00 … 17:00), then one row per room:
   - the room's cover thumbnail, name in English with the Khmer name, and floor · building ·
     seats; with Free at set and the room free: "Free until 16:00" or "Free for the rest of the
     day" in green;
   - Shared (globe) or Private (lock);
   - the lane, 07:00 to 18:00 to scale: a light green lane, hour lines, the room's bookings as
     blocks, the past hatched (today only), a red Now line (today only, with a "Now 10:20" tag in
     the header), and a green line at the Free at time when it is not Now.
6. **Legend:** Free · Booked · Waiting for approval · Past.

Rows: by building and room name; with Free at set, rooms free at that time come first (free the
longest first) and the others fade (opacity about 0.5).

## Blocks

- From `GET /room-schedule?date=&room_ids=` (one call for every room in view).
- **Booked** (CONFIRMED, SETUP_IN_PROGRESS): red tint. **Waiting** (PENDING_PITIKA,
  PENDING_OWNER): amber tint with a dashed edge. **Masked** (a private booking the reader may
  not see): grey, "Private booking", not clickable.
- A block shows its title and times, cut with an ellipsis when short.
- **Hover or keyboard focus:** a dark tooltip with the title, the times, the booker and, when
  waiting, "Waiting for Pitika" / "Waiting for room owner".
- **Click:**
  - waiting for Pitika, read by a Pitika: the To review panel (`ReviewPanel`) with Approve and
    Reject, through the same confirm pop-up as To review (`BookingActionDialog`; reject needs a
    reason of 5 characters or more). After a decision: a toast, the panel closes, the day
    reloads.
  - anything else: the booking drawer of the Bookings page (`BookingPanel`; the Admin's actions
    only for an Admin), like the Food list.
  - the open booking lives in the address (`?booking=ID`), so a reload keeps it.

## Free at

A room is free at time *t* when *t* is within its opening hours (`start_time` ≤ *t* <
`end_time`) and no block covers *t* (a block covers [start, end)). It stays free until the next
block's start or the room's closing time, whichever comes first. "Now" is the Phnom Penh clock,
checked every 20 seconds.

## Data and refresh

- Rooms: `listAllRooms` (the room list the Pitika's To review already loads), kept to the
  Pitika's province (`user.province`), active rooms only.
- The day: `getDaySchedule(day, roomIds)`, again on the live refresh (every 15 s, quiet).
- Errors: the list page's load error with Try again, as on the Food list.

## Left to the builder

Component split, CSS details, empty and loading states (a skeleton like the Food list; "No room
matches these filters." with Clear filters), and test names.
