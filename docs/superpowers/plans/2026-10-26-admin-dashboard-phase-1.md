# Admin Dashboard Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working Vue admin dashboard with sign-in, first password change, automatic token refresh, Admin-only access, the app shell (rail + top bar) and the My profile page.

**Architecture:** A Vite + Vue 3 single-page app in `admin_dashboard/`. One small fetch client talks to the FastAPI API, turns every error into one `ApiError` type, and refreshes the access token once on a 401. A Pinia session store owns the tokens and the signed-in user; one pure function decides every route redirect. Screens are built from a few base components styled with the approved NBC tokens.

**Tech Stack:** Vue 3 (Composition API, `<script setup lang="ts">`), TypeScript, Vite, Vue Router, Pinia, Tailwind CSS v4 (`@tailwindcss/vite`), `lucide-vue-next`, `openapi-typescript`, Vitest + `@vue/test-utils` + jsdom, Playwright, ESLint (from `create-vue`).

**Spec:** `docs/superpowers/specs/2026-10-26-admin-dashboard-requirements.md` (DSH-A01 to DSH-A09, sections 6, 8, 9). Visual source of truth: `docs/design/admin-direction.html` and `DESIGN.md` (with `.impeccable/design.json`). Product context: `PRODUCT.md`.

## Global Constraints

- Work on branch `feature/dashboard-phase-1`. Commit messages carry no AI attribution lines.
- App lives in `admin_dashboard/` with its own `package.json`; Node ≥ 20 (machine has 24).
- API origin from `VITE_API_URL` (default `http://localhost:8000`); every path starts with `/api/v1/`.
- Access token in memory only. Refresh token in `sessionStorage` under key `nbc.admin.refresh` (closing the browser signs out).
- API error shape: `{"error": {"code": string, "message": string, "fields"?: {[field]: message}}}`; `Retry-After` header (seconds) on 429.
- Only users whose `GET /api/v1/me` roles include code `ADMIN` get past sign-in; others see "You do not have access" and a sign-out button.
- While `must_change_password` is true, only the change-password page opens (API allows only `GET /me`, change-password, logout).
- API datetimes are UTC with `Z`; show them in `Asia/Phnom_Penh` (UTC+7). Top bar clock: `Phnom Penh HH:MM` (24-hour).
- English UI. No emoji. Icons: Lucide, stroke width 1.75. No badges or pills for state; no card boxes around tables.
- Colours/fonts from DESIGN.md: rail `#260707`, raised `#3A0D0D`, gold thread `#E2B33C`, paper `#F9F7F5`, sheet `#FFFFFF`, rule `#E9E3DD`, strong rule `#D8CFC7`, ink `#2A1C13`, intaglio brown `#6B5243`, crimson `#991B1B` (hover `#7F1D1D`), ok `#2F6B3F`; Poppins (UI), Kantumruy Pro (Khmer), JetBrains Mono (serials, times, counts).
- Saving shows a quiet toast with a check icon; no seal animation (owner decision).
- Password rules shown before sending (same as API R18): 8 to 128 characters, not the email (ignoring case), never trimmed; a new password must differ from the current one.

## Review Focus

- Two calls get 401 at the same moment → exactly one refresh request, both calls retried with the new token (test in Task 3).
- The page is reloaded with an expired or revoked refresh token → the user lands on sign-in with no loop and no blank screen (test in Task 5).
- The API is down or unreachable (`fetch` throws) → sign-in shows "Can't reach the server. Check the API is running." instead of crashing (tests in Tasks 3 and 8).
- An error body that is not JSON (a 502 HTML page from a proxy) → a plain "Something went wrong (502)." message, never `[object Object]` (test in Task 2).
- A signature file the API refuses (413 FILE_TOO_LARGE, 415, 422 INVALID_IMAGE) → the API's message shows under the signature field and the old signature stays (test in Task 10).

---

### Task 1: Project scaffold and API CORS

**Files:**
- Create: `admin_dashboard/` (via `create-vue`), `admin_dashboard/.env.example`, `admin_dashboard/src/styles/main.css`
- Modify: `admin_dashboard/vite.config.ts`, `admin_dashboard/package.json` (scripts), `.env.example` (API), `.env` (API, local)
- Delete: create-vue demo files (`src/components/HelloWorld.vue`, `TheWelcome.vue`, `WelcomeItem.vue`, `icons/`, `views/AboutView.vue`, demo store `counter.ts`, their tests)
- Test: `admin_dashboard/src/__tests__/App.spec.ts`

**Interfaces:**
- Produces: npm scripts `dev`, `build`, `test:unit`, `test:e2e`, `lint`, `type-check`, `gen:api`; Tailwind loaded through `src/styles/main.css`.

- [ ] **Step 1: Scaffold.** From repo root run `npm create vue@latest admin_dashboard -- --ts --router --pinia --vitest --playwright --eslint` (accept defaults), then `cd admin_dashboard && npm install && npm install -D tailwindcss @tailwindcss/vite openapi-typescript && npm install lucide-vue-next`.
- [ ] **Step 2: Wire Tailwind.** Add `tailwindcss()` from `@tailwindcss/vite` to `vite.config.ts` plugins. Create `src/styles/main.css` starting with `@import "tailwindcss";` and import it from `src/main.ts` (replace the demo CSS import). Add the Google Fonts `<link>` for Poppins 400/500/600/700, Kantumruy Pro 400/500, JetBrains Mono 400/500 to `index.html`; set `<title>NBC Meeting Rooms · Admin</title>` and the favicon from `docs/design/assets/nbc-logo.png` (copy to `admin_dashboard/public/nbc-logo.png`).
- [ ] **Step 3: Scripts and env.** In `package.json` add `"gen:api": "openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts"`. Create `.env.example` with `VITE_API_URL=http://localhost:8000`. Add `admin_dashboard/.env.local`, `node_modules`, `dist`, `test-results`, `playwright-report` to `admin_dashboard/.gitignore` (create-vue adds most).
- [ ] **Step 4: API CORS.** In the API's `.env.example` and local `.env`, set `CORS_ORIGINS=http://localhost:3000,http://localhost:5173`.
- [ ] **Step 5: Smoke test.** Replace the demo `App.spec.ts` with a test that mounts `App.vue` with a memory router and Pinia and asserts it renders without throwing.
- [ ] **Step 6: Verify.** Run `npm run test:unit -- --run`, `npm run type-check`, `npm run lint`, `npm run build` in `admin_dashboard/`. Expected: all pass.
- [ ] **Step 7: Commit** `admin_dashboard/` (no `node_modules`) and the API `.env.example` change: `git commit -m "Scaffold admin dashboard (Vue 3, TypeScript, Vite, Tailwind) and allow its dev origin"`.

### Task 2: API types and error parsing

**Files:**
- Create: `admin_dashboard/src/api/schema.d.ts` (generated), `admin_dashboard/src/api/types.ts`, `admin_dashboard/src/api/errors.ts`
- Test: `admin_dashboard/src/api/__tests__/errors.spec.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `Tokens`, `UserDetail`, `MeUpdate`, `RoleRef` re-exported from `components['schemas']` of `schema.d.ts` (names as in the OpenAPI document).
  - `errors.ts`: `class ApiError extends Error { status: number; code: string; fields: Record<string, string>; retryAfterSeconds: number | null }`; `parseApiError(response: Response): Promise<ApiError>`; `networkError(cause: unknown): ApiError` with `status 0`, `code "NETWORK_ERROR"`, message `"Can't reach the server. Check the API is running."`.

- [ ] **Step 1: Generate types.** Start the API (`run.bat`), then `npm run gen:api`. Expected: `src/api/schema.d.ts` contains `Tokens` and `UserDetail`.
- [ ] **Step 2: Write failing tests** in `errors.spec.ts`:
  - `parseApiError` on 422 `{"error":{"code":"VALIDATION_ERROR","message":"Invalid request.","fields":{"phone":"Too long (max 20)."}}}` → `status 422`, `code "VALIDATION_ERROR"`, `fields.phone === "Too long (max 20)."`.
  - On 429 with header `Retry-After: 840` and code `RATE_LIMITED` → `retryAfterSeconds === 840`.
  - On 502 with body `<html>Bad gateway</html>` → `code "HTTP_502"`, message `"Something went wrong (502)."`, `fields` is `{}`.
  - `networkError(new TypeError("Failed to fetch"))` → `status 0`, `code "NETWORK_ERROR"`, message as above.
- [ ] **Step 3: Run** `npm run test:unit -- --run src/api/__tests__/errors.spec.ts`. Expected: FAIL (module missing).
- [ ] **Step 4: Implement** `errors.ts` and `types.ts` to the interfaces above.
- [ ] **Step 5: Run** the same command. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: generated API types and one ApiError type"`.

### Task 3: HTTP client with one-time token refresh

**Files:**
- Create: `admin_dashboard/src/api/client.ts`
- Test: `admin_dashboard/src/api/__tests__/client.spec.ts`

**Interfaces:**
- Consumes: `ApiError`, `parseApiError`, `networkError` (Task 2).
- Produces:
  - `interface ClientOptions { baseUrl: string; getAccessToken(): string | null; refresh(): Promise<boolean>; onAuthLost(): void; fetchImpl?: typeof fetch }`
  - `createApiClient(options: ClientOptions)` returning `{ request<T>(method: 'GET'|'POST'|'PUT'|'PATCH'|'DELETE', path: string, body?: { json?: unknown; form?: FormData }): Promise<T>; requestBlob(path: string): Promise<Blob> }`
  - `request` returns `undefined` for 204; sends `Authorization: Bearer <token>` when a token exists; sets `Content-Type: application/json` only for `json` bodies (never for `form`).
  - On 401: calls `refresh()` once (concurrent 401s share the same pending refresh), then repeats the call once. If refresh returns false or the retry is 401 again: calls `onAuthLost()` and throws the 401 `ApiError`.
  - `fetch` throwing → `networkError`.

- [ ] **Step 1: Write failing tests** with a fake `fetchImpl`:
  - `request('GET','/api/v1/me')` sends `Authorization: Bearer A1` to `http://localhost:8000/api/v1/me`.
  - 204 response → resolves `undefined`.
  - `form` body → no `Content-Type` header set by the client.
  - 401 then refresh → retried with the new token, resolves the 200 body; `refresh` called once.
  - Two parallel requests both get 401 → `refresh` called exactly once; both resolve.
  - Refresh returns false → `onAuthLost` called once; promise rejects with `status 401`.
  - `fetchImpl` throws `TypeError` → rejects with `code "NETWORK_ERROR"`.
  - `requestBlob('/api/v1/users/2/signature')` returns the response blob and sends the bearer token.
- [ ] **Step 2: Run** `npm run test:unit -- --run src/api/__tests__/client.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `client.ts`. Keep one module-level `pendingRefresh: Promise<boolean> | null` per client instance for the single-flight refresh.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: API client with single-flight token refresh"`.

### Task 4: Auth and profile endpoint functions

**Files:**
- Create: `admin_dashboard/src/api/auth.ts`, `admin_dashboard/src/api/me.ts`
- Test: `admin_dashboard/src/api/__tests__/endpoints.spec.ts`

**Interfaces:**
- Consumes: `Tokens`, `UserDetail`, `MeUpdate` (Task 2); `createApiClient` (Task 3).
- Produces:
  - `auth.ts` (plain `fetch`, no refresh retry, errors via `parseApiError`/`networkError`): `login(baseUrl, email, password): Promise<Tokens>` (POST `/api/v1/auth/login`, body `{email, password}`), `refreshTokens(baseUrl, refreshToken): Promise<Tokens>` (POST `/api/v1/auth/refresh`, `{refresh_token}`).
  - `me.ts` (through the client): `getMe(client): Promise<UserDetail>`, `updateMe(client, changes: MeUpdate): Promise<UserDetail>` (PATCH `/api/v1/me`), `changePassword(client, current: string, next: string): Promise<Tokens>` (POST `/api/v1/auth/change-password`, `{current_password, new_password}`), `logout(client, refreshToken: string | null): Promise<void>` (POST `/api/v1/auth/logout`, body `{refresh_token}` or none), `uploadMySignature(client, file: File): Promise<UserDetail>` (PUT `/api/v1/me/signature`, `FormData` field `file`), `deleteMySignature(client): Promise<void>` (DELETE `/api/v1/me/signature`), `getSignatureBlob(client, signatureUrl: string): Promise<Blob>` (GET the `signature_url` path from `UserDetail`).

- [ ] **Step 1: Write failing tests** asserting method, path and body for each function above (fake `fetchImpl`): `login` body is exactly `{"email":"Admin@Company.com","password":" pw with spaces "}` (no trimming of the password in the client); `uploadMySignature` sends a `FormData` whose `file` entry is the given `File`; `updateMe(client, {phone: "012 345 678"})` sends PATCH with exactly that body.
- [ ] **Step 2: Run** `npm run test:unit -- --run src/api/__tests__/endpoints.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `auth.ts` and `me.ts`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: auth and profile API functions"`.

### Task 5: Session store and route guard

**Files:**
- Create: `admin_dashboard/src/stores/session.ts`, `admin_dashboard/src/router/guard.ts`, `admin_dashboard/src/api/index.ts`
- Modify: `admin_dashboard/src/router/index.ts`, `admin_dashboard/src/main.ts`
- Test: `admin_dashboard/src/stores/__tests__/session.spec.ts`, `admin_dashboard/src/router/__tests__/guard.spec.ts`

**Interfaces:**
- Consumes: Tasks 2 to 4.
- Produces:
  - `api/index.ts`: `api` = the app's single client, built with `baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'` and wired to the session store (`getAccessToken`, `refresh`, `onAuthLost → session.expire()`).
  - `useSessionStore` (Pinia, setup style): state `accessToken: string | null`, `user: UserDetail | null`, `ready: boolean`; getters `signedIn`, `isAdmin` (roles include code `ADMIN`), `mustChangePassword` (`user?.must_change_password`); actions `signIn(email, password): Promise<void>` (login → store tokens → `loadMe`), `restore(): Promise<void>` (on start: refresh token in `sessionStorage['nbc.admin.refresh']` → refresh → `loadMe`; any failure clears it; always sets `ready`), `refresh(): Promise<boolean>`, `loadMe(): Promise<void>`, `applyTokens(tokens: Tokens): void`, `changePassword(current, next): Promise<void>` (stores the returned tokens, reloads user), `signOut(): Promise<void>` (calls `logout`, ignores its failure, clears everything), `expire(): void` (clears tokens and user, keeps `ready`).
  - `guard.ts`: `type Nav = { name: string; fullPath: string; meta: { public?: boolean } }`; `resolveNavigation(to: Nav, s: { signedIn: boolean; mustChangePassword: boolean; isAdmin: boolean }): true | { name: string; query?: Record<string, string> }`.
  - Routes (names): `sign-in` (public, `/sign-in`), `change-password` (`/change-password`), `no-access` (`/no-access`), `shell` (`/`, component `AppShell`) with children `home` (`''`, placeholder "Rooms are built in Phase 2") and `profile` (`profile`). `router.beforeEach` awaits `session.restore()` once, then applies `resolveNavigation`.

- [ ] **Step 1: Write failing guard tests** (`resolveNavigation`): not signed in + `home` → `{ name: 'sign-in', query: { redirect: '/' } }`; not signed in + `sign-in` → `true`; signed in + must change + `profile` → `{ name: 'change-password' }`; signed in + must change + `change-password` → `true`; signed in + not admin + `home` → `{ name: 'no-access' }`; admin + `sign-in` → `{ name: 'home' }`; admin + `profile` → `true`.
- [ ] **Step 2: Write failing store tests** (fake `fetch` via the client's `fetchImpl`, `sessionStorage` from jsdom): `signIn` keeps the access token in memory and the refresh token only in `sessionStorage['nbc.admin.refresh']`; `isAdmin` false for roles `[STAFF]`; `restore` with a stored refresh token that gets 401 ends with `signedIn === false`, `ready === true` and the key removed; `signOut` clears state even when logout fails with 500.
- [ ] **Step 3: Run** `npm run test:unit -- --run src/stores src/router`. Expected: FAIL.
- [ ] **Step 4: Implement** `session.ts`, `guard.ts`, `api/index.ts`, and the routes in `router/index.ts` (lazy-load views).
- [ ] **Step 5: Run** the same command. Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "Dashboard: session store, token storage and route guard"`.

### Task 6: Theme tokens and base components

**Files:**
- Modify: `admin_dashboard/src/styles/main.css`
- Create: `admin_dashboard/src/components/base/BaseButton.vue`, `BaseField.vue`, `FormErrorSummary.vue`, `AppToast.vue`, `admin_dashboard/src/composables/useToast.ts`, `admin_dashboard/src/composables/useFieldErrors.ts`
- Test: `admin_dashboard/src/components/base/__tests__/base.spec.ts`, `admin_dashboard/src/composables/__tests__/useFieldErrors.spec.ts`

**Interfaces:**
- Produces:
  - `main.css`: `@theme` tokens for every DESIGN.md colour and the three font families; base rules for `::selection`, `caret-color`, focus ring (2px crimson, offset 2px), thin themed scrollbars; component classes `.input`, `.input.has-error`, `select.input` (chevron), `.mono` (tabular nums) copied in spirit from `docs/design/admin-direction.html`.
  - `BaseButton.vue`: props `variant: 'primary' | 'secondary' | 'quiet' | 'danger' = 'secondary'`, `busy = false`, `type = 'button'`; when busy: disabled and shows a spinner plus the default slot.
  - `BaseField.vue`: props `id: string`, `label: string`, `hint?: string`, `error?: string`; default slot for the control; renders the error with `id="<id>-error"` and the field wrapper class `has-error` when `error` is set.
  - `FormErrorSummary.vue`: prop `errors: Array<{ id: string; label: string }>`; renders "N field(s) need attention:" plus one link per field; clicking a link focuses `#id`.
  - `useToast()`: `{ toasts, show(title: string, detail?: string) }`; `AppToast.vue` shows the newest toast with a Lucide `CircleCheck` icon, auto-hides after 4200 ms.
  - `useFieldErrors()`: `{ errors: Ref<Record<string,string>>, formMessage: Ref<string>, apply(err: unknown): void, clear(): void }` — `apply` copies `ApiError.fields` into `errors` and `ApiError.message` into `formMessage`; non-`ApiError` values set `formMessage` to `"Something went wrong."`.

- [ ] **Step 1: Write failing tests:** `BaseButton` with `busy` is disabled and contains the slot text; `BaseField` with `error="Too long (max 20)."` renders that text with id `phone-error`; `FormErrorSummary` with two errors renders "2 fields need attention:" and clicking "Phone" focuses the element with id `phone`; `useFieldErrors.apply(new ApiError(...fields {phone}))` sets `errors.value.phone`.
- [ ] **Step 2: Run** `npm run test:unit -- --run src/components src/composables`. Expected: FAIL.
- [ ] **Step 3: Implement** the files above with the DESIGN.md values.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: NBC theme tokens and base form components"`.

### Task 7: App shell

**Files:**
- Create: `admin_dashboard/src/layouts/AppShell.vue`, `admin_dashboard/src/layouts/AppRail.vue`, `admin_dashboard/src/layouts/AppTopbar.vue`, `admin_dashboard/src/layouts/nav.ts`, `admin_dashboard/src/utils/time.ts`, `admin_dashboard/src/views/HomeView.vue`
- Test: `admin_dashboard/src/utils/__tests__/time.spec.ts`, `admin_dashboard/src/layouts/__tests__/shell.spec.ts`

**Interfaces:**
- Consumes: `useSessionStore` (Task 5), `AppToast` (Task 6).
- Produces:
  - `time.ts`: `formatPhnomPenh(isoUtc: string): string` → e.g. `"23 Oct 2026, 13:51"` for `"2026-10-23T06:51:03Z"`; `phnomPenhClock(now: Date): string` → `"HH:MM"` (24-hour).
  - `nav.ts`: `NAV_GROUPS: Array<{ title: string | null; items: Array<{ label: string; icon: string; route?: string }> }>` — groups and labels exactly as the direction page (Rooms; Places: Offices, Buildings, Floors; Catalog: Room types, Equipment; Organisation: Departments, Divisions, Positions; People: Users, Roles). Only `Rooms` (route `home`) has a route in Phase 1; items without a route render as disabled links with `aria-disabled="true"` and the title "Coming soon".
  - Shell layout per DESIGN.md: rail 248px with logo, grouped nav, gold windowed 1px security thread on the active item, user foot (initials, name, email, sign-out button → `session.signOut()` then route `sign-in`); top bar with breadcrumb from `route.meta.title` and clock `Phnom Penh HH:MM` updated every 30 s; `<RouterView>` in the work area; `AppToast` mounted once. Rail collapses to 64px icons at ≤1100px and hides at ≤760px.

- [ ] **Step 1: Write failing tests:** `formatPhnomPenh("2026-10-23T06:51:03Z") === "23 Oct 2026, 13:51"`; `phnomPenhClock(new Date("2026-10-23T23:30:00Z")) === "06:30"`; mounting `AppShell` on route `home` marks the Rooms link `aria-current="page"`, renders "Offices" with `aria-disabled="true"`, shows the user's name from the store, and clicking "Sign out" calls `signOut`.
- [ ] **Step 2: Run** `npm run test:unit -- --run src/utils src/layouts`. Expected: FAIL.
- [ ] **Step 3: Implement** the files above.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: app shell with rail, top bar and Phnom Penh clock"`.

### Task 8: Sign-in and no-access pages

**Files:**
- Create: `admin_dashboard/src/views/SignInView.vue`, `admin_dashboard/src/views/NoAccessView.vue`
- Test: `admin_dashboard/src/views/__tests__/sign-in.spec.ts`

**Interfaces:**
- Consumes: `useSessionStore.signIn`, `BaseButton`, `BaseField`, `useFieldErrors`.
- Produces: route components for `sign-in` and `no-access`.

- [ ] **Step 1: Write failing tests:** submitting with a 401 `INVALID_CREDENTIALS` shows the API message and keeps the typed email; a 429 with `retryAfterSeconds 840` shows "Too many tries. Try again in 14 minutes." (minutes = ceil(seconds / 60), "1 minute" when 1); a `NETWORK_ERROR` shows "Can't reach the server. Check the API is running."; success navigates to `route.query.redirect` or `home`; the submit button is busy while waiting; the password value is sent untrimmed. `NoAccessView` shows "You do not have access" and a working "Sign out" button.
- [ ] **Step 2: Run** `npm run test:unit -- --run src/views/__tests__/sign-in.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** both views (sign-in: NBC logo, "Meeting Rooms Admin", email + password fields with show/hide, one primary button "Sign in"; layout per DESIGN.md, centred on paper, no card shadow stack).
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: sign-in and no-access pages"`.

### Task 9: Change password page

**Files:**
- Create: `admin_dashboard/src/views/ChangePasswordView.vue`, `admin_dashboard/src/utils/password.ts`
- Test: `admin_dashboard/src/utils/__tests__/password.spec.ts`, `admin_dashboard/src/views/__tests__/change-password.spec.ts`

**Interfaces:**
- Consumes: `useSessionStore.changePassword`, base components (Task 6).
- Produces: `passwordProblem(next: string, email: string, current: string): string | null` returning exactly `"Password must be 8 to 128 characters."`, `"Password cannot be your email."`, `"Use a new password."` or `null`.

- [ ] **Step 1: Write failing tests:** `passwordProblem("short", ...)` → length message; 129 chars → length message; `"ADMIN@company.com"` with email `admin@company.com` → email message; same as current → "Use a new password."; `" abc12345"` vs current `"abc12345"` → `null` (spaces count). View: 400 `WRONG_PASSWORD` shows its message under "Current password"; a 422 `fields.new_password` shows under "New password"; "Confirm new password" mismatch shows "The passwords do not match." without calling the API; success stores the new tokens and navigates to `home` with toast "Password changed".
- [ ] **Step 2: Run** `npm run test:unit -- --run src/utils/__tests__/password.spec.ts src/views/__tests__/change-password.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `password.ts` and the view (also shows a sign-out link, since this is the only page a must-change user can open).
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: first-sign-in password change"`.

### Task 10: My profile page

**Files:**
- Create: `admin_dashboard/src/views/ProfileView.vue`, `admin_dashboard/src/components/SignatureField.vue`, `admin_dashboard/src/stores/drafts.ts`
- Test: `admin_dashboard/src/views/__tests__/profile.spec.ts`, `admin_dashboard/src/components/__tests__/signature.spec.ts`

**Interfaces:**
- Consumes: `getMe`, `updateMe`, `uploadMySignature`, `deleteMySignature`, `getSignatureBlob` (Task 4); `api`, `useSessionStore` (Task 5); base components and `useToast` (Task 6); `formatPhnomPenh` (Task 7).
- Produces:
  - `useDraftsStore` (Pinia, memory only): `get<T>(key: string): T | undefined`, `set(key: string, value: unknown): void`, `clear(key: string): void` — keeps unsaved form values across a forced sign-in (DSH-A06).
  - `ProfileView`: read-only block (name EN over KH, staff ID, email, position, division, department, province, roles in seed order, last sign-in in Phnom Penh time) and an edit form for `secondary_email`, `phone`, `avatar_url`, `email_notifications`. Save sends only changed fields; empty text sends `null`; draft key `profile`. While `getMe` loads, show skeleton lines (DESIGN.md loading pattern), not a full-page spinner.
  - `SignatureField`: shows the signature from `getSignatureBlob` as an object URL (revoked on change/unmount) on a checkerboard-free plain sheet, "Upload signature" (accept `image/jpeg,image/png,image/webp`) and "Remove" with an inline confirm; hint "Sign with a dark pen on blank white paper.".

- [ ] **Step 1: Write failing tests:** changing only phone sends `PATCH {"phone":"012 345 678"}`; clearing the second email sends `{"secondary_email": null}`; a 422 `fields.secondary_email = "Second email must be different."` shows under that field and the summary lists it; after save the toast "Profile saved" shows and the draft is cleared; with a draft in the store, mounting shows the draft values. Signature: upload sends the file; on 413 `FILE_TOO_LARGE` the API message shows under the field and the previous image stays; "Remove" asks first, then calls DELETE and shows "No signature yet".
- [ ] **Step 2: Run** `npm run test:unit -- --run src/views/__tests__/profile.spec.ts src/components/__tests__/signature.spec.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** the files above; add the `profile` route title "My profile" and the user foot link in the rail to it.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: My profile page with signature"`.

### Task 11: End-to-end check and README

**Files:**
- Create: `admin_dashboard/e2e/phase1.spec.ts`, `admin_dashboard/README.md`
- Modify: `admin_dashboard/playwright.config.ts` (base URL `http://localhost:5173`, start `npm run dev` as web server)

**Interfaces:**
- Consumes: everything above. Needs the API running (`run.bat`) and env vars `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD` (an Admin whose password is already changed); the spec skips itself when they are unset.

- [ ] **Step 1: Write the e2e test:** sign in → shell shows "Rooms" active and the Phnom Penh clock → open My profile → change phone to `012 345 678` → toast "Profile saved" → reload → still signed in and the phone is kept → sign out → sign-in page. Then set the phone back.
- [ ] **Step 2: Run** `npm run test:e2e` with the env vars set and the API running. Expected: PASS (or SKIPPED without env vars).
- [ ] **Step 3: README:** setup (`npm install`, copy `.env.example` to `.env.local`), `npm run dev`, `npm run gen:api` after API changes, test commands, the CORS line the API needs, token storage rule (refresh token in sessionStorage, access token in memory).
- [ ] **Step 4: Full verification** in `admin_dashboard/`: `npm run lint`, `npm run type-check`, `npm run test:unit -- --run`, `npm run build`. Expected: all pass. In the repo root: `.venv/Scripts/python -m pytest -q` still passes (only the CORS env example changed).
- [ ] **Step 5: Commit** `git commit -m "Dashboard: phase 1 end-to-end check and README"`.
