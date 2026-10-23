# Room Booking System — Project Requirements (Part 1)

Oct 21, 2026 · @Someone

This document lists what the system must do, module by module. Each module has its **functions** (what people can do) and its **validation** (what the system checks).

## Modules at a glance

The system has 6 modules. Each function and each validation rule has an ID (for example `USR-F03`), so people can talk about it easily.

| # | Module | What it covers | ID prefix |
| --- | --- | --- | --- |
| 1 | Auth | Sign in, sign out, change password, my profile | `AUTH` |
| 2 | User & roles | User accounts, the 6 roles | `USR` |
| 3 | Organisation | Departments, divisions (teams), job positions | `ORG` |
| 4 | Location | Provinces, offices (locations), buildings, floors | `LOC` |
| 5 | Room | Room types (categories), rooms, room photos, room equipment | `ROOM` |
| 6 | Equipment | The list of equipment, for example a projector | `EQP` |

**ID meaning:** `F` = function, `V` = validation. `LOC-V04` = Location module, validation rule 4.

**Who can do what** (short words used in the tables):

| Word | Meaning |
| --- | --- |
| Everyone | Any person who is signed in |
| Admin | A person with the Admin role |
| Owner | The room owner of that room |

## How the modules connect

&#91;embedded content: how the modules connect\]

Each arrow means "has": an office has buildings, a room has photos, a person has roles. A person can own rooms, and a room can also have no owner. The Auth module is not in the picture because it keeps no data of its own; it uses the people from the User module.

## Rules for all modules

These functions and checks are the same in every module. The module sections below do not repeat them.

**Common functions**

| ID | Function |
| --- | --- |
| COM-F01 | Lists show 20 items per page. You can ask for up to 100. |
| COM-F02 | Lists can **search** by name (English or Khmer). |
| COM-F03 | Lists can show only **active** or only **inactive** items. |
| COM-F04 | Lists are sorted by **sort order**, then by English name. |
| COM-F05 | We **never delete**. We turn items off (inactive). Only room photos are really deleted. |
| COM-F06 | Every item shows when it was **created** and last **updated**. |
| COM-F07 | Most items have a name in **English and Khmer**. The system shows both. |

**Common validation**

| ID | Rule | If the rule is broken |
| --- | --- | --- |
| COM-V01 | A required field cannot be empty or only spaces. | Error: "This field is required." |
| COM-V02 | Spaces at the start and end of text are removed. (Not for passwords.) | No error |
| COM-V03 | Text cannot be longer than its limit. Khmer letters count as letters, not bytes. | Error: "Too long (max 100)." |
| COM-V04 | The system refuses fields it does not know. | Error: "Unknown field." |
| COM-V05 | An item that does not exist cannot be opened or changed. | Error: "Not found." |
| COM-V06 | You cannot link to an **inactive** item. Example: a new building in an inactive office. | Error: "This office is inactive." |
| COM-V07 | You cannot turn an item on again if its **parent is off**. Example: a building whose office is inactive. | Error: "The office is inactive." |
| COM-V08 | Names must not repeat. Capital and small letters count as the same ("Room A" = "room a"). | Error: "This name already exists." |
| COM-V09 | Sort order is a whole number from 0 to 9999. | Error: "Must be 0 to 9999." |
| COM-V10 | A person without the right role cannot use a function. | Error: "You are not allowed." |

## General requirements

These are about the whole system, not one module.

| ID | Topic | Requirement |
| --- | --- | --- |
| GEN-01 | Security | Passwords are saved in a safe, secret form (hashed). Nobody can read them, not even the Admin. |
| GEN-02 | Security | Secrets are never shown: no passwords, and no door codes (except to the Admin and the room owner). |
| GEN-03 | Security | Every function needs sign-in, except sign-in itself and the health check. |
| GEN-04 | Security | A sign-in key works for 15 minutes. A refresh key works for 7 days. |
| GEN-05 | Time | All dates and times are saved in world time (UTC). Room opening hours are in Cambodia time (UTC+7). |
| GEN-06 | Language | Most names are in English and Khmer. The API always sends both. The app chooses which one to show. |
| GEN-07 | Photos | Photos are saved on the server's own disk. Each file gets a random name. |
| GEN-08 | Data | Nothing is deleted, except room photos. Items are turned off instead. |
| GEN-09 | Errors | Every error has the same simple form: a code and a message. Field errors also say which field is wrong. |
| GEN-10 | Database | MySQL 8. Khmer text must save and show correctly. |

## Module 1 — Auth (sign-in)

People sign in with email and password. There is no sign-up: only the Admin creates accounts (module 2).

**Functions**

| ID | Function | Who | API |
| --- | --- | --- | --- |
| AUTH-F01 | Sign in with email and password. You get a key (token) for 15 minutes, and a refresh key for 7 days. | Anyone | `POST /auth/login` |
| AUTH-F02 | Stay signed in: get a new key with the refresh key. | Anyone | `POST /auth/refresh` |
| AUTH-F03 | Sign out. | Everyone | `POST /auth/logout` |
| AUTH-F04 | Change my password. | Everyone | `POST /auth/change-password` |
| AUTH-F05 | First sign-in: a new user must change their password before they can do anything else. | Everyone | — |
| AUTH-F06 | See my profile: my name, team, job, province and roles. | Everyone | `GET /me` |
| AUTH-F07 | Change my profile: second email, phone, photo link, email notifications on or off. | Everyone | `PATCH /me` |
| AUTH-F08 | Add, change or remove my signature (a picture of how I sign). It is printed on booking approval forms. | Everyone | `PUT /me/signature`, `DELETE /me/signature` |

**Validation**

| ID | Rule | If the rule is broken |
| --- | --- | --- |
| AUTH-V01 | Email: spaces removed and changed to small letters before checking. | No error |
| AUTH-V02 | Wrong email, wrong password, or an inactive user all get the **same** message. Nobody can learn which emails exist. | "Email or password is wrong." |
| AUTH-V03 | After 5 wrong tries in 15 minutes (same email, same computer), sign-in stops for a while. | "Too many tries. Try again later." |
| AUTH-V04 | A new password has 8 to 128 characters. | "Password must be 8 to 128 characters." |
| AUTH-V05 | A new password cannot be the same as your email. | "Password cannot be your email." |
| AUTH-V06 | A new password must be different from the old one. | "Use a new password." |
| AUTH-V07 | To change your password, the current password must be correct. | "Current password is wrong." |
| AUTH-V08 | After a password change or reset, old keys stop working on **all** devices. | "Please sign in again." |
| AUTH-V09 | When a user is turned off, they are signed out at once. | "Please sign in again." |
| AUTH-V10 | While a user must change their password, they can only: change password, sign out, see my profile. | "Please change your password first." |
| AUTH-V11 | Second email: a real email address, max 254 characters, not the same as the main email. | "Invalid second email." |
| AUTH-V12 | Phone: max 20 characters. Photo link: max 3000 characters, starts with `http://`, `https://` or `/`. | "Invalid phone" / "Invalid link." |
| AUTH-V13 | In "my profile" you can change only the 4 fields in AUTH-F07. Name, email and roles are changed by the Admin. | "You cannot change this field." |
| AUTH-V14 | Passwords are never shown, never sent back, and never saved as plain text. | — |

## Module 2 — User & roles

Only the Admin manages user accounts and roles. One user can have more than one role.

**The 6 roles**

| Role | What they can do in part 1 |
| --- | --- |
| Admin | Everything |
| Room owner | Change only their own rooms |
| Staff | Look at places, rooms and teams |
| Pitika | Same as Staff now. Approves bookings in part 2 |
| IT Lead | Same as Staff now. Sends IT staff in part 2 |
| IT Staff | Same as Staff now. Prepares rooms in part 2 |

**Functions**

| ID | Function | Who | API |
| --- | --- | --- | --- |
| USR-F01 | See the list of users. Search by name, staff ID or email. Filter by division, department, job, role, province, or active. | Admin | `GET /users` |
| USR-F02 | See one user: all details, roles, province and the rooms they own. | Admin | `GET /users/{id}` |
| USR-F03 | Create a user with a temporary password. | Admin | `POST /users` |
| USR-F04 | Change a user's details. | Admin | `PATCH /users/{id}` |
| USR-F05 | Turn a user off or on. | Admin | `PATCH /users/{id}` |
| USR-F06 | Reset a user's password. The Admin gives a new temporary password. | Admin | `POST /users/{id}/reset-password` |
| USR-F07 | Give or remove roles. The Admin sends the full new list of roles. | Admin | `PUT /users/{id}/roles` |
| USR-F08 | See the list of the 6 roles. | Admin | `GET /roles` |
| USR-F09 | Change a role's name in English or Khmer. | Admin | `PATCH /roles/{id}` |
| USR-F10 | When a user is turned off, or loses the Room owner role, their rooms become **no-owner** rooms. The system shows which rooms changed. | System | — |
| USR-F11 | Add, change or remove a user's signature for them. | Admin | `PUT /users/{id}/signature`, `DELETE /users/{id}/signature` |
| USR-F12 | See a user's signature. | Everyone | `GET /users/{id}/signature` |

**User fields**

| Field | Required? | Limit |
| --- | --- | --- |
| Staff ID | Yes | Max 20, no repeats |
| Title | No | One of: Mr., Ms., Mrs., Dr. |
| Name in English, name in Khmer | Yes | Max 100 each |
| Email | Yes | Max 254, no repeats |
| Second email | No | Max 254 |
| Phone | No | Max 20 |
| Photo link | No | Max 3000 |
| Job position | Yes | Must exist |
| Division (team) | No | Must exist |
| Email notifications | No | On by default |
| Temporary password | Yes, when creating | 8 to 128 |
| Signature | No | A JPG, PNG or WebP picture, max 5 MB |

**Validation**

| ID | Rule | If the rule is broken |
| --- | --- | --- |
| USR-V01 | Staff ID is required, max 20 characters, and cannot repeat. | "This staff ID already exists." |
| USR-V02 | Email is required, must be a real email, and is saved in small letters. It cannot repeat: "A@x.com" and "a@x.com" are the same. | "This email already exists." |
| USR-V03 | Second email must be different from the main email. | "Second email must be different." |
| USR-V04 | Job position is required. It must exist and be active. | "Job position not found" / "is inactive." |
| USR-V05 | Division is optional. If given, it must exist and be active. | "Division not found" / "is inactive." |
| USR-V06 | Temporary password: 8 to 128 characters, not the same as the email. The user must change it at first sign-in. | "Password must be 8 to 128 characters." |
| USR-V07 | Pitika, IT Lead and IT Staff **must have a division**, so the system knows their province. You cannot remove the division from them. | "This role needs a division." |
| USR-V08 | There must always be **at least one active Admin**. | "You cannot remove the last Admin." |
| USR-V09 | An Admin cannot turn off their own account or remove their own Admin role. | "You cannot do this to yourself." |
| USR-V10 | Only the 6 roles exist. A role given twice is saved once. | "Unknown role." |
| USR-V11 | Roles cannot be added, turned off, or have their code changed. Only their names can change. | "You cannot change this field." |
| USR-V12 | A user's province is not typed. It comes from: division → department → office → province. | — |
| USR-V13 | Users never see passwords. The API never sends them. | — |
| USR-V14 | Signature: a JPG, PNG or WebP picture, at most 5 MB and 40 million pixels. The system checks the file itself, not its name. | "File too big" / "Wrong file type" / "Not a real image." |
| USR-V15 | The system cleans every signature: turns it the right way up, removes hidden data, makes the paper see-through, makes the ink black (any pen colour), cuts it to the signature and makes it small (at most 600 × 300). The result is black and white. A blank page is refused. For the best result, sign with a dark pen on blank white paper, in good light. | "No signature found in the image." |
| USR-V16 | Only signed-in people can see a signature. It is never in the public photo folder. A person changes only their own signature; the Admin can change anyone's. | "You are not allowed." |

## Module 3 — Organisation

The company is organised like this: an **office** has **departments**, a department has **divisions** (teams), and a person is in a division. Every person also has a **job position**.

**Functions**

| ID | Function | Who | API |
| --- | --- | --- | --- |
| ORG-F01 | See the list of departments. Filter by office. | Everyone | `GET /departments` |
| ORG-F02 | See one department. | Everyone | `GET /departments/{id}` |
| ORG-F03 | Create a department in an office. | Admin | `POST /departments` |
| ORG-F04 | Change a department, move it to another office, or turn it off or on. | Admin | `PATCH /departments/{id}` |
| ORG-F05 | See the list of divisions. Filter by department. | Everyone | `GET /divisions` |
| ORG-F06 | See one division. | Everyone | `GET /divisions/{id}` |
| ORG-F07 | Create a division in a department. | Admin | `POST /divisions` |
| ORG-F08 | Change a division, move it to another department, or turn it off or on. | Admin | `PATCH /divisions/{id}` |
| ORG-F09 | See the list of job positions. | Everyone | `GET /positions` |
| ORG-F10 | See one job position. | Everyone | `GET /positions/{id}` |
| ORG-F11 | Create a job position. | Admin | `POST /positions` |
| ORG-F12 | Change a job position, or turn it off or on. | Admin | `PATCH /positions/{id}` |

**Fields**

| Item | Fields |
| --- | --- |
| Department | Office (required), name in English and Khmer (required, max 100), sort order |
| Division | Department (required), name in English and Khmer (required, max 100), short name (max 20), sort order |
| Job position | Name in English and Khmer (required, max 100), sort order |

**Validation**

| ID | Rule | If the rule is broken |
| --- | --- | --- |
| ORG-V01 | A department must be in an office that exists and is active. | "Office not found" / "is inactive." |
| ORG-V02 | Two departments in the **same office** cannot have the same English name. | "This name already exists." |
| ORG-V03 | A division must be in a department that exists and is active. | "Department not found" / "is inactive." |
| ORG-V04 | Two divisions in the **same department** cannot have the same English name. | "This name already exists." |
| ORG-V05 | Two job positions cannot have the same English name. | "This name already exists." |
| ORG-V06 | When a department, division or job position is turned off, its people keep it. But new people cannot be put in it. | "This division is inactive." |
| ORG-V07 | You cannot turn a division on again if its department is off. You cannot turn a department on again if its office is off. | "The department is inactive." |
| ORG-V08 | Moving a department to another office also changes the **province** of all its people. This is allowed. | No error |

## Module 4 — Location

Places are organised like this: a **province** has **offices** (locations), an office has **buildings**, and a building has **floors**. Rooms are on floors (module 5).

**Functions**

| ID | Function | Who | API |
| --- | --- | --- | --- |
| LOC-F01 | See the list of provinces (Phnom Penh and the 24 provinces). | Everyone | `GET /provinces` |
| LOC-F02 | See the list of offices. Filter by province. Search by name or address. | Everyone | `GET /locations` |
| LOC-F03 | See one office. | Everyone | `GET /locations/{id}` |
| LOC-F04 | Create an office. | Admin | `POST /locations` |
| LOC-F05 | Change an office, or turn it off or on. | Admin | `PATCH /locations/{id}` |
| LOC-F06 | See the list of buildings. Filter by office. | Everyone | `GET /buildings` |
| LOC-F07 | See one building, with its office and province. | Everyone | `GET /buildings/{id}` |
| LOC-F08 | Create a building in an office. | Admin | `POST /buildings` |
| LOC-F09 | Change a building, move it to another office, or turn it off or on. | Admin | `PATCH /buildings/{id}` |
| LOC-F10 | See the list of floors. Filter by building or office. | Everyone | `GET /floors` |
| LOC-F11 | See one floor, with its building, office and province. | Everyone | `GET /floors/{id}` |
| LOC-F12 | Create a floor in a building. | Admin | `POST /floors` |
| LOC-F13 | Change a floor, or turn it off or on. | Admin | `PATCH /floors/{id}` |

**Fields**

| Item | Fields |
| --- | --- |
| Office | Name in English and Khmer (required, max 100), province (required), description (max 1000), address (max 200), map search text (max 500) |
| Building | Office (required), name in English and Khmer (required, max 100), short name (max 20), sort order |
| Floor | Building (required), floor label, for example "3rd floor" (required, max 100, one language), sort order |

**Validation**

| ID | Rule | If the rule is broken |
| --- | --- | --- |
| LOC-V01 | The province list is fixed. Nobody can add or change provinces in the system. | — |
| LOC-V02 | An office's province must be from the list. | "Choose a province from the list." |
| LOC-V03 | Two offices cannot have the same English name. | "This name already exists." |
| LOC-V04 | A building must be in an office that exists and is active. | "Office not found" / "is inactive." |
| LOC-V05 | Two buildings in the **same office** cannot have the same English name. The same name in different offices is OK. | "This name already exists." |
| LOC-V06 | A floor must be in a building that exists and is active. | "Building not found" / "is inactive." |
| LOC-V07 | Two floors in the **same building** cannot have the same label. | "This floor already exists." |
| LOC-V08 | Turning off an office, building or floor does **not** turn off what is inside. But every room inside becomes **not bookable**. | No error |
| LOC-V09 | You cannot turn a building on again if its office is off. You cannot turn a floor on again if its building is off. | "The office is inactive." |
| LOC-V10 | Moving a building to another office also moves its floors and rooms. The new office must be active. | "The office is inactive." |

## Module 5 — Room

A room is on a floor and has a **type** (category), for example "Meeting room". A room can have one **owner** or no owner. The Admin manages all rooms; an owner manages only their own rooms.

**Functions**

| ID | Function | Who | API |
| --- | --- | --- | --- |
| ROOM-F01 | See the list of room types. | Everyone | `GET /categories` |
| ROOM-F02 | See one room type. | Everyone | `GET /categories/{id}` |
| ROOM-F03 | Create a room type. | Admin | `POST /categories` |
| ROOM-F04 | Change a room type, or turn it off or on. | Admin | `PATCH /categories/{id}` |
| ROOM-F05 | See the list of rooms. Filter by province, office, building, floor, room type, number of people, equipment, owner, "has owner", active, or bookable. Search by name. | Everyone | `GET /rooms` |
| ROOM-F06 | See one room: its place, type, owner, opening hours, photos, equipment, and if it is bookable. | Everyone | `GET /rooms/{id}` |
| ROOM-F07 | Create a room. | Admin | `POST /rooms` |
| ROOM-F08 | Change a room. The owner can change only some fields (see below). | Admin, Owner | `PATCH /rooms/{id}` |
| ROOM-F09 | Turn a room off or on, move it to another floor, or change its owner. | Admin | `PATCH /rooms/{id}` |
| ROOM-F10 | See the room's **door code**. | Admin, Owner | `GET /rooms/{id}/door-code` |
| ROOM-F11 | See the room's photos. | Everyone | `GET /rooms/{id}/photos` |
| ROOM-F12 | Add a photo (one photo at a time). | Admin, Owner | `POST /rooms/{id}/photos` |
| ROOM-F13 | Change the order of the photos. The first photo is the **cover photo** in the room list. | Admin, Owner | `PUT /rooms/{id}/photos/order` |
| ROOM-F14 | Delete a photo. | Admin, Owner | `DELETE /rooms/{id}/photos/{photo_id}` |
| ROOM-F15 | See the room's equipment. | Everyone | `GET /rooms/{id}/equipment` |
| ROOM-F16 | Choose the room's equipment. You send the full new list. | Admin, Owner | `PUT /rooms/{id}/equipment` |

**Room fields**

| Field | Required? | Limit | Owner can change? |
| --- | --- | --- | --- |
| Name in English, name in Khmer | Yes | Max 100 each | Yes |
| Floor | Yes | Must exist | No |
| Room type | Yes | Must exist | Yes |
| Number of people (capacity) | Yes | 1 to 10000 | Yes |
| Size in m² | No | 1 to 100000 | Yes |
| Opening time, closing time | Yes | Like "08:00" | Yes |
| Short description | No | Max 200 | Yes |
| Description | No | Max 1000 | Yes |
| Door code | No | Max 50, secret | Yes |
| Owner | No | A user | No |
| Active | — | On or off | No |

**Validation**

| ID | Rule | If the rule is broken |
| --- | --- | --- |
| ROOM-V01 | Two room types cannot have the same English name. | "This name already exists." |
| ROOM-V02 | A room must be on a floor that exists and is active. Its room type must exist and be active. | "Floor not found" / "is inactive." |
| ROOM-V03 | Two rooms on the **same floor** cannot have the same English name. | "This name already exists." |
| ROOM-V04 | Number of people: a whole number, 1 to 10000. Size: 1 to 100000. | "Must be 1 to 10000." |
| ROOM-V05 | Opening time must be **before** closing time. The hours are the same every day, in Cambodia time. A room cannot stay open after midnight. | "Opening time must be before closing time." |
| ROOM-V06 | The owner is optional. If given, the owner must be an active user with the **Room owner** role. | "This user cannot own rooms." |
| ROOM-V07 | A room with no owner is open for everyone to book later. | No error |
| ROOM-V08 | An owner can change only **their own** rooms, and only the fields marked "Yes" above. | "You are not allowed." |
| ROOM-V09 | The door code is **secret**. It is never in the room list or room details. Only the Admin and the owner can see it, with ROOM-F10. | "You are not allowed." |
| ROOM-V10 | A room is **bookable** only when the room, its floor, its building and its office are all active. The room type does not matter. | — |
| ROOM-V11 | You cannot turn a room on again if its floor is off. | "The floor is inactive." |
| ROOM-V12 | When a room type is turned off, rooms keep it. But new rooms cannot use it. | "This room type is inactive." |
| ROOM-V13 | A room can have **at most 20 photos**. | "This room has 20 photos already." |
| ROOM-V14 | A photo must be JPG, PNG or WebP, at most **5 MB**, and at most 40 million pixels. The system checks the file itself, not its name. | "File too big" / "Wrong file type" / "Not a real image." |
| ROOM-V15 | The system turns photos the right way up, removes hidden data (like GPS location), and saves them as JPG with a small preview (thumbnail). | No error |
| ROOM-V16 | The new photo order must list **every** photo of the room, each one once. | "The list of photos is not complete." |
| ROOM-V17 | Room equipment: every item must exist. A new item must be active. Repeats are saved once. An empty list removes all equipment. | "Equipment not found" / "is inactive." |

## Module 6 — Equipment

This module keeps the list of equipment, for example "Projector" or "Whiteboard". Choosing which room has which equipment is in module 5 (ROOM-F16). A room either has an item or not; there is no number (quantity).

**Functions**

| ID | Function | Who | API |
| --- | --- | --- | --- |
| EQP-F01 | See the list of equipment. Search by name. | Everyone | `GET /equipment` |
| EQP-F02 | See one item. | Everyone | `GET /equipment/{id}` |
| EQP-F03 | Create an item. | Admin | `POST /equipment` |
| EQP-F04 | Change an item, or turn it off or on. | Admin | `PATCH /equipment/{id}` |

**Fields**

| Field | Required? | Limit |
| --- | --- | --- |
| Name | Yes | Max 200, one language |
| Icon (icon name or link) | No | Max 1000 |
| Sort order | No | 0 to 9999 |

**Validation**

| ID | Rule | If the rule is broken |
| --- | --- | --- |
| EQP-V01 | Two items cannot have the same name. | "This name already exists." |
| EQP-V02 | When an item is turned off, rooms that have it **keep** it. But it cannot be added to other rooms. | "This equipment is inactive." |

## Stories: step by step

These stories show how the functions work together. The IDs show which function is used.

**Story 1 — A new person joins**

1. The Admin creates the account with a temporary password. (USR-F03)
2. The Admin gives the person their roles, for example Staff. (USR-F07)
3. The Admin gives the password to the person, for example by phone.
4. The person signs in. (AUTH-F01)
5. The system says: "Please change your password first." (AUTH-F05)
6. The person chooses a new password. (AUTH-F04)
7. Now the person can use the system.

**Story 2 — A new room**

1. If the office does not exist, the Admin creates it. (LOC-F04)
2. The Admin creates the building in the office. (LOC-F08)
3. The Admin creates the floor in the building. (LOC-F12)
4. The Admin creates the room on the floor, with its type, size and opening hours. The Admin can choose an owner, or leave it empty. (ROOM-F07)
5. The Admin or the owner adds photos. (ROOM-F12)
6. The Admin or the owner chooses the equipment, for example a projector. (ROOM-F16)
7. Everyone can now see the room in the list. (ROOM-F05)

**Story 3 — A room owner leaves the company**

1. The Admin turns off the person's account. (USR-F05)
2. The person is signed out at once. (AUTH-V09)
3. All their rooms become no-owner rooms. The system shows which rooms changed. (USR-F10)
4. If needed, the Admin chooses a new owner for each room. (ROOM-F09)

**Story 4 — Someone forgets their password**

1. The person asks the Admin for help.
2. The Admin gives a new temporary password. (USR-F06)
3. The person's old sign-in stops working on all devices. (AUTH-V08)
4. The person signs in and must choose a new password. (AUTH-F05)

## Team plan for 2 people

Two people can build at the same time. Each person has their own line of modules, so they rarely wait for each other.

**Which module needs which**

| Module | Needs first |
| --- | --- |
| Base: project setup, database, sign-in core | Nothing |
| Auth | Base |
| Location | Base |
| Equipment | Base |
| Organisation | Location (a department is in an office) |
| User | Organisation (a person has a division and a job position) |
| Room | Location and Equipment. It also uses User for owners, but can use test users until User is ready. |

**The plan**

| Step | Person A | Person B |
| --- | --- | --- |
| 1. Together | Build the **Base** together. Agree on shared names and the error format. | (same) |
| 2 | **Auth** (module 1) | **Location** (module 4) |
| 3 | **Organisation** (module 3). Person B's Location is ready now. | **Equipment** (module 6) |
| 4 | **User & roles** (module 2) | **Room** (module 5), with test users as owners |
| 5. Together | Test the parts that join the two lines (see below). Check each other's work. | (same) |

**Step 5: things to test together**

- A room owner must be an active user with the Room owner role. (ROOM-V06)
- When an owner is turned off, their rooms become no-owner rooms. (USR-F10)
- Pitika, IT Lead and IT Staff get their province from their office. (USR-V07, USR-V12)
- Stories 1 to 4 work from start to end.

**Simple rules**

- Each person changes only the files of their own modules. If you need a change in your partner's module, ask them.
- Only one person changes the database tables at a time.
- Talk for 15 minutes every day: what I finished, what I do today, do I need help.

## Not in this project

These come later, in part 2 or after.

- Booking rooms, and checking if a room is free.
- Approving bookings (Pitika, room owner).
- Printing signatures on approval forms. Signatures are saved now (AUTH-F08, USR-F11) and used when bookings come.
- IT help for bookings (IT Lead, IT Staff).
- Sending emails or notifications.
- Signing up alone, or "forgot password" by email.
- Website or app screens. Part 1 is the API only.

## Questions for you

All 6 questions are answered (21 Oct 2026). The answers are already in the module sections.

| # | Question | My suggestion | Your answer |
| --- | --- | --- | --- |
| 1 | What does a **staff ID** look like? Any text, or a fixed format like "EMP-00123"? | Any text, max 20 characters | OK |
| 2 | Must a **phone** number be a Cambodian number (for example 012 345 678)? | Any text, max 20 characters | OK |
| 3 | Is the **title** free text, or a list (Mr., Ms., Mrs., Dr.)? | A fixed list: Mr., Ms., Mrs., Dr. | OK |
| 4 | What are the **Khmer names** of the 6 roles? | Use the English names until you send them | OK |
| 5 | Can everyone see **inactive** offices and rooms in lists, or only the Admin? | Everyone (you chose this before). Each item shows if it is active | OK |
| 6 | Can Staff see the **list of users** (names, teams), or only the Admin? | Only the Admin | OK |
