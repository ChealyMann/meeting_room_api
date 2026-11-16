# Booking attachments — design

Date: 16 Nov 2026. Branch: `feature/weekends-borders-attachments`.

## Why

When staff book a room, they often have a document that goes with the meeting (an agenda, a
letter, a list of guests). Today there is no place to put it. Pitika, the room owner and IT
then ask for it by chat or email. The owner wants the file to live on the booking itself, so
everyone who checks the booking can open it in one click.

## Goals

- The booker can add files to a booking. It is **optional**: a booking with no file works
  exactly as today.
- **Documents only** for now: PDF, Word (`.doc`, `.docx`), Excel (`.xls`, `.xlsx`).
- Everyone who can already see the booking can open its files (owner decision: "Pitika and the
  room owner and any roles related to the booking process").
- The booker can **add or remove** files while the booking is not yet confirmed. Once it is
  confirmed, the files are locked.

## Non-goals

- No images, slides, zip or other types (maybe later; the type list is one place in code).
- No preview inside the dashboard. A click downloads the file and the computer opens it.
- No virus scanning (no scanner exists on the server today).
- Files are not printed on the request slip and are not sent in emails or the calendar file.
- Nobody but the booker adds or removes files. Pitika, the owner, Admin and IT only open them.

## Anti-goals (it fails even if it "works")

- A person who cannot see the booking can download its file (by guessing a URL or an id).
- A file is served from the public `/uploads` folder.
- A booking can no longer be sent because a file failed to upload.
- A file can still be added or removed after the booking is confirmed (including the race where
  the confirm and the upload happen at the same time).

## Owner decisions (16 Nov 2026)

| Topic | Decision |
|---|---|
| Optional | Yes |
| Types | Documents only |
| Who can open | Everyone who can see the booking |
| Add / remove | The booker, until the booking is confirmed |

**Claude's calls** (proposed in chat, not objected to; the owner can change them):

- PDF, Word, Excel are the "documents"; 10 MB per file; 3 files per booking.
- Rejected and cancelled bookings lock the files too (they will never be confirmed).
- The lock is by status only, not by time: a booking still waiting for IT on the meeting day
  can still get a file.
- Files go in the Meeting details step; the upload happens right after Send.
- The review queue rows show no paperclip tag; files are in the pop-up only.

## Rules

**Types.** Decided by the file's **content**, never only its name or `Content-Type` (same rule as
images, R14):

| Type | Content check | Extensions accepted |
|---|---|---|
| PDF | starts with `%PDF-` | `.pdf` |
| Word 97–2003 / Excel 97–2003 | OLE2 header `D0 CF 11 E0 A1 B1 1A E1` | `.doc`, `.xls` |
| Word | a zip (`PK\x03\x04`) that holds `word/document.xml` | `.docx` |
| Excel | a zip that holds `xl/workbook.xml` | `.xlsx` |

The extension must also be one of the five, and must agree with the content (a `.pdf` must be a
PDF; `.doc`/`.xls` both accept OLE2). Anything else: **415 `UNSUPPORTED_FILE_TYPE`**, message
"Only PDF, Word or Excel files." Opening the zip must be safe: read only the zip's file list,
never extract it.

**Size.** At most **10 MB** per file: a new setting `max_attachment_mb = 10`. Over that: **413
`FILE_TOO_LARGE`** (reuse `read_upload`). Empty file: 422 `VALIDATION_ERROR`.

**Count.** At most **3 files** per booking: a new setting `max_attachments_per_booking = 3`. A 4th:
**409 `ATTACHMENT_LIMIT_REACHED`** (new code, like `PHOTO_LIMIT_REACHED`).

**Who can open.** `booking_access.can_view` — the same rule as the booking itself: the booker,
Admin, the room owner, a Pitika of the room's province, the IT Lead once the ticket is forwarded,
and IT Staff assigned to the ticket. Anyone else gets **404** (same answer as a missing booking).
There is no food/catering role in the system, so nobody else is involved.

**Who can add or remove.** Only the booker (`requester_id`). Another viewer gets **403
`FORBIDDEN`**.

**When.** Add and remove are allowed while the status is `PENDING_PITIKA`, `PENDING_OWNER` or
`SETUP_IN_PROGRESS`. When it is `CONFIRMED`, `REJECTED` or `CANCELLED`: **409
`INVALID_TRANSITION`**, message "Files are locked once the booking is confirmed." (or "…is
closed." for rejected/cancelled). Read the booking with `load_booking_for_write` (FOR UPDATE), so
a confirm and an upload at the same moment can't both win. Files stay readable in every status,
forever (no clean-up job).

**Version.** Adding or removing a file does **not** change `bookings.version` and needs no
`version` in the request. Files are their own rows; reviewers' screens don't go stale because of
them.

## Data

New table `booking_attachments` (one model file, `app/models/booking_attachment.py`):

| Column | Type | Note |
|---|---|---|
| `id` | unsigned int PK | `IdMixin` |
| `booking_id` | FK `bookings.id`, RESTRICT | indexed |
| `file_name` | varchar(255) | the name as uploaded, cleaned: path parts removed, control characters removed, trimmed to 255 |
| `content_type` | varchar(100) | from the detected type, not from the browser |
| `size_bytes` | unsigned int | |
| `stored_path` | varchar(500) | path inside `attachment_dir`, `bookings/{booking_id}/{uuid}.{ext}` |
| `uploaded_by` | FK `users.id`, RESTRICT | the booker |
| `created_at`, `updated_at` | | `TimestampMixin` |

Rows are really deleted on remove (like room photos), and the file is deleted after the commit.
`Booking.attachments` relationship, ordered by `id`. One Alembic migration.

**Storage.** A new private folder setting `attachment_dir = ./attachments`, never under the
public `/uploads`. Same safe-path check as signatures (`resolve()` + `is_relative_to`). Add
`attachments/` to `.gitignore` next to `signatures/` and `avatars/`, and `ATTACHMENT_DIR` to
`.env.example`. (Docker runs only MySQL, so there is no app volume to change.)

## API

All under `/api/v1/bookings/{booking_id}/attachments`, signed-in users only.

| Method | Path | Who | Answer |
|---|---|---|---|
| `GET` | `` | viewers | `ItemList[AttachmentOut]` |
| `POST` | `` (multipart, field `file`) | booker, open status | 201 `AttachmentOut` |
| `GET` | `/{attachment_id}` | viewers | the file, `Content-Disposition: attachment` with the cleaned name (RFC 5987 `filename*` for Khmer names), `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store` |
| `DELETE` | `/{attachment_id}` | booker, open status | 204 |

An attachment id that belongs to another booking is 404.

`AttachmentOut`: `id`, `file_name`, `content_type`, `size_bytes`, `created_at`, `url` (the GET
path above).

`BookingDetail` gets `attachments: list[AttachmentOut]` and `attachments_open: bool` (the status
still lets files change), so every pop-up has the list without a second call. It is not a
per-user flag: the detail builder has no current user, and only My bookings (the booker's own
list) shows Add/remove. The server checks the booker on every write.

Code lives in one file per resource: `app/routers/booking_attachments.py`,
`app/schemas/booking_attachment.py`, `app/services/booking_attachment.py`.

## Dashboard

**One shared component**, `components/AttachmentList.vue`: the list of files (icon by type, name,
size like "1.2 MB"), each a download link that fetches with the auth token and saves the file
(same way as the request slip and `.ics` download). With `editable`, it also shows **Add file**
and a remove (×) button on each row, and enforces type, size and count on the client too (the
server is still the judge). Messages are short: "Only PDF, Word or Excel files.", "File too big
(max 10 MB).", "Up to 3 files."

**Book → Meeting details step:** a new optional field "Files (optional)" under Notes, using the
same component on files kept in the draft (not yet uploaded). The Review step lists them. On
**Send**, the booking is created first, then each file is uploaded one by one. If an upload fails,
the booking is still sent: the toast says "Request sent. 1 file could not be added — add it
from My bookings." Leaving the flow drops the files, like the rest of the draft.

**Where files show (read only, unless editable):**

- Staff: `BookingDetailDialog` (My bookings) — editable when `attachments_open`.
- Pitika and room owner: `ReviewPanel`.
- Admin: `BookingPanel`.
- IT: `ITPanel`.

With no files, the read-only places show nothing (no empty box). The editable place shows only
**Add file**.

## Tests

Backend (pytest, real MySQL): each type accepted; a renamed `.exe`/image refused (415); a `.docx`
name on a PDF refused; 10 MB + 1 byte refused (413); a 4th file refused (409); every viewer role
can list and download; a non-viewer gets 404 on list, download and upload; a non-booker viewer
gets 403 on upload and delete; upload and delete refused when confirmed, rejected or cancelled;
the file is not under `/uploads`; the download headers; a Khmer file name; delete removes the row
and the file; `BookingDetail` carries the list and the flag.

Dashboard (Vitest): the component lists, adds, removes and shows each error; Book sends the booking
then the files, and the partial-failure message; each of the 4 pop-ups shows the files; My bookings
hides Add/remove once confirmed.

## Left to the builder

- The exact look of the file rows (follow the soft-row / hairline style already used).
- Upload progress: a simple "Uploading…" state per file is enough.
- Whether the client blocks a duplicate file name (the server allows it).
