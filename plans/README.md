# Animation plans

Written by the `improve-animations` audit of the admin dashboard's `/profile` page
(commit `17e4ef5`). Each plan is self-contained: hand it to any agent to execute.

| # | Plan | Severity | Status |
| --- | --- | --- | --- |
| 001 | [Fade the profile photo and signature in instead of popping](001-fade-in-profile-images.md) | LOW | DONE |
| 002 | [Slide the sidebar when it folds and opens](002-slide-the-sidebar-fold.md) | MEDIUM | DONE |

## Execution order

1. 001 — no dependencies (done).
2. 002 — no dependencies (done).

## Audit findings not planned yet

From the same audit; turn any of them into a plan when wanted.

- Back-to-back toasts jump for 160ms (`admin_dashboard/src/components/base/AppToast.vue:15`, `:32-34`): take the leaving toast out of the flow.
- Loading shimmer uses `ease-in-out` (`admin_dashboard/src/styles/main.css:364`): constant motion should be `linear`.
- The Remove confirm swaps in instantly (`admin_dashboard/src/components/AvatarField.vue:74-87`, same in `SignatureField.vue`): a short opacity + 4px enter.
- Day/night switch tears (`admin_dashboard/src/stores/ui.ts:33` with colour transitions at `admin_dashboard/src/styles/main.css:155`, `:228`, `:279`, `:442`, `admin_dashboard/src/layouts/AppRail.vue:190`): the page changes in one frame while buttons, inputs and the switch fade for ~150ms. Turn transitions off for the one frame of the switch.
