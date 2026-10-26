# NBC Meeting Rooms · Admin dashboard

The admin dashboard for the meeting-room booking API in this repository.
Vue 3 (Composition API, `<script setup>`), TypeScript, Vite, Pinia, Vue Router, Tailwind CSS 4.

Phase 1 has: sign-in, the first password change, Admin-only access, the app shell, and My profile (with my signature).
The design rules are in [`../DESIGN.md`](../DESIGN.md).

## Setup

You need Node.js 22.18+ (or 24.12+) and the API running (`run.bat` in the repository root).

```sh
npm install
cp .env.example .env.local   # VITE_API_URL=http://localhost:8000
npm run dev                  # http://localhost:5173
```

The API must allow this origin. In the API `.env`:

```
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## API types

`src/api/schema.d.ts` is made from the API's OpenAPI document. Run this after the API changes (the API must be running):

```sh
npm run gen:api
```

## Tests and checks

```sh
npm run test:unit -- --run   # unit tests (Vitest)
npm run type-check
npm run lint
npm run build
```

End-to-end test (Playwright, Chromium). It needs the API running and an Admin account whose password is already changed. Without the two variables it is skipped.

```sh
npx playwright install chromium   # first time only
E2E_ADMIN_EMAIL=admin@company.com E2E_ADMIN_PASSWORD='...' npm run test:e2e
```

The test changes the account's phone, checks it after a reload, then puts it back.

## How sign-in works

- **Access token:** in memory only. It lasts 15 minutes.
- **Refresh token:** in `sessionStorage` (`nbc.admin.refresh`), so a reload keeps you signed in and closing the browser signs you out. Nothing goes to `localStorage`.
- When a call gets 401, the app refreshes the token once and repeats the call. Calls that fail at the same time share one refresh. If the refresh is refused, you go to sign-in and come back to the same page after.
- A user with `must_change_password` can open only the "Choose a new password" page.
- A user without the `ADMIN` role sees "You do not have access" and a Sign out button.
- Unsaved profile changes are kept in memory while you sign in again.
- Times from the API are UTC; the dashboard shows Phnom Penh time.
