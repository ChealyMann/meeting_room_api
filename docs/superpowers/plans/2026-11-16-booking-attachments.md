# Booking Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The booker can add up to 3 document files (PDF, Word, Excel) to a booking until it is confirmed, and everyone who can see the booking can download them.

**Architecture:** A new `booking_attachments` table and a private `attachment_dir` folder. A pure type checker reads the file's bytes. One service and router at `/api/v1/bookings/{id}/attachments`. `BookingDetail` carries the list. On the dashboard, one shared `AttachmentList.vue` is used by the Book flow and the 4 booking pop-ups.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, MySQL 8, pytest. Vue 3 + TypeScript, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-16-booking-attachments-design.md`

## Global Constraints

- Types: PDF, `.doc`, `.docx`, `.xls`, `.xlsx`. The content is checked, not only the name. Extensions are not case-sensitive.
- `max_attachment_mb = 10`, `max_attachments_per_booking = 3` (new settings, `ge=1`).
- Errors: 415 `UNSUPPORTED_FILE_TYPE` "Only PDF, Word or Excel files."; 413 `FILE_TOO_LARGE` "File too big (max 10 MB)."; 409 `ATTACHMENT_LIMIT_REACHED` "Up to 3 files."; 409 `INVALID_TRANSITION` "Files are locked once the booking is confirmed." / "Files are locked: this booking is closed."; 403 `FORBIDDEN` "Only the booker can change the files."; 404 for anyone who cannot see the booking.
- Open statuses (files can change): `PENDING_PITIKA`, `PENDING_OWNER`, `SETUP_IN_PROGRESS`.
- Files never live under `upload_dir` (public `/uploads`).
- Adding or removing a file does not change `bookings.version`.
- Repo style: one model class per file; one schema/router/service file per resource; dashboard TS uses single quotes and no semicolons; no Claude attribution in commits.
- Run Python with `.venv\Scripts\python.exe`. Backend tests need Docker MySQL on port 3307 (`docker compose up -d`).

## Change to the spec (decided while planning)

`BookingDetail` gets **`attachments_open: bool`** (status is open) instead of `can_edit_attachments`. The detail builder has no current user. Only My bookings shows Add/remove, and it lists only the user's own bookings. The server still checks the booker on every write. Update the spec's API section in Task 3.

## Review Focus

1. `Agenda.PDF` (upper-case extension) must be accepted → test in Task 2.
2. A plain zip or an `.odt` renamed `.docx` must be refused with 415 → test in Task 2.
3. A Khmer file name (`កម្មវិធី.pdf`) downloads with that name → test in Task 3.
4. A row whose file is gone from disk gives 404, not 500 → test in Task 3.
5. A file over 10 MB is stopped in the browser before upload, with the server's message text → test in Task 4.

---

### Task 1: Settings, model, migration, error code

**Files:**
- Modify: `app/config.py` (after `avatar_dir`), `app/errors.py`, `app/models/__init__.py`, `app/models/booking.py`, `.gitignore`, `.env.example`, `tests/conftest.py` (`settings` fixture), `tests/test_errors.py`
- Create: `app/models/booking_attachment.py`, `alembic/versions/a7c2e9f4b1d3_booking_attachments.py` (down_revision `e8f1a3c5d7b9`)
- Test: `tests/test_booking_attachment_model.py`

**Interfaces:**
- Produces: `Settings.attachment_dir: Path = Path("./attachments")` (comment: private, like signatures), `Settings.max_attachment_mb: int = 10`, `Settings.max_attachments_per_booking: int = 3`; `ErrorCode.ATTACHMENT_LIMIT_REACHED`; model `BookingAttachment(IdMixin, TimestampMixin, Base)`, table `booking_attachments`, columns `booking_id` (FK bookings RESTRICT, indexed), `file_name String(255)`, `content_type String(100)`, `size_bytes UnsignedInt`, `stored_path String(500)`, `uploaded_by` (FK users RESTRICT); `Booking.attachments: Mapped[list["BookingAttachment"]] = relationship(order_by="BookingAttachment.id")`.

- [ ] **Step 1: Write the failing tests**

`tests/test_booking_attachment_model.py`:
- `test_settings_defaults`: `Settings(_env_file=None, database_url="x", jwt_secret="a"*32)` has `attachment_dir == Path("./attachments")`, `max_attachment_mb == 10`, `max_attachments_per_booking == 3`.
- `test_attachment_rows_belong_to_a_booking_in_order` (uses `make_bookable_room`, `make_user`, `make_booking`, `db_session`): add two `BookingAttachment` rows, flush, `db_session.refresh(booking)`, assert `[a.file_name for a in booking.attachments] == ["a.pdf", "b.docx"]`.

In `tests/test_errors.py`, add `"ATTACHMENT_LIMIT_REACHED"` to the complete list. In `tests/conftest.py` `settings`, add `attachment_dir=tmp_path / "attachments"`.

- [ ] **Step 2: Run to see them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_booking_attachment_model.py tests/test_errors.py -q`
Expected: FAIL (ImportError / missing setting / missing code).

- [ ] **Step 3: Implement**

Settings, error code, model file, `__init__` import and `__all__`, relationship, migration (`create_table` with the FK names in the repo's style; look at `e8f1a3c5d7b9` for how `booking_signers` was created). Add `attachments/` to `.gitignore` after `avatars/`, and `ATTACHMENT_DIR=./attachments` to `.env.example`.

- [ ] **Step 4: Run to see them pass, plus the migration tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_booking_attachment_model.py tests/test_errors.py tests/test_migrations.py tests/test_schema.py tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -m "Attachments: table, settings and error code"`

---

### Task 2: Document type check (pure)

**Files:**
- Create: `app/services/document_files.py`
- Test: `tests/test_document_files.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class DocumentType: extension: str; content_type: str`
  - `detect_document(data: bytes, file_name: str) -> DocumentType` — raises `AppError(UNSUPPORTED_FILE_TYPE, 415, "Only PDF, Word or Excel files.")`
  - `clean_file_name(file_name: str, extension: str) -> str`

Content types: pdf `application/pdf`; doc `application/msword`; xls `application/vnd.ms-excel`; docx `application/vnd.openxmlformats-officedocument.wordprocessingml.document`; xlsx `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

Rules: the extension is the lower-cased text after the last dot of the base name. `.pdf` needs `%PDF-` at the start. `.doc`/`.xls` need the OLE2 header `D0 CF 11 E0 A1 B1 1A E1`. `.docx`/`.xlsx` need `zipfile.is_zipfile` on a `BytesIO`, and `ZipFile(...).namelist()` must contain `word/document.xml` / `xl/workbook.xml`. Never extract. A `BadZipFile` is a 415.

`clean_file_name`: keep only the part after the last `/` or `\`; drop characters whose `unicodedata.category` starts with `C`; strip spaces; if it ends up empty, use `file.{extension}`; if it is longer than 255, cut the stem so that `stem + "." + extension` is 255 at most.

- [ ] **Step 1: Write the failing tests** (build docx/xlsx bytes in the test with `zipfile.ZipFile(BytesIO(), "w")` and write `word/document.xml` or `xl/workbook.xml`)

- `test_accepts_each_type` (parametrize the 5 types) → `detect_document(...).extension` is the expected one and `content_type` matches the table.
- `test_extension_case_does_not_matter`: `detect_document(PDF, "Agenda.PDF").extension == "pdf"`.
- `test_refuses_a_name_that_does_not_match`: PDF bytes named `x.docx` → 415.
- `test_refuses_a_plain_zip_named_docx`: a zip holding only `a.txt`, named `x.docx` → 415.
- `test_refuses_a_png_named_pdf` and `test_refuses_an_exe` (`b"MZ..."`, `x.exe`) → 415, message `"Only PDF, Word or Excel files."`.
- `test_refuses_broken_zip`: `b"PK\x03\x04garbage"` named `x.xlsx` → 415.
- `test_clean_file_name`: `"C:\\fake\\path\\Plan.pdf"` → `"Plan.pdf"`; `"../../a\x00b.pdf"` → `"ab.pdf"`; `"   "` → `"file.pdf"`; `"កម្មវិធី.pdf"` unchanged; a 300-character stem + `.docx` → length 255 and ends with `.docx`.

- [ ] **Step 2: Run to see them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_document_files.py -q` → FAIL (module missing).

- [ ] **Step 3: Implement `app/services/document_files.py`**

- [ ] **Step 4: Run to see them pass** → PASS.

- [ ] **Step 5: Commit**

`git commit -m "Attachments: check a document by its content"`

---

### Task 3: Service, schemas, router, booking detail

**Files:**
- Create: `app/schemas/booking_attachment.py`, `app/services/booking_attachment.py`, `app/routers/booking_attachments.py`
- Modify: `app/main.py` (include the router next to `bookings`), `app/schemas/booking.py` (`BookingDetail`), `app/services/booking_view.py` (`build_booking_detail`), `app/constants/booking.py` (add `ATTACHMENTS_OPEN`), spec file (API section: `attachments_open`)
- Test: `tests/test_booking_attachments.py`

**Interfaces:**
- Consumes: Task 1 model and settings; Task 2 `detect_document`, `clean_file_name`; `booking_access.load_visible_booking(session, current, id, for_write=True)`; `images.read_upload(file, max_mb)` (413 text "File too big (max 10 MB)."), `images.remove_files`.
- Produces:
  - `ATTACHMENTS_OPEN = {PENDING_PITIKA, PENDING_OWNER, SETUP_IN_PROGRESS}` in `app/constants/booking.py`
  - `class AttachmentOut(ResponseModel): id: int; file_name: str; content_type: str; size_bytes: int; created_at: UtcDateTime; url: str` (url = `/api/v1/bookings/{booking_id}/attachments/{id}`)
  - `attachment_out(row: BookingAttachment) -> AttachmentOut` (in the schema file or service)
  - `list_attachments(session, current, booking_id) -> list[BookingAttachment]`
  - `add_attachment(session, settings, current, booking_id, file: BinaryIO, file_name: str) -> BookingAttachment`
  - `attachment_file(session, settings, current, booking_id, attachment_id) -> tuple[BookingAttachment, Path]`
  - `remove_attachment(session, settings, current, booking_id, attachment_id) -> None`
  - `BookingDetail.attachments: list[AttachmentOut]`, `BookingDetail.attachments_open: bool`
  - Routes: `GET ""` → `ItemList[AttachmentOut]`; `POST ""` (UploadFile `file`) → 201 `AttachmentOut`; `GET "/{attachment_id}"` → file; `DELETE "/{attachment_id}"` → 204.

Order of checks on a write: visible (404) → booker (403) → status open (409) → (add only) count < max (409) → size (413) → empty (422) → type (415). `read_upload` raises `INVALID_IMAGE` "Not a real image." for an empty file; catch that one case in the service and raise `AppError(ErrorCode.VALIDATION_ERROR, 422, "The file is empty.")` instead. Write the file to `attachment_dir / f"bookings/{booking_id}/{uuid4()}.{ext}"`, then add the row and commit. If the commit fails, delete the file (like `user_signature.set_signature`). On remove, delete the row, commit, then delete the file. Safe path: `resolve()` + `is_relative_to(attachment_dir.resolve())`, else 404. Missing file on disk: log a warning and 404. Download headers: `Content-Disposition: attachment; filename="attachment-{id}.{ext}"; filename*=UTF-8''{quote(file_name)}`, `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store`, media type = `content_type`. Use `FileResponse`.

- [ ] **Step 1: Write the failing tests** in `tests/test_booking_attachments.py`

Reuse a `world` fixture like `tests/test_booking_access.py` (private room, owner, booker, IT staff assigned, Pitika of PHNOM_PENH, far Pitika, admin, stranger, IT lead with `forwarded=True`), but status `PENDING_PITIKA`. A helper `upload(client, headers, booking, name="a.pdf", data=PDF)` posts `files={"file": (name, data, "application/octet-stream")}`.

- `test_booker_uploads_and_lists` → 201; body `file_name == "a.pdf"`, `content_type == "application/pdf"`, `size_bytes == len(PDF)`, `url` ends with `/attachments/{id}`; then GET list `total == 1`.
- `test_file_is_private` → saved under `settings.attachment_dir`; nothing new under `settings.upload_dir`.
- `test_every_viewer_can_list_and_download` (parametrize booker, admin, owner, pitika, lead, helper) → 200 on both, bytes equal.
- `test_non_viewer_gets_404` (stranger, far_pitika, other_helper) on list, download, upload and delete.
- `test_viewer_who_is_not_the_booker_cannot_change` (admin, owner, pitika) → upload and delete 403 `FORBIDDEN`.
- `test_locked_after_confirm` (status CONFIRMED) → upload 409 `INVALID_TRANSITION` with message "Files are locked once the booking is confirmed."; delete also 409; GET still 200.
- `test_locked_when_closed` (parametrize REJECTED, CANCELLED) → 409 with "Files are locked: this booking is closed."
- `test_open_during_setup` (SETUP_IN_PROGRESS) → 201.
- `test_fourth_file_refused` → 3 uploads 201, the 4th 409 `ATTACHMENT_LIMIT_REACHED`.
- `test_too_big` → `settings.max_attachment_mb = 1` (or build Settings with 1), 1 MB + 1 byte → 413 `FILE_TOO_LARGE`.
- `test_wrong_type` → PNG bytes named `a.pdf` → 415.
- `test_empty_file` → `b""` named `a.pdf` → 422 `VALIDATION_ERROR` "The file is empty."
- `test_khmer_name_download` → upload `កម្មវិធី.pdf`; the download's `content-disposition` contains `filename*=UTF-8''%E1%9E%80` and the list shows `file_name == "កម្មវិធី.pdf"`; headers `x-content-type-options == "nosniff"`, `cache-control == "private, no-store"`.
- `test_missing_file_is_404` → upload, delete the file on disk, GET → 404.
- `test_attachment_of_another_booking_is_404` → an id from booking B under booking A's URL → 404.
- `test_delete_removes_row_and_file` → 204; list empty; file gone.
- `test_version_unchanged` → booking `version` is the same after upload and delete.
- `test_detail_carries_files` → `GET /bookings/{id}` has `attachments` (1 item) and `attachments_open is True`; for a CONFIRMED booking `attachments_open is False`.

- [ ] **Step 2: Run to see them fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_booking_attachments.py -q` → FAIL (404 on the routes).

- [ ] **Step 3: Implement** the schema, the service, the router (summaries and `responses` like `room_photos.py`), the `main.py` include, the `BookingDetail` fields and `build_booking_detail` (`attachments=[attachment_out(a) for a in booking.attachments]`, `attachments_open=booking.status in ATTACHMENTS_OPEN`). In the spec, change `can_edit_attachments` to `attachments_open`, and the Book "done screen" line to the toast text from Task 5.

- [ ] **Step 4: Run the new tests, then the full suite**

Run: `.venv\Scripts\python.exe -m pytest tests/test_booking_attachments.py -q` → PASS.
Run: `.venv\Scripts\python.exe -m pytest -q` → all pass (`BookingDetail` changes may touch snapshot-like tests in `tests/test_bookings_read.py`; update them to include the two new fields).
Run: `.venv\Scripts\python.exe -m ruff check app tests` and `ruff format --check app tests` → clean.

- [ ] **Step 5: Commit**

`git commit -m "Attachments: upload, list, download and remove on a booking"`

---

### Task 4: Dashboard API and the shared AttachmentList

**Files:**
- Modify: `admin_dashboard/src/api/schema.d.ts` (regenerate), `admin_dashboard/src/api/types.ts`
- Create: `admin_dashboard/src/api/attachments.ts`, `admin_dashboard/src/utils/attachments.ts`, `admin_dashboard/src/components/AttachmentList.vue`
- Test: `admin_dashboard/src/utils/__tests__/attachments.spec.ts`, `admin_dashboard/src/components/__tests__/attachment-list.spec.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `export type AttachmentOut = Schemas['AttachmentOut']`
  - `api/attachments.ts`: `listAttachments(client, bookingId): Promise<ItemList<AttachmentOut>>`, `uploadAttachment(client, bookingId, file: File): Promise<AttachmentOut>` (FormData field `file`, like `uploadRoomPhoto`), `getAttachment(client, url: string): Promise<Blob>` (`client.requestBlob(url)`), `removeAttachment(client, bookingId, id): Promise<void>`
  - `utils/attachments.ts`: `MAX_FILES = 3`, `MAX_MB = 10`, `ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx'`, `fileProblem(file: { name: string; size: number }, count: number): string | null` (returns the exact server messages: "Only PDF, Word or Excel files." / "File too big (max 10 MB)." / "Up to 3 files."), `sizeText(bytes: number): string` ("820 KB", "1.2 MB")
  - `AttachmentList.vue` props: `files: { name: string; size: number; url?: string; id?: number }[]`, `editable?: boolean`, `busy?: boolean`. Emits: `add: [File]`, `remove: [index: number]`, `open: [index: number]`. It shows nothing when `files` is empty and not editable. With `editable`, it shows an **Add file** button (hidden `<input type="file" :accept="ACCEPT">`), and runs `fileProblem` before it emits `add`; a problem shows under the list (`role="alert"`) and nothing is emitted. The parent does the network work (the Book draft keeps `File`s; the pop-ups call the API).

- [ ] **Step 1: Regenerate the API types**

Start the API (`.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`), then in `admin_dashboard`: `npm run gen:api`. Expected: `schema.d.ts` has `AttachmentOut` and `BookingDetail.attachments`, `attachments_open`. Stop the server.

- [ ] **Step 2: Write the failing tests**

`utils/__tests__/attachments.spec.ts`: `fileProblem({ name: 'a.PDF', size: 1 }, 0)` is null; `'a.png'` → "Only PDF, Word or Excel files."; size `10 * 1024 * 1024 + 1` → "File too big (max 10 MB)."; count 3 → "Up to 3 files."; `sizeText(839680) === '820 KB'`, `sizeText(1258291) === '1.2 MB'`.

`components/__tests__/attachment-list.spec.ts`: lists names and sizes; empty and read-only renders nothing (`wrapper.html()` is a comment); click on a name emits `open` with its index; editable shows **Add file** and a remove button per row (`aria-label="Remove a.pdf"`) that emits `remove`; choosing an 11 MB file shows "File too big (max 10 MB)." and emits nothing; choosing a good file emits `add`.

- [ ] **Step 3: Run to see them fail**

Run (in `admin_dashboard`): `npx vitest run src/utils/__tests__/attachments.spec.ts src/components/__tests__/attachment-list.spec.ts` → FAIL.

- [ ] **Step 4: Implement** the API file, utils, and component (hairline rows like `SoftRow`, lucide `FileText`/`FileSpreadsheet` icons, `Paperclip` on Add file).

- [ ] **Step 5: Run to see them pass**, plus `npx vue-tsc --noEmit -p tsconfig.app.json` and `npx eslint src` → clean.

- [ ] **Step 6: Commit**

`git commit -m "Dashboard: attachments API and the shared file list"`

---

### Task 5: Book flow — pick files, send, then upload

**Files:**
- Modify: `admin_dashboard/src/views/staff/book/useBookingDraft.ts` (add `files: File[]` to `BookingDraft`, start `[]`), `admin_dashboard/src/views/staff/book/MeetingStep.vue` (a "Files (optional)" field under "Agenda or notes", using `AttachmentList` editable over `draft.files`), `admin_dashboard/src/views/staff/book/ReviewStep.vue` (list the files, read only), `admin_dashboard/src/views/staff/BookView.vue` (`send()`)
- Test: `admin_dashboard/src/views/staff/__tests__/book-meeting.spec.ts`, `book-review.spec.ts`, and the fetch mock in `admin_dashboard/src/test-utils/staff.ts` (answer `POST /api/v1/bookings/{id}/attachments`)

**Interfaces:**
- Consumes: Task 4 `AttachmentList`, `uploadAttachment`.
- `send()`: after `sendBooking` resolves with `saved`, upload each `draft.files[i]` in order with `uploadAttachment(api, saved.id, file)`; count failures; never throw for them. Toast: no failure → the current text; with failures → `` `Request sent. ${n} file${n === 1 ? '' : 's'} could not be added — add ${n === 1 ? 'it' : 'them'} from My bookings.` ``. Then go to My bookings as now.

- [ ] **Step 1: Write the failing tests**

`book-meeting.spec.ts`: `it('adds and removes optional files')`: set a `File` on the file input (`new File(['%PDF-1'], 'agenda.pdf')`), see `agenda.pdf` listed, remove it, list empty; the step still goes on with no file.
`book-review.spec.ts`: `it('sends the booking, then each file')`: with 2 files, the fetch log has `POST /api/v1/bookings` before two `POST /api/v1/bookings/77/attachments` (use the id the mock returns). `it('still sends when a file fails')`: mock the second upload with a 415; the toast text is "Request sent. 1 file could not be added — add it from My bookings." and the route is `my-bookings`.

- [ ] **Step 2: Run to see them fail** — `npx vitest run src/views/staff/__tests__/book-meeting.spec.ts src/views/staff/__tests__/book-review.spec.ts` → FAIL.

- [ ] **Step 3: Implement.**

- [ ] **Step 4: Run all dashboard tests** — `npx vitest run` → PASS; `vue-tsc` and `eslint` clean.

- [ ] **Step 5: Commit**

`git commit -m "Book: optional files in Meeting details, uploaded after Send"`

---

### Task 6: Files in the 4 booking pop-ups

**Files:**
- Modify: `admin_dashboard/src/views/staff/BookingDetailDialog.vue` (editable when `booking.attachments_open`), `admin_dashboard/src/views/bookings/ReviewPanel.vue`, `admin_dashboard/src/views/bookings/BookingPanel.vue`, `admin_dashboard/src/views/it/ITPanel.vue` (read only)
- Test: `admin_dashboard/src/views/staff/__tests__/my-bookings.spec.ts`, `admin_dashboard/src/views/__tests__/review.spec.ts`, `booking-panel.spec.ts`, `it-setup.spec.ts`; add `attachments: []` and `attachments_open` to any booking-detail test data builder these use

**Interfaces:**
- Consumes: Task 4 component and API; `downloadBlob(blob, name)` from `utils/download.ts`.
- Each pop-up passes `booking.attachments` mapped to `{ id, name: file_name, size: size_bytes, url }`. `open` → `downloadBlob(await getAttachment(api, url), file_name)`. In `BookingDetailDialog` only: `add` → `uploadAttachment` then put the answer in the list; `remove` → `removeAttachment` then drop it; while a call runs, `busy`. A 409 (locked by a confirm that just happened) shows the server message and reloads the booking. Placement: a "Files" section after the meeting details, before the history (pick the same heading style the pop-up uses for its other sections).

- [ ] **Step 1: Write the failing tests**

`my-bookings.spec.ts`: `it('adds and removes files while the booking is waiting')` (PENDING_PITIKA, `attachments_open: true`) → Add file and Remove exist, the upload and delete calls are made, the list updates. `it('shows files read only once confirmed')` (`attachments_open: false`) → the file name shows, no Add file, no Remove button.
`review.spec.ts`, `booking-panel.spec.ts`, `it-setup.spec.ts`: `it('lists the booking files and downloads one')` → `agenda.pdf` shows; a click calls `GET /api/v1/bookings/{id}/attachments/{aid}`; no Add file button.

- [ ] **Step 2: Run to see them fail** → FAIL.

- [ ] **Step 3: Implement.**

- [ ] **Step 4: Run all dashboard tests, type check, lint** → PASS / clean.

- [ ] **Step 5: Run the full backend suite once more** — `.venv\Scripts\python.exe -m pytest -q` → all pass.

- [ ] **Step 6: Commit**

`git commit -m "Dashboard: booking files in My bookings, review, Admin and IT pop-ups"`
