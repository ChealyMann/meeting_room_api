# Request Slip (ប័ណ្ណស្នើ) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** plan only. Build it only when the owner says go.

**Goal:** A confirmed booking downloads a Word (.docx) request slip that looks like the NBC signed paper: header, the booking in Khmer, the Khmer lunar date, the booker's signature, and three opinion boxes signed automatically at confirm.

**Architecture:** The API builds the .docx (signatures are private files). Pure Khmer text and lunar-calendar helpers turn values into Khmer; a slip-data builder reads only **copies** kept on the booking (the booker's Khmer office names at send; the signers, their signatures and the confirm time at confirm), so an old slip never changes. New Admin data: a head on each department and office, and one "Request slip" settings row (Director of Cabinet, address). The dashboard adds a download button and the Admin pickers.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic (MySQL), pytest, python-docx · Vue 3 + TS, Vitest, Playwright (only to make the lunar fixture).

**Spec:** this plan carries the owner's decisions (13 Nov 2026) below; the look is the demo https://claude.ai/artifact/GESV7Yw3WNGqwLnSF1bKdD (switch "Show where the data comes from" for every field's source) and the signed scan `SKM_28726091415580.pdf` (owner's file). Read both before Task 6.

## Owner decisions (the spec)

- Word .docx only. The **booker**, **Admin** and the **Pitika of the room's province** can download. Only CONFIRMED (also when it shows as COMPLETED). Other status → 404 "This booking is not confirmed yet.".
- Page (A4, like the scan): NBC logo top left with "ធនាគារជាតិ នៃ កម្ពុជា" under it; "លេខ" + dots (never filled); "ព្រះរាជាណាចក្រកម្ពុជា / ជាតិ សាសនា ព្រះមហាក្សត្រ" top right; title "ប័ណ្ណស្នើ"; the address line at the bottom (from settings). Fonts: Khmer OS Battambang (text), Khmer OS Muol Light (labels, names, title). Filled text black; opinion comments and dates blue `1F3A93`.
- Lines: "គោរពជូន ៖ <dir title>នាយកខុទ្ទកាល័យ"; "តាមរយៈ ៖ - <dept head title>ប្រធាន<department_kh>"; "- <office head title>ប្រធាន<division_kh>". No department / office → dots in place of the name.
- Subject, one sentence: "៖ សំណើសុំរៀបចំបន្ទប់ប្រជុំ “<room name_kh>” សម្រាប់កិច្ចប្រជុំ<meeting_title>។ <when> សមាជិកចូលរួមចំនួន <attendees> រូប។". **Keep the end time.** `<when>`:
  - one day: "កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅនៅថ្ងៃទី១៥ ខែកញ្ញា ឆ្នាំ២០២៦ វេលាម៉ោង ២:០០ នាទីរសៀល ដល់ម៉ោង ៥:០០ នាទីល្ងាច។"
  - several days, one time: "កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅរយៈពេល ៣ថ្ងៃ ចាប់ពីថ្ងៃទី២៣ ដល់ថ្ងៃទី២៥ ខែវិច្ឆិកា ឆ្នាំ២០២៦ វេលាម៉ោង ៨:០០ នាទីព្រឹក ដល់ម៉ោង ១២:០០ នាទីថ្ងៃត្រង់។" (first day in full when month or year differ)
  - times differ: "កិច្ចប្រជុំនឹងប្រព្រឹត្តទៅរយៈពេល ៥ថ្ងៃ តាមកាលវិភាគខាងក្រោម៖" + a table ល.រ | កាលបរិច្ឆេទ | វេលាម៉ោង.
- ស្នើសុំរៀបចំ៖ "- នំ ផ្លែឈើ និងភេសជ្ជៈ។" when there is a catering order; "- អ្នកបច្ចេកទេស IT និងឧបករណ៍ IT។" when there is an IT ticket; neither → "- មិនមាន។".
- Closing: "អាស្រ័យដូចបានជម្រាបជូនខាងលើ សូម <dir title>នាយកខុទ្ទកាល័យ មេត្តាពិនិត្យ និងសម្រេចដោយអនុគ្រោះ។" / "សូម <dir title>នាយកខុទ្ទកាល័យ មេត្តាទទួលនូវការគោរពដ៏ខ្ពង់ខ្ពស់អំពីយើងខ្ញុំ។".
- Dates, from the day **sent** (`bookings.created_at` in Phnom Penh): lunar line e.g. "ថ្ងៃចន្ទ ៣កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០" and "រាជធានីភ្នំពេញ ថ្ងៃទី១៤ ខែកញ្ញា ឆ្នាំ២០២៦".
- អ្នកធ្វើប័ណ្ណ: the booker's signature and Khmer name.
- Opinion boxes, signed **automatically at confirm**, same text every time, with the person's signature, the **confirm date** "១៥/០៩/២០២៦" and "<title> <name_kh>":
  - office head (middle, under the dates): "សូមគោរពជូន <dept head title>ប្រធាននាយកដ្ឋាន មេត្តាពិនិត្យ និងសម្រេចដោយអនុគ្រោះ។"
  - department head (left, beside the closing lines): "សូមគោរពជូន <dir title>នាយកខុទ្ទកាល័យ មេត្តាពិនិត្យ និងសម្រេចដោយអនុគ្រោះ។"
  - Director of Cabinet (left, under its label beside the subject): "ឯកភាពតាមសំណើ។"
  - A box with no person set stays empty (label only). A person with no saved signature: comment, date, name, no picture.
  - **The booker may be a head:** then they sign that box too.
- Titles from `users.title`: "Mr." → "លោក", "Ms." / "Mrs." → "លោកស្រី", "Dr." → "បណ្ឌិត", none → "" (just "ប្រធាន…").
- Heads: the Admin sets a head on each department and each office (division). The Director of Cabinet and the address line are on a new Admin page **"Request slip"** (Setup). Address default: "ប្រអប់សំបុត្រលេខ ២៥, ផ្ទះលេខ ៨៨ ផ្លូវលេខ ១០២ កែងផ្លូវលេខ ១៩ សង្កាត់វត្តភ្នំ ខណ្ឌដូនពេញ រាជធានីភ្នំពេញ, ទូរស័ព្ទ ៖ (៨៥៥-២៣) ៧២២ ៥៦៣, ទូរស័ព្ទ / ទូរសារ ៖ (៨៥៥-២៣) ៩២៦ ១១៧" (the owner checks the numbers on the page).
- **Copies, so old slips never change:** at send, `requester_info` also keeps `division_id`, `division_kh`, `department_id`, `department_kh`; at confirm, the app keeps `confirmed_at` and one signer row per box (and one for the booker) with name, title and a **copy** of the signature PNG.

## Global Constraints

- Branch `feature/staff-booking-pages` (or a new branch from it if the owner asks). Commits and PRs **without** any Claude attribution line.
- API: pip + `requirements*.txt` (no uv), Python 3.12, `ruff format` + `ruff check` clean. Models one class per file; schemas, routers, services one file per resource.
- `ErrorCode` must not grow (see `app/errors.py`); use existing codes.
- Signature files stay out of `UPLOAD_DIR` (R19). Copies go under `SIGNATURE_DIR/bookings/<booking_id>/<role>.png`.
- Dashboard: `npm run gen:api` after API changes (API on :8000); views import `api` from `../api`; copy in short plain English.
- Run pytest and Playwright one at a time.

## Review Focus

1. **A booking confirmed before this feature** (no signer rows, no `confirmed_at` before the backfill): the slip still downloads, boxes empty, booker signature from the current profile. → Task 7 test `test_old_booking_without_copies`.
2. **The booker moves office or a head changes after confirm**: the slip keeps the old names, heads and signatures. → Task 5 test `test_copies_survive_moves`, Task 7 test `test_slip_reads_only_copies`.
3. **The booker has no division** (Admin user, no office): "តាមរយៈ" lines show dots, no head boxes signed, no crash. → Task 5 test `test_booker_without_division`.
4. **A signature file missing on disk** (deleted or moved): the box prints without a picture. → Task 5 test `test_missing_signature_file_is_skipped`.
5. **A long booking** (200-character title, 20 sessions with different times): the table runs onto page 2 and the file still opens. → Task 7 test `test_twenty_sessions`.

---

### Task 1: Khmer words for numbers, dates, times and titles

**Files:**
- Create: `app/services/khmer_text.py`
- Test: `tests/test_khmer_text.py`

**Interfaces:**
- Produces: `khmer_digits(value: int | str) -> str`; `khmer_date(day: date) -> str` ("ថ្ងៃទី១៤ ខែកញ្ញា ឆ្នាំ២០២៦"); `khmer_short_date(day: date) -> str` ("១៥/០៩/២០២៦"); `khmer_time(t: time) -> str` ("ម៉ោង ២:០០ នាទីរសៀល"); `khmer_weekday(day: date) -> str` ("ច័ន្ទ"); `khmer_title(title: str | None) -> str`; `KH_MONTHS: tuple[str, ...]` (មករា … ធ្នូ).

- [ ] **Step 1: Write the failing tests**

```python
def test_digits():
    assert khmer_digits(2026) == "២០២៦"
    assert khmer_digits("08:30") == "០៨:៣០"

def test_dates():
    assert khmer_date(date(2026, 9, 14)) == "ថ្ងៃទី១៤ ខែកញ្ញា ឆ្នាំ២០២៦"
    assert khmer_short_date(date(2026, 9, 5)) == "០៥/០៩/២០២៦"
    assert khmer_weekday(date(2026, 9, 14)) == "ច័ន្ទ"

@pytest.mark.parametrize(("t", "text"), [
    (time(8, 0), "ម៉ោង ៨:០០ នាទីព្រឹក"),
    (time(12, 30), "ម៉ោង ១២:៣០ នាទីថ្ងៃត្រង់"),
    (time(14, 0), "ម៉ោង ២:០០ នាទីរសៀល"),
    (time(17, 0), "ម៉ោង ៥:០០ នាទីល្ងាច"),
    (time(19, 30), "ម៉ោង ៧:៣០ នាទីយប់"),
])
def test_times(t, text):
    assert khmer_time(t) == text

@pytest.mark.parametrize(("title", "word"), [("Mr.", "លោក"), ("Ms.", "លោកស្រី"), ("Mrs.", "លោកស្រី"), ("Dr.", "បណ្ឌិត"), (None, "")])
def test_titles(title, word):
    assert khmer_title(title) == word
```

- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_khmer_text.py -q` — Expected: FAIL (module missing).
- [ ] **Step 3: Implement the functions in `app/services/khmer_text.py`.** Periods: before 12:00 ព្រឹក, 12:xx ថ្ងៃត្រង់, 13–16 រសៀល, 17–18 ល្ងាច, 19+ យប់; hour shown 12-hour (`h % 12 or 12`), minutes two digits. Weekdays: អាទិត្យ ច័ន្ទ អង្គារ ពុធ ព្រហស្បតិ៍ សុក្រ សៅរ៍.
- [ ] **Step 4: Run** the same command — Expected: PASS. `ruff check app tests` clean.
- [ ] **Step 5: Commit** `git add app/services/khmer_text.py tests/test_khmer_text.py && git commit -m "Slip: Khmer words for numbers, dates, times and titles"`

### Task 2: Khmer lunar date

**Files:**
- Create: `app/services/khmer_calendar.py`, `tests/fixtures/khmer_lunar_2026_2027.json`, `scripts/make_lunar_fixture.cjs`
- Test: `tests/test_khmer_calendar.py`

**Interfaces:**
- Consumes: `khmer_digits` (Task 1).
- Produces: `@dataclass(frozen=True) class LunarDate: weekday: str; day: int; phase: str; month: str; animal: str; sak: str; be_year: int`; `lunar_date(day: date) -> LunarDate`; `lunar_line(day: date) -> str` ("ថ្ងៃចន្ទ ៣កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០").

- [ ] **Step 1: Make the fixture.** `scripts/make_lunar_fixture.cjs` opens a Playwright page that loads `https://cdn.jsdelivr.net/npm/@thyrith/momentkh@3.0.3/momentkh.js` and writes, for every day 2026-01-01 … 2027-12-31, `{"date": "...", "line": momentkh.format(fromGregorian(y, m, d), "ថ្ងៃW dN ខែm ឆ្នាំa e ព.ស.b")}` — check the output's first lines by eye against the field names below. Save to `tests/fixtures/khmer_lunar_2026_2027.json` (730 rows). Playwright lives in the dashboard: load it with `require(path.resolve('admin_dashboard/node_modules/playwright'))` and run from the repo root: `node scripts/make_lunar_fixture.cjs`.
- [ ] **Step 2: Write the failing tests**

```python
def test_signed_paper_date():  # the owner's signed scan
    assert lunar_line(date(2026, 9, 14)) == "ថ្ងៃចន្ទ ៣កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០"

def test_demo_dates():
    assert lunar_line(date(2026, 9, 16)) == "ថ្ងៃពុធ ៥កើត ខែភទ្របទ ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០"
    assert lunar_line(date(2026, 11, 12)) == "ថ្ងៃព្រហស្បតិ៍ ៣កើត ខែកត្ដិក ឆ្នាំមមី អដ្ឋស័ក ព.ស.២៥៧០"

@pytest.mark.parametrize(("day", "month", "phase"), [
    (date(2026, 5, 1), "ពិសាខ", "កើត"),     # Visak Bochea
    (date(2026, 10, 11), "ភទ្របទ", "រោច"),  # Pchum Ben
    (date(2026, 11, 24), "កត្ដិក", "កើត"),   # Water Festival
])
def test_full_moons_2026(day, month, phase):
    lunar = lunar_date(day)
    assert (lunar.day, lunar.month, lunar.phase) == (15, month, phase)

def test_every_day_matches_momentkh():
    rows = json.loads(Path("tests/fixtures/khmer_lunar_2026_2027.json").read_text(encoding="utf-8"))
    wrong = [r["date"] for r in rows if lunar_line(date.fromisoformat(r["date"])) != r["line"]]
    assert wrong == []
```

- [ ] **Step 3: Run** `.venv/Scripts/python -m pytest tests/test_khmer_calendar.py -q` — Expected: FAIL.
- [ ] **Step 4: Implement by porting momentkh 3.0.3** (`momentkh.ts`, MIT; get it with `npm pack @thyrith/momentkh@3.0.3`; keep its MIT notice at the top of the file). Port only Gregorian → lunar: the aharkun / kromthupul / avoman / bodithey year rules, leap month (adhikameas) and leap day (chantrameas) years, the epoch walk, the Buddhist-era and animal-year change days, and the sak. Names in Khmer exactly as momentkh prints them (e.g. "កត្ដិក" with ដ្ដ).
- [ ] **Step 5: Run** — Expected: PASS (all 730 days). Commit `git commit -m "Slip: Khmer lunar date (port of momentkh 3.0.3)"`.

### Task 3: Heads of departments and offices

**Files:**
- Create: `alembic/versions/<new>_department_division_heads.py`
- Modify: `app/models/department.py`, `app/models/division.py`, `app/schemas/department.py`, `app/schemas/division.py`, `app/services/department.py`, `app/services/division.py`
- Test: `tests/test_departments.py`, `tests/test_divisions.py`

**Interfaces:**
- Produces: `Department.head_user_id: Mapped[int | None]` + `head: Mapped["User | None"]`; same on `Division`. Schemas: `head_user_id: RefId = None` on Create/Update; `head: NamedRef | None` on Out.

- [ ] **Step 1: Write the failing tests** (both resources): create/patch with `head_user_id` of an active user → 201/200 and `head == {"id", "name_en", "name_kh"}`; `head_user_id: null` clears it; an unknown id → 422 field `head_user_id`; an inactive user → 409 `INACTIVE_REFERENCE` on `head_user_id`; `test_schema.py` expects `head_user_id: ("int unsigned", True)` on both tables.
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_departments.py tests/test_divisions.py tests/test_schema.py -q` — FAIL.
- [ ] **Step 3: Implement.** Migration adds the nullable FK (`ON DELETE SET NULL`) to both tables (`down_revision` = the current head; check with `alembic heads`). Services check the user with the existing `get_reference` / active-reference helpers, like `room_owner_id`.
- [ ] **Step 4: Run** — PASS. Commit `"Slip: a head on each department and office"`.

### Task 4: "Request slip" settings (Director of Cabinet, address)

**Files:**
- Create: `app/models/slip_settings.py`, `app/schemas/slip_settings.py`, `app/services/slip_settings.py`, `app/routers/slip_settings.py`, `alembic/versions/<new>_slip_settings.py`
- Modify: `app/main.py` (include router), `app/models/__init__.py`
- Test: `tests/test_slip_settings.py`

**Interfaces:**
- Produces: table `slip_settings` (one row, `id = 1`): `director_user_id` (nullable FK users, SET NULL), `address_kh VARCHAR(500)` (default from the spec), timestamps. `GET /slip-settings` (Admin) → `SlipSettingsOut {director: NamedRef | None, address_kh: str, updated_at}`; `PUT /slip-settings` (Admin) body `{director_user_id: int | None, address_kh: str (1–500, trimmed)}`. Service `get_slip_settings(session) -> SlipSettings` (creates the row on first read).

- [ ] **Step 1: Write the failing tests:** first GET returns the default address and `director: None`; PUT sets both and GET returns them; staff → 403; inactive director → 409 `INACTIVE_REFERENCE`; empty address → 422.
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_slip_settings.py -q` — FAIL.
- [ ] **Step 3: Implement** (migration inserts row 1 with the default address).
- [ ] **Step 4: Run** — PASS. Commit `"Slip: Request slip settings (Director of Cabinet, address)"`.

### Task 5: Copies kept on the booking (send and confirm)

**Files:**
- Create: `app/models/booking_signer.py`, `app/services/booking_signers.py`, `alembic/versions/<new>_booking_signers.py`
- Modify: `app/services/booking.py:111` (`requester_info`), `app/services/booking_transitions.py:237` (`make_confirmed`), `app/models/booking.py` (`confirmed_at`, `signers` relationship), `app/models/__init__.py`, `tests/factories.py` (`make_booking` sets `confirmed_at` for CONFIRMED)
- Test: `tests/test_booking_signers.py`

**Interfaces:**
- Consumes: `Department.head`, `Division.head` (Task 3); `get_slip_settings` (Task 4); `signature_file` / `SIGNATURE_DIR` from `app/services/user_signature.py`.
- Produces: `requester_info` gains `division_id`, `division_kh`, `department_id`, `department_kh` (None when no division). `Booking.confirmed_at: Mapped[datetime | None]` (UTC). `class SignerRole(StrEnum): MAKER, OFFICE_HEAD, DEPARTMENT_HEAD, DIRECTOR` (in `app/constants/booking.py`). Table `booking_signers`: `booking_id`, `role`, `user_id` (nullable, SET NULL), `name_kh`, `title` (nullable), `signature_path` (nullable, inside SIGNATURE_DIR), `signed_at`; unique (`booking_id`, `role`). `record_signers(session, settings, booking) -> None` — called from `make_confirmed` after `advance`, which now also sets `confirmed_at=clock.now_utc()`.

- [ ] **Step 1: Write the failing tests**

```python
def test_send_keeps_khmer_office_names(...)        # requester_info has division_kh / department_kh and the ids
def test_confirm_keeps_time_and_four_signers(...)  # roles MAKER, OFFICE_HEAD, DEPARTMENT_HEAD, DIRECTOR; names, titles; files copied to SIGNATURE_DIR/bookings/<id>/<ROLE>.png
def test_copies_survive_moves(...)                 # after confirm: move the booker, change both heads and their signatures → rows and files unchanged
def test_booker_is_office_head(...)                # same user in MAKER and OFFICE_HEAD
def test_booker_without_division(...)              # only MAKER and DIRECTOR rows
def test_unset_head_has_no_row(...)                # department without head → no DEPARTMENT_HEAD row
def test_missing_signature_file_is_skipped(...)    # profile path set but file gone → row with signature_path None
def test_all_confirm_paths_record(...)             # last review, IT ready, and the auto-confirm at start (booking_expiry) all write rows
```

Heads come from the ids in `requester_info` (the office **when sent**), not from the booker's current division.

- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_booking_signers.py -q` — FAIL.
- [ ] **Step 3: Implement.** Migration: `bookings.confirmed_at` + backfill for CONFIRMED rows (the IT ticket's `ready_at`, else the last APPROVED review's `reviewed_at`, else `created_at`), and the `booking_signers` table. No signer backfill (old bookings get empty boxes; see Review Focus 1).
- [ ] **Step 4: Run** the new tests and `tests/test_booking_*.py tests/test_it_*.py` — PASS. Commit `"Slip: keep the booker's Khmer office names at send and the signers at confirm"`.

### Task 6: Slip data (every value, in Khmer, from the copies)

**Files:**
- Create: `app/services/request_slip_data.py`
- Test: `tests/test_request_slip_data.py`

**Interfaces:**
- Consumes: Tasks 1, 2, 4, 5.
- Produces:
```python
@dataclass(frozen=True)
class SlipSigner:  # one opinion box or the maker
    comment: str | None; name: str; title: str; signature: Path | None; date: str | None  # date "១៥/០៩/២០២៦"
@dataclass(frozen=True)
class SlipData:
    director_title: str; department_line: str; office_line: str     # "លោកប្រធាននាយកដ្ឋាន…", dots when none
    subject: str                                                    # the whole sentence incl. people when no table
    timetable: list[tuple[str, str, str]]                           # (ល.រ, កាលបរិច្ឆេទ, វេលាម៉ោង); empty unless times differ
    people_line: str | None                                         # only when there is a timetable
    requests: list[str]; closing: list[str]
    lunar_line: str; city_date: str                                 # "រាជធានីភ្នំពេញ ថ្ងៃទី…"
    address: str; maker: SlipSigner
    director: SlipSigner | None; department_head: SlipSigner | None; office_head: SlipSigner | None
def build_slip_data(session: Session, settings: Settings, booking: Booking) -> SlipData
```
Comments and titles exactly as in "Owner decisions". Names `title + " " + name_kh` are built in the renderer. The maker's signature: the MAKER copy, else (old booking) the current profile file.

- [ ] **Step 1: Write the failing tests** with the three demo bookings: one afternoon (subject equals the spec's one-day sentence for 15 Sep 2026 14:00–17:00, people 30, food only → requests `["- នំ ផ្លែឈើ និងភេសជ្ជៈ។"]`), three days same time (the spec's range sentence), five days different times (timetable of 5 rows, `people_line` set); no catering and no IT → `["- មិនមាន។"]`; `lunar_line` for a booking sent 14 Sep 2026 equals the signed-paper line; `city_date == "រាជធានីភ្នំពេញ ថ្ងៃទី១៤ ខែកញ្ញា ឆ្នាំ២០២៦"`; office head comment uses the department head's title; boxes' `date` is `confirmed_at` in Phnom Penh; `test_slip_reads_only_copies` (rename the department after send → old Khmer name stays).
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_request_slip_data.py -q` — FAIL.
- [ ] **Step 3: Implement** (sessions sorted by date then start; "days" = distinct dates).
- [ ] **Step 4: Run** — PASS. Commit `"Slip: all slip values in Khmer from the booking's copies"`.

### Task 7: The .docx and its endpoint

**Files:**
- Create: `app/services/request_slip_docx.py`, `app/assets/nbc-logo.png` (copy of `admin_dashboard/public/nbc-logo.png`)
- Modify: `app/routers/bookings.py` (new route), `app/services/booking_access.py` (`is_slip_viewer`), `requirements.txt` (`python-docx==1.1.2`), `spec.md` (endpoint + R20 rule)
- Test: `tests/test_request_slip.py`

**Interfaces:**
- Consumes: `SlipData` (Task 6).
- Produces: `render_slip_docx(data: SlipData) -> bytes`; `GET /api/v1/bookings/{id}/request-slip` → `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `Content-Disposition: attachment; filename="request-slip-<reference_code>.docx"; filename*=UTF-8''ប័ណ្ណស្នើបន្ទប់ប្រជុំ_<room name_kh>_<dd_mm_yyyy first session>.docx`. `is_slip_viewer(current, booking) -> bool`: requester, Admin, Pitika of the province.

- [ ] **Step 1: Write the failing tests:** booker / Admin / Pitika get 200 and a file python-docx can open whose text contains the subject, the lunar line, the three comments and the names; room owner and IT → 403; not visible → 404; PENDING / REJECTED / CANCELLED → 404 "This booking is not confirmed yet."; COMPLETED (ended) → 200; the document has 5 pictures when all signers have signatures (logo + maker + 3 boxes); `test_old_booking_without_copies` (no signer rows: 200, only the logo and the maker's current signature); `test_twenty_sessions` (20 rows, 200-char title: opens, timetable has 20 rows).
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/test_request_slip.py -q` — FAIL.
- [ ] **Step 3: Implement the renderer** to match the scan: A4, margins top/bottom 1.8 cm, left 1.0 cm, right 1.1 cm; a borderless header table (logo 2.6 cm wide + bank name | motto); title centred, underlined, Muol Light 14 pt; a borderless 2-column body table (labels 6.6 cm, right-aligned, Muol Light 11 pt underlined | text 11 pt Battambang). Dashed rule lines: every text run underlined `WD_UNDERLINE.DASH`, and each paragraph ends with a right tab at the cell edge whose leader is `WD_TAB_LEADER.HYPHENS`, so short lines run to the edge like the paper. Opinion boxes: comment and date blue `1F3A93`, signature pictures 3.2 cm wide, names Muol Light. Address centred 8 pt at the bottom (page footer). Set East Asian / complex-script fonts on every run (`w:rFonts w:cs`).
- [ ] **Step 4: Run** — PASS. **Look at it:** save one demo slip, convert with Word (`ExportAsFixedFormat`, as done in this session) and compare with the scan; fix spacing once. Commit `"Slip: download the request slip as Word"`.

### Task 8: Dashboard — the download button

**Files:**
- Create: `admin_dashboard/src/utils/download.ts`
- Modify: `src/api/bookings.ts` (`getRequestSlip`), `src/views/staff/BookingDetailDialog.vue`, `src/views/bookings/BookingPanel.vue`, `src/views/bookings/ReviewPanel.vue` (Add to calendar code moves to `downloadBlob`)
- Test: `src/views/staff/__tests__/my-bookings.spec.ts`, `src/views/__tests__/booking-panel.spec.ts`, `src/views/__tests__/review.spec.ts`

**Interfaces:**
- Produces: `getRequestSlip(client: ApiClient, id: number): Promise<Blob>`; `downloadBlob(blob: Blob, fileName: string): void`.

- [ ] **Step 1: Write the failing tests:** on a CONFIRMED (and COMPLETED) booking the button "ប័ណ្ណស្នើ (Word)" calls `GET /api/v1/bookings/7/request-slip` and saves `request-slip-NBC-26-7.docx`; on PENDING / REJECTED / CANCELLED there is no button; an API error shows under the button ("The slip could not load." when no message).
- [ ] **Step 2: Run** `npx vitest run src/views/staff src/views/__tests__/booking-panel.spec.ts src/views/__tests__/review.spec.ts` — FAIL.
- [ ] **Step 3: Implement** (`npm run gen:api` first).
- [ ] **Step 4: Run** — PASS; `npm run type-check`, `npx eslint src` clean. Commit `"Dashboard: download the request slip (Word) on a confirmed booking"`.

### Task 9: Dashboard — heads and the Request slip page

**Files:**
- Create: `admin_dashboard/src/views/SlipSettingsView.vue`, `src/api/slipSettings.ts`
- Modify: `src/views/organisation/DepartmentFormPanel.vue`, `src/views/organisation/DivisionFormPanel.vue` (a "Head" `SearchPicker` of active users, optional), `src/router/index.ts` (route `slip-settings`, Admin), `src/layouts/nav.ts` (Setup → Organisation → "Request slip"), `src/layouts/__tests__/nav.spec.ts`
- Test: `src/views/__tests__/departments.spec.ts`, `src/views/__tests__/divisions.spec.ts`, `src/views/__tests__/slip-settings.spec.ts`

**Interfaces:**
- Consumes: Tasks 3 and 4 endpoints.
- Produces: `getSlipSettings(client)`, `saveSlipSettings(client, body)`.

- [ ] **Step 1: Write the failing tests:** department and office panels send `head_user_id` (and `null` when cleared) and show the head in the list; the Request slip page loads the director and address, saves with PUT, shows API field errors, and says "Saved" in a toast.
- [ ] **Step 2: Run** `npx vitest run src/views/__tests__/departments.spec.ts src/views/__tests__/divisions.spec.ts src/views/__tests__/slip-settings.spec.ts src/layouts` — FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — PASS; whole dashboard suite, type-check and lint clean. Commit `"Dashboard: heads on departments and offices, and the Request slip page"`.

### Task 10: Finish

- [ ] Full backend suite (`.venv/Scripts/python -m pytest -q`), `ruff`, whole dashboard suite — all pass.
- [ ] `spec.md`: endpoints (`/slip-settings`, `/bookings/{id}/request-slip`), the new fields, rule R20 (who downloads, when, the copies). `requirements.md`: the slip in the Staff, Admin and Pitika lists.
- [ ] Ask the owner to check one real slip printed on paper, and the address numbers on the Request slip page.
- [ ] Commit `"Slip: spec and requirements"`.
