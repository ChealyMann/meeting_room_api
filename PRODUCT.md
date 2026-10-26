# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Admin dashboard (`admin_dashboard/`, not built yet): Vue 3 with the Composition API (`<script setup lang="ts">`), TypeScript, Vite, Vue Router, Pinia, Tailwind CSS, Lucide stroke icons. API types generated from the API's `/openapi.json`. Backend: the FastAPI + MySQL Meeting Room Booking API in this repository (`app/`).

## Users

- **Admin** (only user of this version): staff of the National Bank of Cambodia who set up and maintain the room booking data. Uses the dashboard every day, making many changes: rooms, offices, buildings, floors, room types, equipment, departments, divisions, positions, users and roles.
- Other roles (Room owner, Staff, Pitika, IT Lead, IT Staff) have no dashboard access yet; their permissions are undecided.

## Product Purpose

Replace `/docs` (Swagger) as the way to manage the booking system's master data. Success: the Admin does every create, edit and turn off/on task from real screens, sees the API's own error messages next to the right field, and never loses typed work when a session token expires. Bookings are not built yet; booking pages come later.

## Positioning

An internal tool shaped exactly around this bank's data and rules: bilingual records (English and Khmer names side by side), a fixed place hierarchy (province → office → building → floor → room), the bank's organisation (department → division) that decides a person's province, and the API's rules enforced, not re-invented.

## Operating Context

- Daily, data-dense work at a desk: long lists, filters, quick edits. Laptop (1280 px) first, tablet (768 px) must work.
- Times from the API are UTC; people read Cambodia time (UTC+7). Room opening hours are already Cambodia time.
- Nothing is deleted except room photos; records are turned off instead.
- Door codes are secret and shown only on request.

## Capabilities and Constraints

- Requirements: `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (approved). API rules: `spec.md`, plain-language rules: `requirements.md`.
- UI language: English. Data shows English and Khmer names together.
- Build order: sign-in and layout → rooms → places → room types and equipment → organisation → users and roles.
- Undecided: permissions for non-Admin roles; booking pages.

## Brand Commitments

- National Bank of Cambodia meeting-room system. Keep the NBC theme of the existing mockup (`frontend_mockup/meeting_room_mockup`): dark crimson sidebar, crimson actions, warm cream canvas, Poppins + Kantumruy Pro (Khmer) + JetBrains Mono, Lucide stroke icons, no emoji.
- The NBC logo is approved for the sidebar: `frontend_mockup/meeting_room_mockup/assets/nbc-logo.png`.
- The owner wants it to look crafted, not like a generic AI admin template.

## Evidence on Hand

- Real organisation data: `scripts/seed_org.json` (Head Office with 41 departments, 19 provincial branches; division English names are draft translations).
- Demo places: `scripts/seed_demo.py`. Room photos and data in the mockup are demo content.
- No real usage numbers, screenshots of production, or user research exist; do not invent them.

## Product Principles

1. The API is the source of truth: same rules, same messages, no extra rules in the UI.
2. Dense and fast beats decorative: the Admin edits many records every day.
3. Bilingual by default: a record is never shown with only one of its names when both exist.
4. Nothing destructive by surprise: turn off instead of delete, confirm on the page, secrets only on request.
5. Never lose the Admin's work.
