# Room Booking API — Build Spec for AI Agent (Rooms & Users)

Version: 21 Oct 2026. Exported from the shared spec doc; if the two differ, ask which one is current.

## 1. How to use this spec

This document is the single source of truth for building the rooms and users part of a room booking API. It is written for an AI coding agent. Follow it exactly; where it is silent, choose the simplest option that keeps every rule here true.

**Priorities, in order**

1. Correct data and business rules (sections 6, 7, 15).
2. Security: authentication, permissions, never leaking `password_hash` or `door_code` (sections 5, 9).
3. The exact request and response contracts (sections 4, 10–14, 17).
4. Edge cases (section 16) and tests (section 18).
5. Code quality and readability.

**Rules for the agent**

- Build only what is in scope (section 2). Do not add booking tables, booking endpoints or approval logic.
- Do not rename fields, paths or error codes. Clients are built against these names.
- Every business rule and edge case must have at least one automated test.
- Keep business logic in service functions, not in route handlers, so the booking scope can reuse it later.
- If two parts of this spec conflict, stop and report the conflict instead of guessing.
- Stop and ask before: changing the database schema beyond section 6–7, adding a dependency not listed in section 3, or weakening a security rule.

**Words used in this spec**

| Word | Meaning |
| --- | --- |
| must | Required. A build that breaks it is wrong. |
| should | Strongly recommended. Skip only with a written reason. |
| Admin, Owner, Any | Access labels, defined in section 5. |
| deactivate | Set `is_active` to false. Nothing is hard-deleted except room photos. |
| no-owner room | A room whose `room_owner_id` is null. Anyone can book it later. |

## 2. Scope

Build the master data, users and sign-in for the room booking system: 14 tables, about 60 endpoints, no bookings.

**In scope**

- Sign-in with email and password, token refresh, password change, admin password reset.
- Places: provinces (fixed list), locations, buildings, floors.
- Rooms: categories, rooms, room photos (uploaded to server disk), equipment and which rooms have it.
- Organisation: departments, divisions, positions.
- Users and roles: user accounts, the six fixed roles, role assignment.
- The province helpers `get_room_province()` and `get_user_province()` as shared service functions.

**Out of scope (do not build)**

- Bookings, availability search by date, approval steps, IT support requests.
- Email sending of any kind (no set-password links, no notifications).
- Self-registration, forgot-password by email, single sign-on.
- Hard deletes of any record except room photos.
- A user interface. This is an API only.

## 3. Tech stack and project structure

Python 3.12, FastAPI, SQLAlchemy 2.0 and MySQL 8, with Alembic migrations and pytest.

| Concern | Choice |
| --- | --- |
| Language | Python 3.12 |
| Web framework | FastAPI, Pydantic v2 (`extra="forbid"` on every request model) |
| Database | MySQL 8.0+, InnoDB, `utf8mb4`, collation `utf8mb4_0900_ai_ci` |
| ORM and driver | SQLAlchemy 2.0 (sync), PyMySQL |
| Migrations | Alembic; one migration per change; never edit an applied migration |
| Password hashing | `argon2-cffi` (Argon2id). Not bcrypt: bcrypt silently cuts passwords at 72 bytes |
| Tokens | `PyJWT`, HS256, secret from environment |
| Images | Pillow (validate, re-encode, thumbnail) |
| Settings | `pydantic-settings`, values from environment / `.env` |
| Tests | pytest, FastAPI `TestClient`, a real MySQL test database (not SQLite) |
| Lint and format | ruff |

**Folder layout**

```
app/
  main.py              # create app, include routers, error handlers, static /uploads
  config.py            # Settings (DB URL, JWT secret, token lifetimes, upload dir, limits)
  db.py                # engine, session, get_db dependency
  security.py          # hashing, JWT create/verify, current-user dependency, role checks
  errors.py            # AppError class + error codes + handlers
  constants/
    provinces.py       # fixed province list
    roles.py           # role codes
  models/              # one file per table group (SQLAlchemy)
  schemas/             # Pydantic request/response models, one file per resource
  services/            # business rules; no FastAPI imports here
    province.py        # get_room_province(), get_user_province()
  routers/             # one file per resource: auth, me, provinces, locations, buildings,
                       # floors, categories, rooms, room_photos, equipment, departments,
                       # divisions, positions, users, roles
alembic/
scripts/seed.py        # roles + first admin
tests/
uploads/               # photo files (not in git)
signatures/            # signature images (not in git, never served publicly)
```

**Environment variables**

| Name | Example | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `mysql+pymysql://app:pw@localhost:3306/rooms?charset=utf8mb4` |  |
| `JWT_SECRET` | 64 random characters | App must refuse to start if missing or shorter than 32 |
| `ACCESS_TOKEN_MINUTES` | `15` |  |
| `REFRESH_TOKEN_DAYS` | `7` |  |
| `UPLOAD_DIR` | `./uploads` | Created on start if missing |
| `SIGNATURE_DIR` | `./signatures` | Signature images (R19). Must not be inside `UPLOAD_DIR`, which is public. Created when the first signature is saved |
| `MAX_UPLOAD_MB` | `5` |  |
| `FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD`, `FIRST_ADMIN_STAFF_ID` |  | Used only by the seed script |
| `CORS_ORIGINS` | `https://rooms.company.com` | Comma separated |

## 4. API conventions

Every endpoint follows these rules unless its own section says otherwise.

**Paths and headers**

- Base path: `/api/v1`. Resource names are plural and lowercase. A room's photos and equipment live under `/rooms/{id}/photos` and `/rooms/{id}/equipment`.
- Every request except `GET /health`, `POST /auth/login` and `POST /auth/refresh` sends `Authorization: Bearer <access_token>`.
- Request and response bodies are JSON (`Content-Type: application/json`), except photo upload, which is `multipart/form-data`.
- Path ids are positive integers. A non-integer id returns 422; an unknown id returns 404.

**Lists**

- Paged lists accept `page` (default 1, minimum 1) and `size` (default 20, minimum 1, maximum 100). Out of range values return 422.
- A page past the end returns 200 with an empty `items` list and the real `total`.
- Paged list response: `{"items": [...], "page": 1, "size": 20, "total": 57}`.
- Small fixed lists (provinces, roles, a room's photos, a room's equipment) are not paged: `{"items": [...], "total": 6}`.
- Default order: `sort_order` ascending, then `name_en` ascending, then `id` ascending. Users: `name_en`, then `id`. Tables without `sort_order` skip that step.
- `is_active=true|false` filters by status. Without it, lists return both active and inactive records.
- `search` is trimmed; empty means no filter. It matches with `LIKE '%term%'` on the fields listed per endpoint. Escape `%`, `_` and `\` in the term so they match literally.
- Filters that take several ids use commas: `equipment_ids=1,4,7`. A value that is not an integer returns 422.

**Request bodies**

- Unknown fields return 422 (`extra="forbid"`).
- Strings are trimmed before validation. A required string that is empty after trimming returns 422. An optional string that is empty after trimming is saved as `null`.
- Length limits count characters, not bytes. Khmer text must be accepted.
- Server-set fields (`id`, `created_at`, `updated_at`, `last_login_at`, `password_hash`, `must_change_password`) are rejected with 422 if sent, except where an endpoint says otherwise.

**PATCH**

- Only the fields sent are changed. A field that is left out stays the same.
- Sending `null` clears an optional field. Sending `null` for a required field returns 422.
- An empty body `{}` returns 200 with the record unchanged and does not change `updated_at`.
- `updated_at` changes only when at least one value actually changes.

**Time**

- All datetimes are stored and returned in UTC, in ISO 8601 with a `Z`: `2026-10-21T02:15:00Z`.
- Room hours (`start_time`, `end_time`) are Cambodia local time (UTC+7, no daylight saving) and use `HH:MM`. Input `HH:MM:SS` is accepted; seconds are dropped.

**Bilingual names**

Every record with names returns both `name_en` and `name_kh`. The API never picks a language.

**Errors**

Every error uses one shape. `fields` appears only for field-level problems.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request.",
    "fields": { "province": "Must be a province code from GET /provinces." }
  }
}
```

FastAPI's default 422 body must be replaced by this shape. Field paths use dots for nesting (`items.0.id`). Unexpected server errors return 500 with code `INTERNAL_ERROR` and no stack trace. Section 17 lists every code.

**Methods not allowed**

There is no `DELETE` on any resource except `DELETE /rooms/{id}/photos/{photo_id}`. Other `DELETE` calls return 405.

## 5. Roles and permissions

Six fixed roles exist. Code checks the role `code`, never the display name. A user can have several roles.

| Code | Display name | What they can do in this scope | Province scope |
| --- | --- | --- | --- |
| `ADMIN` | Admin | Everything in this spec | All |
| `ROOM_OWNER` | Room owner | Edit rooms they own, their photos and equipment | Rooms where `room_owner_id` is their id |
| `STAFF` | Staff | Read places, rooms, equipment, organisation | All |
| `PITIKA` | Pitika | Same as Staff for now; duties come with bookings | Province of their department's location |
| `IT_LEAD` | IT Lead | Same as Staff for now; duties come with bookings | Province of their department's location |
| `IT_STAFF` | IT Staff | Same as Staff for now; duties come with bookings | Province of their department's location |

**Access labels**

| Label | Who passes |
| --- | --- |
| Public | Anyone, no token |
| Any | Any active, signed-in user, whatever their roles (a user with no roles passes) |
| Admin | Active user with `ADMIN` |
| Owner | Active user with `ROOM_OWNER` whose id equals that room's `room_owner_id` |
| Admin, Owner | Either of the two |

**Checks on every authenticated request, in this order**

1. Token present, valid signature, not expired, type `access` → else 401 `UNAUTHORIZED`.
2. User exists and `is_active` is true → else 401 `UNAUTHORIZED`.
3. Token's password fingerprint matches the user's current password (section 9) → else 401 `UNAUTHORIZED`.
4. If `must_change_password` is true and the endpoint is not one of `POST /auth/change-password`, `POST /auth/logout`, `GET /me` → 403 `PASSWORD_CHANGE_REQUIRED`.
5. Role check for the endpoint → else 403 `FORBIDDEN`.
6. Then load the record → 404 `NOT_FOUND` if missing.

Roles are read from the database on every request, not from the token, so role changes take effect immediately.

**How a province is found**

- Room: `rooms.floor_id` → `floors.building_id` → `buildings.location_id` → `locations.province`.
- User: `users.division_id` → `divisions.department_id` → `departments.location_id` → `locations.province`. A user without a division has no province (`null`).

## 6. Data model: places and rooms

These 8 tables follow the ERD (`User_Room_Final.drawio`) exactly; only types, limits and constraints are added here.

**Rules for every table**

- Engine InnoDB, charset `utf8mb4`, collation `utf8mb4_0900_ai_ci` (case- and accent-insensitive comparisons and unique checks).
- `id`: `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`.
- `created_at`, `updated_at`: `DATETIME NOT NULL`, set by the app in UTC. Every DB connection runs `SET time_zone = '+00:00'`.
- `is_active`: `BOOLEAN NOT NULL DEFAULT TRUE`.
- `sort_order`: `INT NOT NULL DEFAULT 0`, allowed range 0 to 9999.
- Every foreign key is `ON DELETE RESTRICT ON UPDATE RESTRICT`. Nothing is hard-deleted except `room_photos` rows.
- "text (N characters)" in the ERD means `VARCHAR(N)`.

**`locations`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `name_en` | `VARCHAR(100)` | No | Unique |
| `name_kh` | `VARCHAR(100)` | No |  |
| `description` | `VARCHAR(1000)` | Yes |  |
| `address` | `VARCHAR(200)` | Yes |  |
| `province` | `VARCHAR(30)` | No | Province code from section 8, e.g. `PHNOM_PENH`. Indexed |
| `map_query` | `VARCHAR(500)` | Yes | Free text for a map search, e.g. coordinates |
| `is_active`, `created_at`, `updated_at` |  |  | Common columns |

**`buildings`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `location_id` | `INT UNSIGNED` FK → `locations.id` | No | Indexed |
| `name_en` | `VARCHAR(100)` | No | Unique together with `location_id` |
| `name_kh` | `VARCHAR(100)` | No |  |
| `short_name` | `VARCHAR(20)` | Yes |  |
| `sort_order`, `is_active`, `created_at`, `updated_at` |  |  | Common columns |

**`floors`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `building_id` | `INT UNSIGNED` FK → `buildings.id` | No | Indexed |
| `floor_label` | `VARCHAR(100)` | No | e.g. "Ground floor", "3". Unique together with `building_id`. One label, not bilingual |
| `sort_order`, `is_active`, `created_at`, `updated_at` |  |  | Common columns |

**`categories`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `name_en` | `VARCHAR(100)` | No | Unique |
| `name_kh` | `VARCHAR(100)` | No |  |
| `sort_order`, `is_active`, `created_at`, `updated_at` |  |  | Common columns |

**`rooms`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `name_kh` | `VARCHAR(100)` | No |  |
| `name_en` | `VARCHAR(100)` | No | Unique together with `floor_id` |
| `door_code` | `VARCHAR(50)` | Yes | Secret. Never in normal responses |
| `short_desc` | `VARCHAR(200)` | Yes |  |
| `floor_id` | `INT UNSIGNED` FK → `floors.id` | No | Indexed |
| `category_id` | `INT UNSIGNED` FK → `categories.id` | No | Indexed |
| `room_owner_id` | `INT UNSIGNED` FK → `users.id` | Yes | Null = no-owner room. Indexed |
| `capacity` | `INT UNSIGNED` | No | 1 to 10000. `CHECK (capacity >= 1)` |
| `size_sqm` | `INT UNSIGNED` | Yes | 1 to 100000 when set |
| `description` | `VARCHAR(1000)` | Yes |  |
| `is_active` |  |  | Common column |
| `start_time` | `TIME` | No | Opening time, Cambodia local, same every day |
| `end_time` | `TIME` | No | `CHECK (start_time < end_time)`. Rooms do not stay open past midnight |
| `created_at`, `updated_at` |  |  | Common columns |

The ERD's `is_private` column is removed. Rooms have no `sort_order`; they sort by `name_en`, then `id`.

**`room_photos`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `room_id` | `INT UNSIGNED` FK → `rooms.id` | No | Indexed together with `sort_order` |
| `url` | `VARCHAR(3000)` | No | e.g. `/uploads/rooms/12/7f3c….jpg` |
| `thumbnail_url` | `VARCHAR(3000)` | No | e.g. `/uploads/rooms/12/7f3c…_thumb.jpg` |
| `sort_order` | `INT` | No | Common column |
| `created_at`, `updated_at` |  |  | Common columns. No `is_active`: photos are deleted for real |

**`equipment`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `name` | `VARCHAR(200)` | No | Unique. One name, not bilingual |
| `icon` | `VARCHAR(1000)` | Yes | Icon name or URL chosen by the client app |
| `sort_order`, `is_active`, `created_at`, `updated_at` |  |  | Common columns |

**`room_equipment`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `room_id` | `INT UNSIGNED` FK → `rooms.id` | No | Primary key part 1 |
| `equipment_id` | `INT UNSIGNED` FK → `equipment.id` | No | Primary key part 2. Indexed alone too |

No quantity and no timestamps: a room either has a piece of equipment or does not.

## 7. Data model: users, roles and organisation

These 6 tables follow the ERD, plus the three columns added for sign-in and roles. The rules for every table in section 6 apply here too.

**`departments`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `location_id` | `INT UNSIGNED` FK → `locations.id` | No | Indexed |
| `name_en` | `VARCHAR(100)` | No | Unique together with `location_id` |
| `name_kh` | `VARCHAR(100)` | No |  |
| `sort_order`, `is_active`, `created_at`, `updated_at` |  |  | Common columns |

**`divisions`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `department_id` | `INT UNSIGNED` FK → `departments.id` | No | Indexed |
| `name_en` | `VARCHAR(100)` | No | Unique together with `department_id` |
| `name_kh` | `VARCHAR(100)` | No |  |
| `short_name` | `VARCHAR(20)` | Yes |  |
| `sort_order`, `is_active`, `created_at`, `updated_at` |  |  | Common columns |

**`positions`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `name_en` | `VARCHAR(100)` | No | Unique |
| `name_kh` | `VARCHAR(100)` | No |  |
| `sort_order`, `is_active`, `created_at`, `updated_at` |  |  | Common columns |

**`users`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `staff_id` | `VARCHAR(20)` | No | Unique |
| `name_kh` | `VARCHAR(100)` | No |  |
| `name_en` | `VARCHAR(100)` | No |  |
| `title` | `VARCHAR(20)` | Yes | One of `Mr.`, `Ms.`, `Mrs.`, `Dr.` (exact), or null |
| `division_id` | `INT UNSIGNED` FK → `divisions.id` | Yes | Indexed. Needed for `PITIKA`, `IT_LEAD`, `IT_STAFF` |
| `position_id` | `INT UNSIGNED` FK → `positions.id` | No | Indexed |
| `email` | `VARCHAR(254)` | No | Unique. Stored lowercase |
| `secondary_email` | `VARCHAR(254)` | Yes | Stored lowercase. Must differ from `email` |
| `phone` | `VARCHAR(20)` | Yes | Free text, no format check beyond length |
| `avatar_url` | `VARCHAR(3000)` | Yes |  |
| `user_signature` | `VARCHAR(3000)` | Yes | **Added.** Path of the user's signature PNG inside `SIGNATURE_DIR`, e.g. `users/15/7f3c….png` (R19). Never returned; responses show `signature_url` |
| `email_notifications` | `BOOLEAN` | No | Default `TRUE`. Stored now, used by bookings later |
| `is_active` |  |  | Common column |
| `last_login_at` | `DATETIME` | Yes | Set on each successful login |
| `password_hash` | `VARCHAR(255)` | No | **Added.** Argon2id hash. Never returned |
| `must_change_password` | `BOOLEAN` | No | **Added.** Default `TRUE` |
| `created_at`, `updated_at` |  |  | Common columns |

**`roles`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `code` | `VARCHAR(50)` | No | **Added.** Unique. Never changes after seeding |
| `name_en` | `VARCHAR(100)` | No |  |
| `name_kh` | `VARCHAR(100)` | No |  |
| `is_active`, `created_at`, `updated_at` |  |  | Common columns. `is_active` stays true; the API cannot change it |

**`user_roles`**

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `user_id` | `INT UNSIGNED` FK → `users.id` | No | Primary key part 1 |
| `role_id` | `INT UNSIGNED` FK → `roles.id` | No | Primary key part 2. Indexed alone too |

The composite primary key stops the same role being given twice.

## 8. Seed data

`scripts/seed.py` creates the six roles, one position and the first Admin. It must be safe to run many times: it inserts what is missing and changes nothing that exists.

**Roles**

Khmer names are not decided yet. Load them from `scripts/seed_roles.json` so the client can fill them in without code changes; until then `name_kh` repeats `name_en`.

| Code | `name_en` | `name_kh` |
| --- | --- | --- |
| `ADMIN` | Admin | To be confirmed |
| `ROOM_OWNER` | Room owner | To be confirmed |
| `STAFF` | Staff | To be confirmed |
| `PITIKA` | Pitika | To be confirmed |
| `IT_LEAD` | IT Lead | To be confirmed |
| `IT_STAFF` | IT Staff | To be confirmed |

**First Admin**

`users.position_id` cannot be null, so the seed first creates the position "System Administrator" (`name_kh` the same until confirmed). It then creates the user from `FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD` and `FIRST_ADMIN_STAFF_ID` with role `ADMIN`, no division, and `must_change_password = true`. If any of the three variables is missing, the seed stops with a clear message. If a user with that email exists, it is left unchanged.

**Provinces**

Provinces are not a table. They live in `app/constants/provinces.py` as a fixed list, served by `GET /provinces` in this order (Phnom Penh first, then A to Z). `locations.province` stores the code. A native speaker should check the Khmer names before release.

| Code | `name_en` | `name_kh` |
| --- | --- | --- |
| `PHNOM_PENH` | Phnom Penh | ភ្នំពេញ |
| `BANTEAY_MEANCHEY` | Banteay Meanchey | បន្ទាយមានជ័យ |
| `BATTAMBANG` | Battambang | បាត់ដំបង |
| `KAMPONG_CHAM` | Kampong Cham | កំពង់ចាម |
| `KAMPONG_CHHNANG` | Kampong Chhnang | កំពង់ឆ្នាំង |
| `KAMPONG_SPEU` | Kampong Speu | កំពង់ស្ពឺ |
| `KAMPONG_THOM` | Kampong Thom | កំពង់ធំ |
| `KAMPOT` | Kampot | កំពត |
| `KANDAL` | Kandal | កណ្ដាល |
| `KEP` | Kep | កែប |
| `KOH_KONG` | Koh Kong | កោះកុង |
| `KRATIE` | Kratie | ក្រចេះ |
| `MONDULKIRI` | Mondulkiri | មណ្ឌលគិរី |
| `ODDAR_MEANCHEY` | Oddar Meanchey | ឧត្ដរមានជ័យ |
| `PAILIN` | Pailin | ប៉ៃលិន |
| `PREAH_SIHANOUK` | Preah Sihanouk | ព្រះសីហនុ |
| `PREAH_VIHEAR` | Preah Vihear | ព្រះវិហារ |
| `PREY_VENG` | Prey Veng | ព្រៃវែង |
| `PURSAT` | Pursat | ពោធិ៍សាត់ |
| `RATANAKIRI` | Ratanakiri | រតនគិរី |
| `SIEM_REAP` | Siem Reap | សៀមរាប |
| `STUNG_TRENG` | Stung Treng | ស្ទឹងត្រែង |
| `SVAY_RIENG` | Svay Rieng | ស្វាយរៀង |
| `TAKEO` | Takeo | តាកែវ |
| `TBONG_KHMUM` | Tbong Khmum | ត្បូងឃ្មុំ |

## 9. Authentication and security

Sign-in uses email and password, stateless JWT tokens, and a password fingerprint in each token so a password change or reset logs the user out everywhere.

**Passwords**

- Hash with Argon2id (`argon2-cffi` defaults). On a successful login, rehash if the library says the parameters are outdated.
- Rules for every new password (create user, reset, change): 8 to 128 characters, and not equal to the user's email. Any characters are allowed, including spaces and Khmer.
- Passwords are never trimmed, unlike other strings.
- Never log, return or echo a password or a hash.

**Tokens**

| Claim | Access token | Refresh token |
| --- | --- | --- |
| `sub` | User id as a string | Same |
| `type` | `access` | `refresh` |
| `iat`, `exp` | Lifetime `ACCESS_TOKEN_MINUTES` (15) | Lifetime `REFRESH_TOKEN_DAYS` (7) |
| `jti` | Random UUID | Random UUID |
| `pwd` | First 16 hex characters of SHA-256 of the user's current `password_hash` | Same |

- Signed with HS256 and `JWT_SECRET`. Roles are not in the token; they are read from the database on each request.
- A token is rejected if `pwd` no longer matches. This logs the user out on every device after a password change or reset, with no extra table.
- A refresh token cannot be used as an access token, and the reverse.
- Tokens are stateless: logout cannot revoke them on the server. A token stays valid until it expires, the password changes, or the user is deactivated. This is accepted for now.

**Login**

1. Trim and lowercase the email.
2. If no user has that email, still run a dummy Argon2 verify, so the response time does not reveal which emails exist.
3. Wrong email, wrong password and inactive user all return the same 401 `INVALID_CREDENTIALS`.
4. On success, set `last_login_at` to now and return both tokens and `must_change_password`.

**Login rate limit (should)**

After 5 failed logins for the same email from the same IP within 15 minutes, return 429 `RATE_LIMITED` with a `Retry-After` header until the window passes. An in-memory store is enough for one server process; note this limit in the README.

**Other security rules**

- `password_hash` never appears in any response, log or error message.
- `door_code` appears only in `GET /rooms/{id}/door-code` (section 13), never in room lists, room detail or logs.
- Photo files are served at `/uploads/...` without a token, because browser `<img>` tags cannot send one. File names are random UUIDs, so they cannot be guessed. Directory listing is off.
- Signature images are **not** under `/uploads`. They are served only by `GET /users/{id}/signature`, which needs a token (R19).
- CORS allows only the origins in `CORS_ORIGINS`.
- Database access goes through the ORM or bound parameters only; never build SQL by joining strings.
- Error responses never include stack traces or SQL.

## 10. Response shapes

Every endpoint returns one of these shapes. Build each as one Pydantic response model and reuse it; never return an ORM object directly. Optional fields are always present, with `null` when empty.

**Small references (used inside other shapes)**

```json
{
  "ProvinceRef": { "code": "PHNOM_PENH", "name_en": "Phnom Penh", "name_kh": "ភ្នំពេញ" },
  "NamedRef":    { "id": 3, "name_en": "IT Division", "name_kh": "ផ្នែកព័ត៌មានវិទ្យា" },
  "FloorRef":    { "id": 4, "floor_label": "3rd floor" },
  "BuildingRef": { "id": 1, "name_en": "Building A", "name_kh": "អគារ A", "short_name": "A" },
  "OwnerRef":    { "id": 15, "name_en": "Sok Dara", "name_kh": "សុខ ដារ៉ា" },
  "RoleRef":     { "code": "STAFF", "name_en": "Staff", "name_kh": "Staff" }
}
```

**Places**

```json
{
  "Location": {
    "id": 1, "name_en": "Head Office", "name_kh": "ការិយាល័យកណ្ដាល",
    "description": null, "address": "No. 12, Street 214", "province": "<ProvinceRef>",
    "map_query": "11.5564,104.9282", "is_active": true,
    "created_at": "2026-10-21T02:15:00Z", "updated_at": "2026-10-21T02:15:00Z"
  },
  "Building": {
    "id": 1, "location_id": 1, "name_en": "Building A", "name_kh": "អគារ A", "short_name": "A",
    "sort_order": 1, "is_active": true, "created_at": "...", "updated_at": "..."
  },
  "BuildingDetail": "Building + \"location\": <NamedRef> + \"province\": <ProvinceRef>",
  "Floor": {
    "id": 4, "building_id": 1, "floor_label": "3rd floor", "sort_order": 3,
    "is_active": true, "created_at": "...", "updated_at": "..."
  },
  "FloorDetail": "Floor + \"building\": <BuildingRef> + \"location\": <NamedRef> + \"province\": <ProvinceRef>",
  "Category": {
    "id": 2, "name_en": "Meeting room", "name_kh": "បន្ទប់ប្រជុំ", "sort_order": 1,
    "is_active": true, "created_at": "...", "updated_at": "..."
  }
}
```

**Rooms, photos, equipment**

```json
{
  "RoomListItem": {
    "id": 12, "name_en": "Mekong Room", "name_kh": "បន្ទប់មេគង្គ", "short_desc": "Bright room with a river view",
    "capacity": 12, "size_sqm": 40, "start_time": "08:00", "end_time": "18:00",
    "category": "<NamedRef>", "floor": "<FloorRef>", "building": "<BuildingRef>",
    "location": "<NamedRef>", "province": "<ProvinceRef>", "owner": "<OwnerRef or null>",
    "cover_photo": { "url": "/uploads/rooms/12/7f3c.jpg", "thumbnail_url": "/uploads/rooms/12/7f3c_thumb.jpg" },
    "is_active": true, "is_bookable": true
  },
  "RoomDetail": "RoomListItem + \"description\" + \"photos\": [<Photo>] + \"equipment\": [<Equipment>] + \"created_at\" + \"updated_at\"",
  "Photo": {
    "id": 31, "room_id": 12, "url": "/uploads/rooms/12/7f3c.jpg", "thumbnail_url": "/uploads/rooms/12/7f3c_thumb.jpg",
    "sort_order": 1, "created_at": "...", "updated_at": "..."
  },
  "Equipment": {
    "id": 5, "name": "Projector", "icon": "projector", "sort_order": 2,
    "is_active": true, "created_at": "...", "updated_at": "..."
  },
  "DoorCode": { "room_id": 12, "door_code": "4821#" }
}
```

- `cover_photo` is the photo with the lowest `sort_order`, or `null` when the room has none.
- `is_bookable` is computed (rule R12 in section 15); it is never stored.
- `door_code` is in no shape except `DoorCode`.

**Organisation, users, roles, tokens**

```json
{
  "Department": {
    "id": 1, "location_id": 1, "name_en": "Operations", "name_kh": "ប្រតិបត្តិការ", "sort_order": 1,
    "is_active": true, "created_at": "...", "updated_at": "..."
  },
  "Division": {
    "id": 3, "department_id": 1, "name_en": "IT Division", "name_kh": "ផ្នែកព័ត៌មានវិទ្យា", "short_name": "IT",
    "sort_order": 1, "is_active": true, "created_at": "...", "updated_at": "..."
  },
  "Position": {
    "id": 5, "name_en": "Manager", "name_kh": "ប្រធាន", "sort_order": 1,
    "is_active": true, "created_at": "...", "updated_at": "..."
  },
  "Role": { "id": 1, "code": "ADMIN", "name_en": "Admin", "name_kh": "Admin", "is_active": true },
  "UserListItem": {
    "id": 15, "staff_id": "EMP-00123", "title": "Mr.", "name_en": "Sok Dara", "name_kh": "សុខ ដារ៉ា",
    "email": "sok.dara@company.com", "division": "<NamedRef or null>", "position": "<NamedRef>",
    "province": "<ProvinceRef or null>", "role_codes": ["STAFF", "PITIKA"],
    "is_active": true, "last_login_at": "2026-10-21T01:45:00Z"
  },
  "UserDetail": {
    "id": 15, "staff_id": "EMP-00123", "title": "Mr.", "name_en": "Sok Dara", "name_kh": "សុខ ដារ៉ា",
    "email": "sok.dara@company.com", "secondary_email": null, "phone": "012 345 678", "avatar_url": null,
    "signature_url": "/api/v1/users/15/signature",
    "email_notifications": true,
    "division": "<NamedRef or null>", "department": "<NamedRef or null>", "position": "<NamedRef>",
    "province": "<ProvinceRef or null>", "roles": ["<RoleRef>"], "owned_room_ids": [12, 14],
    "is_active": true, "must_change_password": false, "last_login_at": "2026-10-21T01:45:00Z",
    "created_at": "...", "updated_at": "..."
  },
  "Tokens": {
    "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer",
    "expires_in": 900, "must_change_password": false
  }
}
```

- `GET /me` returns `UserDetail` for the signed-in user.
- `signature_url` is the link to `GET /users/{id}/signature`, or `null` when the user has no signature (R19). The stored file path is never returned.
- Changes to users or roles that clear room owners add `"rooms_unassigned": [12, 14]` to the `UserDetail` response (rule R9). The list is empty when nothing was cleared.
- `roles` and `role_codes` are sorted in the seed order: `ADMIN`, `ROOM_OWNER`, `STAFF`, `PITIKA`, `IT_LEAD`, `IT_STAFF`.

## 11. Endpoints: auth and current user

Eight endpoints. Rule numbers (R1…) refer to section 15; error codes to section 17.

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| POST | `/auth/login` | Public | 200 `Tokens` | 401 `INVALID_CREDENTIALS`, 422, 429 `RATE_LIMITED` |
| POST | `/auth/refresh` | Public | 200 `Tokens` | 401 `UNAUTHORIZED`, 422 |
| POST | `/auth/change-password` | Any (allowed while `must_change_password`) | 200 `Tokens` | 400 `WRONG_PASSWORD`, 422 |
| POST | `/auth/logout` | Any (allowed while `must_change_password`) | 204 | 401 |
| GET | `/me` | Any (allowed while `must_change_password`) | 200 `UserDetail` | 401 |
| PATCH | `/me` | Any | 200 `UserDetail` | 403 `PASSWORD_CHANGE_REQUIRED`, 422 |
| PUT | `/me/signature` | Any | 200 `UserDetail` | 403 `PASSWORD_CHANGE_REQUIRED`, 413, 415, 422 |
| DELETE | `/me/signature` | Any | 204 | 403 `PASSWORD_CHANGE_REQUIRED` |

**`POST /auth/login`**

```json
{ "email": "sok.dara@company.com", "password": "MyPassword@123" }
```

Both required. The email is trimmed and lowercased before lookup. See section 9 for the login steps.

**`POST /auth/refresh`**

```json
{ "refresh_token": "eyJ..." }
```

Returns a new access token and a new refresh token. Rejected with 401 if the token is not type `refresh`, is expired, the user is inactive, or the password fingerprint no longer matches.

**`POST /auth/change-password`**

```json
{ "current_password": "Welcome@2026", "new_password": "MyNewPassword@123" }
```

- Wrong `current_password` → 400 `WRONG_PASSWORD`.
- `new_password` must follow R18 and must differ from `current_password` → else 422.
- On success: save the new hash, set `must_change_password = false`, and return fresh `Tokens`. The old tokens stop working because the password fingerprint changed, so the client must switch to the new tokens.

**`POST /auth/logout`**

```json
{ "refresh_token": "eyJ..." }
```

The body is optional. Returns 204. Tokens are stateless, so nothing is revoked on the server; the client deletes its tokens.

**`PATCH /me`**

Only these four fields are allowed; any other field returns 422.

```json
{
  "secondary_email": "dara.personal@gmail.com",
  "phone": "012 345 678",
  "avatar_url": "https://cdn.company.com/avatars/15.jpg",
  "email_notifications": false
}
```

| Field | Rule |
| --- | --- |
| `secondary_email` | Valid email, max 254, saved lowercase, must differ from `email` (R5). `null` clears it |
| `phone` | Max 20 characters. `null` clears it |
| `avatar_url` | Max 3000 characters, must start with `http://`, `https://` or `/`. `null` clears it |
| `email_notifications` | `true` or `false`; `null` is rejected |

## 12. Endpoints: locations, buildings, floors & categories

Everyone signed in can read these; only Admin creates or changes them. Every `PATCH` accepts the same fields as `POST` (all optional) plus `is_active`.

### Provinces

| Method | Path | Access | Success | Notes |
| --- | --- | --- | --- | --- |
| GET | `/provinces` | Any | 200 `{items: [ProvinceRef], total: 25}` | Not paged; ignores `page`, `size`, `is_active` |

### Locations

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/locations` | Any | 200 paged `Location` | 422 |
| GET | `/locations/{id}` | Any | 200 `Location` | 404 |
| POST | `/locations` | Admin | 201 `Location` | 409 `DUPLICATE`, 422 |
| PATCH | `/locations/{id}` | Admin | 200 `Location` | 404, 409, 422 |

List filters: `province` (code; unknown code → 422), `is_active`, `search` (`name_en`, `name_kh`, `address`).

```json
{
  "name_en": "Siem Reap Branch",
  "name_kh": "សាខាសៀមរាប",
  "description": "Branch office near the city center",
  "address": "Sivatha Blvd, Siem Reap",
  "province": "SIEM_REAP",
  "map_query": "13.3633,103.8564"
}
```

Required: `name_en`, `name_kh`, `province` (R1). Optional: `description`, `address`, `map_query`.

### Buildings

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/buildings` | Any | 200 paged `Building` | 422 |
| GET | `/buildings/{id}` | Any | 200 `BuildingDetail` | 404 |
| POST | `/buildings` | Admin | 201 `BuildingDetail` | 409, 422 |
| PATCH | `/buildings/{id}` | Admin | 200 `BuildingDetail` | 404, 409, 422 |

List filters: `location_id`, `is_active`, `search` (`name_en`, `name_kh`, `short_name`).

```json
{ "location_id": 1, "name_en": "Building C", "name_kh": "អគារ C", "short_name": "C", "sort_order": 3 }
```

Required: `location_id` (must exist and be active, R2), `name_en`, `name_kh`. Optional: `short_name`, `sort_order` (default 0). Changing `location_id` moves the building with its floors and rooms.

### Floors

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/floors` | Any | 200 paged `Floor` | 422 |
| GET | `/floors/{id}` | Any | 200 `FloorDetail` | 404 |
| POST | `/floors` | Admin | 201 `FloorDetail` | 409, 422 |
| PATCH | `/floors/{id}` | Admin | 200 `FloorDetail` | 404, 409, 422 |

List filters: `building_id`, `location_id`, `is_active`, `search` (`floor_label`).

```json
{ "building_id": 1, "floor_label": "3rd floor", "sort_order": 3 }
```

Required: `building_id` (must exist and be active, R2), `floor_label`. Optional: `sort_order`.

Deactivating a location, building or floor does not change its children, but makes every room inside it unbookable (R12).

### Categories

Categories say what kind of room it is, for example a meeting room or a training room.

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/categories` | Any | 200 paged `Category` | 422 |
| GET | `/categories/{id}` | Any | 200 `Category` | 404 |
| POST | `/categories` | Admin | 201 `Category` | 409, 422 |
| PATCH | `/categories/{id}` | Admin | 200 `Category` | 404, 409, 422 |

List filters: `is_active`, `search` (`name_en`, `name_kh`).

```json
{ "name_en": "Training room", "name_kh": "បន្ទប់បណ្ដុះបណ្ដាល", "sort_order": 2 }
```

Required: `name_en`, `name_kh`. Optional: `sort_order`. Deactivating a category leaves existing rooms in it unchanged; new rooms cannot use it (R2).

## 13. Endpoints: rooms, photos & equipment

Admin manages all rooms; a room owner manages only their own rooms, with a smaller set of fields.

### Rooms

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/rooms` | Any | 200 paged `RoomListItem` | 422 |
| GET | `/rooms/{id}` | Any | 200 `RoomDetail` | 404 |
| POST | `/rooms` | Admin | 201 `RoomDetail` | 409, 422 |
| PATCH | `/rooms/{id}` | Admin, Owner | 200 `RoomDetail` | 403, 404, 409, 422 |
| GET | `/rooms/{id}/door-code` | Admin, Owner | 200 `DoorCode` | 403, 404 |

**List filters** (all optional, combined with AND)

| Parameter | Meaning |
| --- | --- |
| `province` | Province code of the room's location |
| `location_id`, `building_id`, `floor_id`, `category_id` | Exact match |
| `min_capacity` | `capacity >= value`; integer 1 or more |
| `equipment_ids` | Comma list; room must have every one |
| `owner_id` | Rooms owned by that user |
| `has_owner` | `true` = owned rooms, `false` = no-owner rooms |
| `is_active` | The room's own flag |
| `is_bookable` | Computed flag (R12) |
| `search` | `name_en`, `name_kh`, `short_desc` |

**`POST /rooms`**

```json
{
  "name_en": "Mekong Room",
  "name_kh": "បន្ទប់មេគង្គ",
  "floor_id": 4,
  "category_id": 2,
  "capacity": 12,
  "size_sqm": 40,
  "start_time": "08:00",
  "end_time": "18:00",
  "short_desc": "Bright room with a river view",
  "description": "Has a 75-inch screen and a whiteboard.",
  "door_code": "4821#",
  "room_owner_id": 15
}
```

| Field | Required | Rule |
| --- | --- | --- |
| `name_en`, `name_kh` | Yes | Max 100. `name_en` unique per floor (R4) |
| `floor_id`, `category_id` | Yes | Must exist and be active (R2) |
| `capacity` | Yes | Integer 1 to 10000 |
| `start_time`, `end_time` | Yes | `HH:MM`; start before end (R13) |
| `size_sqm` | No | Integer 1 to 100000 |
| `short_desc` | No | Max 200 |
| `description` | No | Max 1000 |
| `door_code` | No | Max 50. Write-only: accepted here, never returned except by the door-code endpoint |
| `room_owner_id` | No | Null or missing = no-owner room. Else R7 |

**`PATCH /rooms/{id}`**

- Admin may change every field above plus `is_active`.
- Owner may change only: `name_en`, `name_kh`, `short_desc`, `description`, `capacity`, `size_sqm`, `start_time`, `end_time`, `door_code`, `category_id`. Sending `floor_id`, `room_owner_id` or `is_active` returns 403 `FORBIDDEN` and changes nothing (R8).
- Sending only one of `start_time` / `end_time` is checked against the stored other value (R13).

**`GET /rooms/{id}/door-code`** returns `{ "room_id": 12, "door_code": "4821#" }`, or `"door_code": null` when none is set.

### Room photos

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/rooms/{id}/photos` | Any | 200 `{items: [Photo], total}` | 404 |
| POST | `/rooms/{id}/photos` | Admin, Owner | 201 `Photo` | 403, 404, 409 `PHOTO_LIMIT_REACHED`, 413 `FILE_TOO_LARGE`, 415 `UNSUPPORTED_FILE_TYPE`, 422 `INVALID_IMAGE` |
| PUT | `/rooms/{id}/photos/order` | Admin, Owner | 200 `{items: [Photo], total}` | 403, 404, 422 |
| DELETE | `/rooms/{id}/photos/{photo_id}` | Admin, Owner | 204 | 403, 404 |

**Upload** is `multipart/form-data` with one field, `file`, holding one image. Steps, in order:

1. Room must exist (404). Count its photos; 20 or more → 409 `PHOTO_LIMIT_REACHED`.
2. Read at most `MAX_UPLOAD_MB` + 1 byte; more → 413. Empty file → 422 `INVALID_IMAGE`.
3. Open with Pillow, with `Image.MAX_IMAGE_PIXELS = 40_000_000`. Not an image, broken, or too many pixels → 422 `INVALID_IMAGE`. A format other than JPEG, PNG or WebP → 415. Decide by the file's content, never by its name or `Content-Type`.
4. Apply EXIF rotation, then drop all metadata. Animated images keep only the first frame.
5. Save the main image as JPEG, quality 85, longest side at most 2560 px. Transparent areas become white.
6. Save a thumbnail as JPEG, longest side 400 px.
7. File names: `UPLOAD_DIR/rooms/{room_id}/{uuid4}.jpg` and `{uuid4}_thumb.jpg`. The client's file name is ignored.
8. Insert the row with `sort_order` = current highest + 1 (1 for the first photo). If the insert fails, delete both files.

**Reorder**: `{ "photo_ids": [33, 31, 32] }`. The list must contain every photo of that room exactly once, else 422. Sets `sort_order` to 1, 2, 3… in that order.

**Delete** removes the row, then both files. The photo must belong to that room, else 404. A file already missing on disk is logged as a warning and still returns 204. Other photos keep their `sort_order` (gaps are fine).

### Room equipment

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/rooms/{id}/equipment` | Any | 200 `{items: [Equipment], total}` | 404 |
| PUT | `/rooms/{id}/equipment` | Admin, Owner | 200 `{items: [Equipment], total}` | 403, 404, 422 |

`PUT` body: `{ "equipment_ids": [1, 4, 7] }`. It replaces the whole set in one transaction. Rules in R15.

### Equipment

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/equipment` | Any | 200 paged `Equipment` | 422 |
| GET | `/equipment/{id}` | Any | 200 `Equipment` | 404 |
| POST | `/equipment` | Admin | 201 `Equipment` | 409, 422 |
| PATCH | `/equipment/{id}` | Admin | 200 `Equipment` | 404, 409, 422 |

List filters: `is_active`, `search` (`name`).

```json
{ "name": "Projector", "icon": "projector", "sort_order": 2 }
```

Required: `name` (max 200, unique). Optional: `icon` (max 1000), `sort_order`. Deactivating equipment keeps it on rooms that already have it; it cannot be added again (R15).

## 14. Endpoints: users, roles & organisation

Only Admin manages accounts, roles and the organisation tree; everyone signed in can read departments, divisions and positions.

### Departments

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/departments` | Any | 200 paged `Department` | 422 |
| GET | `/departments/{id}` | Any | 200 `Department` | 404 |
| POST | `/departments` | Admin | 201 `Department` | 409, 422 |
| PATCH | `/departments/{id}` | Admin | 200 `Department` | 404, 409, 422 |

List filters: `location_id`, `is_active`, `search` (`name_en`, `name_kh`).

```json
{ "location_id": 1, "name_en": "Operations", "name_kh": "ប្រតិបត្តិការ", "sort_order": 1 }
```

Required: `location_id` (exists, active, R2), `name_en`, `name_kh`. Changing `location_id` changes the province of every user in its divisions.

### Divisions

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/divisions` | Any | 200 paged `Division` | 422 |
| GET | `/divisions/{id}` | Any | 200 `Division` | 404 |
| POST | `/divisions` | Admin | 201 `Division` | 409, 422 |
| PATCH | `/divisions/{id}` | Admin | 200 `Division` | 404, 409, 422 |

List filters: `department_id`, `is_active`, `search` (`name_en`, `name_kh`, `short_name`).

```json
{ "department_id": 1, "name_en": "IT Division", "name_kh": "ផ្នែកព័ត៌មានវិទ្យា", "short_name": "IT", "sort_order": 1 }
```

Required: `department_id` (exists, active, R2), `name_en`, `name_kh`. Optional: `short_name` (max 20), `sort_order`.

### Positions

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/positions` | Any | 200 paged `Position` | 422 |
| GET | `/positions/{id}` | Any | 200 `Position` | 404 |
| POST | `/positions` | Admin | 201 `Position` | 409, 422 |
| PATCH | `/positions/{id}` | Admin | 200 `Position` | 404, 409, 422 |

List filters: `is_active`, `search` (`name_en`, `name_kh`). Body: `{ "name_en": "Manager", "name_kh": "ប្រធាន", "sort_order": 1 }`; `name_en` and `name_kh` required.

### Users

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/users` | Admin | 200 paged `UserListItem` | 403, 422 |
| GET | `/users/{id}` | Admin | 200 `UserDetail` | 403, 404 |
| POST | `/users` | Admin | 201 `UserDetail` | 403, 409, 422 |
| PATCH | `/users/{id}` | Admin | 200 `UserDetail` + `rooms_unassigned` | 403, 404, 409, 422 |
| POST | `/users/{id}/reset-password` | Admin | 204 | 403, 404, 422 |
| PUT | `/users/{id}/roles` | Admin | 200 `UserDetail` + `rooms_unassigned` | 403, 404, 409, 422 |
| GET | `/users/{id}/signature` | Any | 200 `image/png` | 404 |
| PUT | `/users/{id}/signature` | Admin | 200 `UserDetail` | 403, 404, 413, 415, 422 |
| DELETE | `/users/{id}/signature` | Admin | 204 | 403, 404 |

List filters: `division_id`, `department_id`, `position_id`, `role` (code), `province` (code), `is_active`, `search` (`name_en`, `name_kh`, `staff_id`, `email`). An unknown role or province code → 422.

**`POST /users`**

```json
{
  "staff_id": "EMP-00150",
  "title": "Ms.",
  "name_en": "Chan Sreymom",
  "name_kh": "ចាន់ ស្រីមុំ",
  "email": "Chan.Sreymom@Company.com",
  "secondary_email": null,
  "phone": "098 765 432",
  "avatar_url": null,
  "division_id": 3,
  "position_id": 7,
  "email_notifications": true,
  "temporary_password": "Welcome@2026"
}
```

| Field | Required | Rule |
| --- | --- | --- |
| `staff_id` | Yes | Max 20, unique (R5) |
| `name_en`, `name_kh` | Yes | Max 100 |
| `email` | Yes | Valid email, max 254, saved lowercase, unique (R5) |
| `position_id` | Yes | Exists and active (R2) |
| `temporary_password` | Yes | R18. Not trimmed |
| `division_id` | No | Exists and active (R2) |
| `title` | No | One of `Mr.`, `Ms.`, `Mrs.`, `Dr.`; anything else → 422 |
| `secondary_email` | No | Valid, max 254, lowercase, differs from `email` |
| `phone` | No | Max 20 |
| `avatar_url` | No | Max 3000, starts with `http://`, `https://` or `/` |
| `email_notifications` | No | Default `true` |

The new user has no roles and `must_change_password = true`. Roles are set with `PUT /users/{id}/roles`.

**`PATCH /users/{id}`** accepts every field above except `temporary_password`, plus `is_active`. Rules that can block it: R6 (removing a needed division), R10 (last admin), R11 (deactivating yourself). Deactivating a user clears their rooms (R9).

**`POST /users/{id}/reset-password`**: `{ "temporary_password": "Reset@2026" }`. Sets the new hash and `must_change_password = true`. The user's old tokens stop working (section 9). Works on inactive users too.

**`PUT /users/{id}/roles`**: `{ "role_codes": ["STAFF", "IT_STAFF"] }`. Replaces all roles in one transaction. Duplicates are ignored, unknown codes → 422, `[]` removes every role. Checked against R6, R9, R10 and R11.

**Signatures** (R19). Each user can have one signature image, printed on booking approval forms when bookings arrive. Best results: sign with a dark pen on blank white paper, in good light. A user sets their own with `PUT /me/signature`; the Admin sets anyone's with `PUT /users/{id}/signature`. Both take `multipart/form-data` with one field, `file`. Steps, in order:

1. Read and check the file exactly like a room photo (section 13, upload steps 2 and 3): at most `MAX_UPLOAD_MB`, JPEG, PNG or WebP by content, at most 40 million pixels.
2. Apply EXIF rotation, then drop all metadata.
3. Make the paper transparent. Judge each pixel against the paper around it (the lightest nearby area, so grey paper and shadows in phone photos count as paper): darker than its paper by 80 or more (on a 0–255 scale) stays opaque, by 25 or less becomes transparent, and values between fade, so stroke edges stay smooth. Existing transparency is kept.
4. Make the ink pure black (`#000000`), whatever the pen colour; only its opacity varies, at stroke edges. The result is black and white: black ink on transparent paper, which reads as black on white on a form.
5. Crop to the ink, ignoring faint pixels (opacity below 25%). If nothing is left (a blank page) → 422 `INVALID_IMAGE` "No signature found in the image."
6. Scale down to fit 600 × 300 px (never up) and save as PNG: `SIGNATURE_DIR/users/{user_id}/{uuid4}.png`.
7. Save the path in `users.user_signature`, then delete the file it replaces. If saving the path fails, delete the new file and keep the old signature.

`DELETE` clears the signature and deletes its file; it returns 204 even when there was none. `GET /users/{id}/signature` returns the PNG with `Cache-Control: private, no-cache` to any signed-in user, also for inactive users (old approvals still show it). It returns 404 when the user has no signature, or when its file is missing on disk (logged as a warning).

### Roles

| Method | Path | Access | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/roles` | Admin | 200 `{items: [Role], total: 6}` | 403 |
| PATCH | `/roles/{id}` | Admin | 200 `Role` | 403, 404, 422 |

`PATCH` accepts only `name_en` and `name_kh`. Sending `code` or `is_active` → 422 (R17). There is no `POST`: roles come only from the seed.

## 15. Business rules

Eighteen rules, each enforced in a service function inside a database transaction and covered by tests. Endpoint sections refer to them by number.

| # | Rule | Error when broken |
| --- | --- | --- |
| R1 | `locations.province` and every `province` filter must be a code from the fixed list (section 8). | 422 `VALIDATION_ERROR` |
| R2 | A referenced record (`location_id`, `building_id`, `floor_id`, `category_id`, `department_id`, `division_id`, `position_id`) must exist and be active when it is set on create, or changed on update. Keeping an existing reference that later became inactive is allowed. | Missing: 422 `VALIDATION_ERROR` on that field. Inactive: 409 `INACTIVE_REFERENCE` |
| R3 | Deactivating never cascades to children. Reactivating a record whose parent is inactive is refused (a building under an inactive location, a floor under an inactive building, a room on an inactive floor, a department under an inactive location, a division under an inactive department). | 409 `INACTIVE_REFERENCE` |
| R4 | Names are unique (case- and accent-insensitive): location `name_en`; building `name_en` per location; floor `floor_label` per building; category `name_en`; room `name_en` per floor; equipment `name`; department `name_en` per location; division `name_en` per department; position `name_en`. Enforce with database unique keys, and turn a race-condition `IntegrityError` into the same error. | 409 `DUPLICATE`, with the field in `fields` |
| R5 | User `email` and `staff_id` are unique. Emails are trimmed and saved lowercase. `secondary_email` must differ from `email`. | 409 `DUPLICATE`; 422 for the secondary email |
| R6 | A user with `PITIKA`, `IT_LEAD` or `IT_STAFF` must have a `division_id`. Checked when roles are set and when the division is removed. | 409 `DIVISION_REQUIRED` |
| R7 | A room's `room_owner_id`, when set or changed, must be an existing user who is active and has `ROOM_OWNER`. | Missing user: 422. Otherwise 409 `OWNER_INVALID` |
| R8 | A room owner edits only rooms where they are the owner, and only the fields listed in section 13. | 403 `FORBIDDEN` |
| R9 | When a user is deactivated, or loses `ROOM_OWNER`, every room they own gets `room_owner_id = NULL` in the same transaction. The response lists those room ids in `rooms_unassigned`. Reactivating the user or giving the role back does not restore them. | None; this always succeeds |
| R10 | There must always be at least one active user with `ADMIN`. A change that would leave none (deactivating or removing `ADMIN` from the last one) is refused. Lock the admin rows (`SELECT … FOR UPDATE`) while checking. | 409 `LAST_ADMIN` |
| R11 | An Admin cannot deactivate their own account or remove `ADMIN` from their own roles. Checked before R10. | 409 `SELF_ACTION_NOT_ALLOWED` |
| R12 | `is_bookable` is true only when the room, its floor, its building and its location are all active. Category status does not matter. Computed in SQL for the `is_bookable` filter. | Not an error |
| R13 | `start_time` must be earlier than `end_time` (equal is refused). On `PATCH`, compare with the stored value of the field not sent. | 422 `VALIDATION_ERROR` |
| R14 | A room has at most 20 photos. Files are at most `MAX_UPLOAD_MB` (5 MB), JPEG, PNG or WebP by content, at most 40 million pixels. | 409 `PHOTO_LIMIT_REACHED`, 413, 415, 422 `INVALID_IMAGE` |
| R15 | `PUT /rooms/{id}/equipment`: duplicate ids are removed; every id must exist; an id the room does not already have must be active. Inactive equipment the room already has may stay. | Missing: 422 listing the ids. Inactive new id: 409 `INACTIVE_REFERENCE` |
| R16 | While `must_change_password` is true, only `POST /auth/change-password`, `POST /auth/logout` and `GET /me` work. | 403 `PASSWORD_CHANGE_REQUIRED` |
| R17 | Roles are only the six seeded ones. Their `code` and `is_active` never change through the API; there is no create or deactivate. | 422 `VALIDATION_ERROR` |
| R18 | New passwords are 8 to 128 characters, not equal to the user's email, and not trimmed. A changed password must differ from the current one. | 422 `VALIDATION_ERROR` |
| R19 | A user has at most one signature image, cleaned as in section 14 (upright, no metadata, black ink on transparent paper, cropped, at most 600 × 300 px PNG). It is stored outside `UPLOAD_DIR` and served only to signed-in users. A user changes only their own; the Admin changes anyone's. | 413, 415, 422 `INVALID_IMAGE`, 403 |

## 16. Edge cases

Each row is one test: the situation and the exact expected result. Build every one.

### Sign-in and tokens

| Case | Expected |
| --- | --- |
| Login with `"  Sok.Dara@Company.COM "` | Works; email is trimmed and lowercased |
| Login with an email that does not exist | 401 `INVALID_CREDENTIALS`, same message and similar time as a wrong password |
| Login as an inactive user with the right password | 401 `INVALID_CREDENTIALS` |
| Password with a leading or trailing space | Kept as typed; `" abc12345"` and `"abc12345"` are different passwords |
| 6th failed login in 15 minutes for the same email and IP | 429 `RATE_LIMITED` with `Retry-After` |
| Refresh token sent as `Authorization` bearer | 401 `UNAUTHORIZED` |
| Access token sent to `/auth/refresh` | 401 `UNAUTHORIZED` |
| Expired, malformed, or wrongly signed token | 401 `UNAUTHORIZED` |
| Token of a user deactivated after it was issued | 401 on the very next request |
| Old token after the user changes their password | 401; the change-password response carries the new tokens |
| Old token after an Admin resets the password | 401 |
| Admin resets their own password | 204; their current token stops working and they must log in again |
| User with `must_change_password` calls `GET /rooms` | 403 `PASSWORD_CHANGE_REQUIRED` |
| User with `must_change_password` calls `GET /me` or `POST /auth/change-password` | Works |
| Change password with a wrong current password | 400 `WRONG_PASSWORD` |
| New password equals the current one, or equals the email | 422 |
| Password of 7 characters, or 129 characters | 422 |
| User's roles change while their token is valid | New roles apply on the next request |
| User with no roles at all | Can sign in and read everything marked Any |

### Requests and lists

| Case | Expected |
| --- | --- |
| Unknown field in a body, e.g. `{"name": "x"}` on a location | 422, field named in `fields` |
| Server-set field in a body, e.g. `id` or `created_at` | 422 |
| Required string that is only spaces | 422 |
| Optional string that is only spaces | Saved as `null` |
| Khmer text of exactly 100 characters in `name_kh` | Accepted (limits count characters, not bytes) |
| `name_en` of 101 characters | 422 |
| `PATCH` with `{}` | 200, nothing changes, `updated_at` unchanged |
| `PATCH` sets a field to its current value | 200, `updated_at` unchanged |
| `PATCH` sends `null` for a required field | 422 |
| Path id `abc` or `-1` | 422 |
| Path id that does not exist | 404 `NOT_FOUND` |
| `size=0`, `size=101`, `page=0` | 422 |
| `page` past the last page | 200, `items: []`, real `total` |
| `search=50%` or `search=a_b` | `%` and `_` match literally |
| `search="   "` | Treated as no search |
| `equipment_ids=1,x` | 422 |
| `province=MARS` | 422 |
| `DELETE /locations/1` | 405 |
| Malformed JSON body | 422 |

### Places and organisation

| Case | Expected |
| --- | --- |
| Create a building under an inactive location | 409 `INACTIVE_REFERENCE` |
| Create a building with a `location_id` that does not exist | 422, field `location_id` |
| Two buildings named "Building A" in the same location | 409 `DUPLICATE` |
| "Building A" and "building a" in the same location | 409 `DUPLICATE` (case-insensitive) |
| "Building A" in two different locations | Allowed |
| Deactivate a location that has active buildings | Allowed; buildings stay active; their rooms become `is_bookable: false` |
| Reactivate a building whose location is inactive | 409 `INACTIVE_REFERENCE` |
| Move a building to another location | Allowed if the new location is active; its rooms now report the new province |
| Edit a building whose location is now inactive, without changing `location_id` | Allowed (R2 only checks references that change) |
| Move a department to another location | Province of its divisions' users changes |
| Deactivate a division that has users | Allowed; users keep it; new users cannot be put in it |
| Deactivate a category used by rooms | Allowed; rooms keep it; new or moved rooms cannot use it |

### Rooms

| Case | Expected |
| --- | --- |
| `start_time` equal to `end_time`, or later | 422 |
| `PATCH` only `end_time` to a time before the stored `start_time` | 422 |
| `start_time: "8:00"`, `"08:00:30"`, `"24:00"` | `"8:00"` and `"08:00:30"` accepted as 08:00; `"24:00"` → 422 |
| `capacity: 0` or `10001` | 422 |
| `room_owner_id` of a user without `ROOM_OWNER`, or inactive | 409 `OWNER_INVALID` |
| `room_owner_id: null` on `PATCH` | Room becomes a no-owner room |
| Owner edits a room owned by someone else | 403 `FORBIDDEN` |
| Owner sends `room_owner_id`, `floor_id` or `is_active` | 403 `FORBIDDEN`, nothing changes |
| Owner who lost `ROOM_OWNER` (rooms already cleared) edits their old room | 403 `FORBIDDEN` |
| Staff calls `GET /rooms/{id}/door-code` | 403 `FORBIDDEN` |
| `door_code` anywhere in `GET /rooms` or `GET /rooms/{id}` | Must never appear (test the raw JSON) |
| Room with no photos | `cover_photo: null`, `photos: []` |
| `GET /rooms?is_bookable=true` with an inactive building | Rooms in that building are excluded |
| `equipment_ids=1,4` | Only rooms having both 1 and 4 |
| Move a room to another floor with the same room name | 409 `DUPLICATE` |

### Photos and equipment

| Case | Expected |
| --- | --- |
| Upload the 21st photo | 409 `PHOTO_LIMIT_REACHED` |
| Upload a 6 MB image | 413 `FILE_TOO_LARGE`, no file left on disk |
| Upload a 0-byte file | 422 `INVALID_IMAGE` |
| Upload a text file renamed `photo.jpg` | 422 `INVALID_IMAGE` |
| Upload a GIF or BMP | 415 `UNSUPPORTED_FILE_TYPE` |
| Upload an image of 10000 × 10000 pixels | 422 `INVALID_IMAGE` (over 40 million pixels) |
| Upload a file named `../../etc/passwd.jpg` | Name ignored; saved under a random UUID |
| Phone photo with EXIF rotation and GPS data | Saved upright, with no EXIF data |
| Transparent PNG | Saved as JPEG with a white background |
| Database insert fails after the files are written | Both files removed |
| Reorder with a missing id, an extra id, a duplicate, or another room's photo | 422 |
| Delete a photo through a different room's path | 404 |
| Delete a photo whose file is already gone from disk | 204, warning logged |
| `PUT` equipment with `[1, 1, 4]` | Saved as `[1, 4]` |
| `PUT` equipment with an id that does not exist | 422 listing it |
| `PUT` equipment adding a new inactive item | 409 `INACTIVE_REFERENCE` |
| `PUT` equipment keeping an inactive item the room already has | Allowed |
| `PUT` equipment with `[]` | Room has no equipment |

### Users and roles

| Case | Expected |
| --- | --- |
| Create a user with an email that differs from another only by case | 409 `DUPLICATE` |
| `secondary_email` equal to `email` (any case) | 422 |
| Give `PITIKA` to a user with no division | 409 `DIVISION_REQUIRED` |
| Set `division_id: null` on an `IT_STAFF` user | 409 `DIVISION_REQUIRED` |
| Deactivate a user who owns rooms 12 and 14 | 200; both rooms now no-owner; `rooms_unassigned: [12, 14]` |
| Remove `ROOM_OWNER` from a user who owns rooms | Same as above |
| Reactivate that user | Rooms stay no-owner |
| Admin deactivates themselves, or removes their own `ADMIN` | 409 `SELF_ACTION_NOT_ALLOWED` |
| Another Admin deactivates the last active Admin | 409 `LAST_ADMIN` |
| Two Admins remove each other's `ADMIN` at the same moment, leaving none | One succeeds, the other gets 409 `LAST_ADMIN` |
| `PUT /users/{id}/roles` with `["STAFF", "STAFF"]` | Saved once |
| `PUT /users/{id}/roles` with `["MANAGER"]` | 422 |
| `PATCH /roles/{id}` with `code` | 422 |
| Non-admin calls `GET /users` | 403 `FORBIDDEN` |
| `password_hash` anywhere in any response | Must never appear (test the raw JSON) |
| `GET /users?role=PITIKA&province=SIEM_REAP` | Only active and inactive Pitika users whose division's department is in a Siem Reap location |
| User with no division in a `province` filter | Never matches any province |

### Signatures

| Case | Expected |
| --- | --- |
| Phone photo of a signature on white paper | 200; saved as a PNG with transparent paper, cropped to the ink |
| Signature in blue or red pen | Saved as black ink |
| Photo on light grey paper with a shadow | Paper and shadow become fully transparent |
| Signature of 6000 × 4000 pixels | Saved at most 600 × 300 |
| Blank white image | 422 `INVALID_IMAGE` "No signature found in the image." |
| GIF, BMP, a text file, a 0-byte file, a 6 MB file | 415, 422, 422, 413; no file left on disk |
| Upload a second signature | Old file deleted; only the new one remains |
| Database fails while saving the new path | New file deleted; old signature still served |
| Staff calls `PUT /users/{id}/signature` for someone else | 403 `FORBIDDEN` |
| `GET /users/{id}/signature` without a token | 401 `UNAUTHORIZED` |
| Signature file under `/uploads/...` | Never: signatures are not in the public folder |
| User with no signature | `signature_url: null`; `GET /users/{id}/signature` → 404 |

### Data integrity

| Case | Expected |
| --- | --- |
| Two requests create the same unique name at once | One 201, one 409 `DUPLICATE`; never 500 |
| Any error in the middle of a multi-step change (roles + clearing rooms) | Whole change rolled back |
| Database unreachable | 500 `INTERNAL_ERROR`, no stack trace or SQL in the body |

## 17. Error codes

These 20 codes are the complete list; do not invent others. Messages are plain English and may be improved, but codes and statuses must not change.

| Status | Code | When |
| --- | --- | --- |
| 400 | `WRONG_PASSWORD` | `current_password` is wrong on change-password |
| 401 | `UNAUTHORIZED` | Token missing, invalid, expired, wrong type, user inactive, or password fingerprint changed |
| 401 | `INVALID_CREDENTIALS` | Login failed for any reason |
| 403 | `PASSWORD_CHANGE_REQUIRED` | `must_change_password` is true (R16) |
| 403 | `FORBIDDEN` | Signed in but not allowed (role, ownership, owner-only fields) |
| 404 | `NOT_FOUND` | Record in the path does not exist, or a photo is not in that room |
| 405 | `METHOD_NOT_ALLOWED` | Method not supported on the path |
| 409 | `DUPLICATE` | Unique name, email or staff ID already used (R4, R5) |
| 409 | `INACTIVE_REFERENCE` | Linking to, or reactivating under, an inactive record (R2, R3, R15) |
| 409 | `DIVISION_REQUIRED` | Role needs a division the user does not have (R6) |
| 409 | `OWNER_INVALID` | Room owner is inactive or lacks `ROOM_OWNER` (R7) |
| 409 | `LAST_ADMIN` | Change would leave no active Admin (R10) |
| 409 | `SELF_ACTION_NOT_ALLOWED` | Admin deactivating or demoting themselves (R11) |
| 409 | `PHOTO_LIMIT_REACHED` | Room already has 20 photos (R14) |
| 413 | `FILE_TOO_LARGE` | Upload over `MAX_UPLOAD_MB` |
| 415 | `UNSUPPORTED_FILE_TYPE` | Image is not JPEG, PNG or WebP |
| 422 | `VALIDATION_ERROR` | Body, query or path value is invalid; details in `fields` |
| 422 | `INVALID_IMAGE` | Empty, broken or oversized-in-pixels image |
| 429 | `RATE_LIMITED` | Too many failed logins |
| 500 | `INTERNAL_ERROR` | Anything unexpected; logged with a request id, never shown to the client |

Every response, success or error, carries an `X-Request-ID` header (taken from the request if sent, else a new UUID). Server logs include it.

## 18. Testing requirements

The work is not done until every rule (R1–R18) and every edge case in section 16 has a passing automated test, and line coverage of `app/services` is at least 90%.

**Setup**

- Tests run against a real MySQL 8 database (Docker is fine), never SQLite: case-insensitive unique keys, `CHECK` constraints and row locks behave differently.
- Each test runs in a transaction that is rolled back, or on a freshly migrated database. Tests do not depend on each other's order.
- Uploads go to a temporary folder per test session.
- Factories create a valid location → building → floor → category → room chain, and users with any set of roles, in one line each.

**What every endpoint needs**

1. The success case, checking status code and the full response shape.
2. Each access label: no token (401), wrong role (403), right role (success).
3. Not found (404) for each path id.
4. One invalid body or query case (422) that shows the `fields` map.

**Security tests that must exist**

- No response body anywhere contains `password_hash` or a `door_code` value, except `GET /rooms/{id}/door-code`. Scan the raw JSON of every response produced in the test run.
- Every endpoint except login, refresh and `GET /health` returns 401 without a token. Generate this test from the app's route list so new routes are covered automatically.

**Other checks**

- `alembic upgrade head` on an empty database, then `alembic downgrade base`, both succeed.
- The seed script run twice leaves exactly 6 roles, 1 seed position and 1 first Admin.
- `ruff check` and `ruff format --check` pass.
- The generated OpenAPI document (`/docs`) lists every endpoint in sections 11–14, with request and response models.

## 19. Team tasks: one endpoint at a time, and definition of done

The work is split into 66 small tasks: 5 foundation tasks, one task per endpoint (58), and 3 final checks. Tasks 67–69 (user signatures) were added later. Either person takes the next free task; there is no fixed split.

**How to work as a team**

1. Pick the lowest-numbered task that has no owner and whose **Needs** tasks are all Done. Write your name in **Owner** and set **Status** to In progress.
2. Prefer a different resource from your partner at the same time (for example, you take buildings while they take categories). Two people in the same file at once causes merge conflicts.
3. Create a branch named after the task: `task-17`.
4. Tell your AI agent: *"Read SPEC.md. Do task 17 only."*
5. When the agent finishes, open a pull request and set Status to In review. Your partner checks it and merges it. Then set Done.
6. Before starting each task, run `git pull origin main`.

**Foundation first.** Task 1 is done by one person while the other reads the spec. Task 2 (migrations) is done by one person only. After task 2, tasks 3, 4 and 5 can run in parallel. If a later task needs a database change, make it a separate small task, and only one person writes migrations at a time, so Alembic never gets two heads.

**Shared names, fixed in tasks 4 and 5:** `get_current_user()`, `require_roles("ADMIN")`, `AppError(code, status, message, fields)`, `paginate(query, page, size)`, `apply_search(query, term, columns)`, and the test factories `make_location()`, `make_room()`, `make_user(roles=[...])`. Every later task uses these names.

**A task is done when**

- The endpoint matches sections 11–14 exactly: path, access, body, response shape, status codes.
- The rules listed in its row are enforced, and its matching edge cases in section 16 are tested.
- Tests cover: success, 401 without a token, 403 for the wrong role, 404 for an unknown id, and one 422 case.
- All tests pass and `ruff check` is clean.

**Tasks 1–44: foundation, sign-in, places, organisation**

| # | Task | Needs | Rules | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Project skeleton: settings, DB session, error format, `X-Request-ID`, `GET /health` | — | Section 4 |  | To do |
| 2 | Migrations for all 14 tables | 1 | Sections 6–7 |  | To do |
| 3 | Seed script, role and province constants | 2 | Section 8 |  | To do |
| 4 | Auth core: hashing, tokens, `get_current_user`, `require_roles`, request checks | 2 | Sections 5, 9; R16 |  | To do |
| 5 | List helpers and test factories | 2 | Section 4 |  | To do |
| 6 | `POST /auth/login` | 3, 4 | Section 9, rate limit |  | To do |
| 7 | `POST /auth/refresh` | 6 | Section 9 |  | To do |
| 8 | `POST /auth/change-password` | 6 | R16, R18 |  | To do |
| 9 | `POST /auth/logout` | 6 | — |  | To do |
| 10 | `GET /me` | 6 | R16 |  | To do |
| 11 | `PATCH /me` | 10 | R5 |  | To do |
| 12 | `GET /provinces` | 3, 4 | R1 |  | To do |
| 13 | `POST /locations` | 4, 5 | R1, R4 |  | To do |
| 14 | `GET /locations` | 13 | R1 |  | To do |
| 15 | `GET /locations/{id}` | 13 | — |  | To do |
| 16 | `PATCH /locations/{id}` | 13 | R1, R3, R4 |  | To do |
| 17 | `POST /buildings` | 13 | R2, R4 |  | To do |
| 18 | `GET /buildings` | 17 | — |  | To do |
| 19 | `GET /buildings/{id}` | 17 | — |  | To do |
| 20 | `PATCH /buildings/{id}` | 17 | R2, R3, R4 |  | To do |
| 21 | `POST /floors` | 17 | R2, R4 |  | To do |
| 22 | `GET /floors` | 21 | — |  | To do |
| 23 | `GET /floors/{id}` | 21 | — |  | To do |
| 24 | `PATCH /floors/{id}` | 21 | R2, R3, R4 |  | To do |
| 25 | `POST /categories` | 4, 5 | R4 |  | To do |
| 26 | `GET /categories` | 25 | — |  | To do |
| 27 | `GET /categories/{id}` | 25 | — |  | To do |
| 28 | `PATCH /categories/{id}` | 25 | R4 |  | To do |
| 29 | `POST /equipment` | 4, 5 | R4 |  | To do |
| 30 | `GET /equipment` | 29 | — |  | To do |
| 31 | `GET /equipment/{id}` | 29 | — |  | To do |
| 32 | `PATCH /equipment/{id}` | 29 | R4 |  | To do |
| 33 | `POST /positions` | 4, 5 | R4 |  | To do |
| 34 | `GET /positions` | 33 | — |  | To do |
| 35 | `GET /positions/{id}` | 33 | — |  | To do |
| 36 | `PATCH /positions/{id}` | 33 | R4 |  | To do |
| 37 | `POST /departments` | 13 | R2, R4 |  | To do |
| 38 | `GET /departments` | 37 | — |  | To do |
| 39 | `GET /departments/{id}` | 37 | — |  | To do |
| 40 | `PATCH /departments/{id}` | 37 | R2, R3, R4 |  | To do |
| 41 | `POST /divisions` | 37 | R2, R4 |  | To do |
| 42 | `GET /divisions` | 41 | — |  | To do |
| 43 | `GET /divisions/{id}` | 41 | — |  | To do |
| 44 | `PATCH /divisions/{id}` | 41 | R2, R3, R4 |  | To do |

**Tasks 45–66: users, rooms, final checks**

| # | Task | Needs | Rules | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| 45 | `GET /roles` | 3, 4 | — |  | To do |
| 46 | `PATCH /roles/{id}` | 45 | R17 |  | To do |
| 47 | `POST /users` | 33, 41 | R2, R5, R18 |  | To do |
| 48 | `GET /users` | 47 | R1 |  | To do |
| 49 | `GET /users/{id}` | 47 | — |  | To do |
| 50 | `PUT /users/{id}/roles` | 45, 47, 53 | R6, R9, R10, R11 |  | To do |
| 51 | `PATCH /users/{id}` | 47, 53 | R2, R5, R6, R9, R10, R11 |  | To do |
| 52 | `POST /users/{id}/reset-password` | 47 | R18 |  | To do |
| 53 | `POST /rooms` | 21, 25 | R2, R4, R7, R13 |  | To do |
| 54 | `GET /rooms` | 53 | R1, R12 |  | To do |
| 55 | `GET /rooms/{id}` | 53 | R12 |  | To do |
| 56 | `PATCH /rooms/{id}` | 53 | R2, R4, R7, R8, R13 |  | To do |
| 57 | `GET /rooms/{id}/door-code` | 53 | R8 |  | To do |
| 58 | `POST /rooms/{id}/photos` | 53 | R14 |  | To do |
| 59 | `GET /rooms/{id}/photos` | 58 | — |  | To do |
| 60 | `PUT /rooms/{id}/photos/order` | 58 | — |  | To do |
| 61 | `DELETE /rooms/{id}/photos/{photo_id}` | 58 | — |  | To do |
| 62 | `PUT /rooms/{id}/equipment` | 29, 53 | R15 |  | To do |
| 63 | `GET /rooms/{id}/equipment` | 62 | — |  | To do |
| 64 | Security tests: no `password_hash` or `door_code` leaks; 401 on every route | 6–63 | Section 18 |  | To do |
| 65 | Race tests for `LAST_ADMIN` and `DUPLICATE` | 50, 51 | R4, R10 |  | To do |
| 66 | README and final check against the definition of done | 64, 65 | Section 19 |  | To do |

Task 53 creates room owners with the `make_user(roles=["ROOM_OWNER"])` factory, so it does not wait for the users endpoints. Tasks 50 and 51 wait for task 53 because rule R9 clears room owners and needs rooms to test.

**Tasks 67–69: user signatures (added 23 Oct 2026)**

| # | Task | Needs | Rules | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| 67 | `PUT /me/signature`, `DELETE /me/signature`, plus migration for `users.user_signature` | 10 | R19 |  | Done |
| 68 | `PUT /users/{id}/signature`, `DELETE /users/{id}/signature` | 47, 67 | R19 |  | Done |
| 69 | `GET /users/{id}/signature` | 67 | R19 |  | Done |

**Definition of done**

- [ ] Every endpoint in sections 11–14 exists with the exact path, method, access, status codes and shapes.
- [ ] R1–R18 enforced in services and tested.
- [ ] Every row in section 16 has a passing test.
- [ ] No response leaks `password_hash` or `door_code` (outside the door-code endpoint).
- [ ] Migrations upgrade and downgrade cleanly; seed script runs twice safely.
- [ ] `ruff` clean; service coverage at least 90%.
- [ ] README explains setup, environment variables, running migrations, seeding, running tests, and the known limits (stateless logout, in-memory rate limit).

## 20. Out of scope and decisions

The booking scope comes next and will reuse this one: the province helpers, `is_bookable`, room hours, owners and roles. Do not build any of it now.

**Left for the booking scope**

- Booking tables, booking endpoints, availability by date and time, double-booking prevention.
- Pitika approval, room owner approval, IT Lead assignment and IT Staff work.
- Letting a booker see the door code during a confirmed booking.
- What happens to future bookings when a room or place is deactivated, or a room loses its owner.
- Email notifications (the `email_notifications` flag is stored now, unused).

**Decisions (approved on 21 Oct 2026; build with these)**

- [x] Khmer names for the six roles and the seed position. Decision: same as `name_en`, loaded from `scripts/seed_roles.json`.
- [x] Khmer province names checked by a native speaker. Decision: the list in section 8.
- [x] `floors.floor_label` and `equipment.name` have one language only, unlike other names. Decision: keep as in the ERD.
- [x] Password policy beyond length 8. Decision: none.
- [x] Photo limits (20 per room, 5 MB). Decision: as stated; both are settings.
- [x] Should Staff see inactive rooms and places in lists? Decision: yes, with `is_active` in each item; clients filter with `is_active=true`.
