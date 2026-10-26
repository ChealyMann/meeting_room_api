# 002 — Slide the sidebar when it folds and opens

- **Status**: DONE
- **Commit**: ff3524b
- **Severity**: MEDIUM (owner request: "I want a smooth animation for the left sidebar")
- **Category**: Missed opportunities (state change that teleports) + Easing & duration
- **Estimated scope**: 3 files — 1 token line in `main.css`, about 4 lines in `AppShell.vue`, about 60 lines of CSS in `AppRail.vue`. No script or markup changes.

## Problem

The fold button in the top bar (`admin_dashboard/src/layouts/AppTopbar.vue`, aria-label
"Collapse sidebar" / "Expand sidebar") toggles the class `compact` on the shell and on the
rail. Today everything changes in one frame:

1. The shell's first grid column jumps from 248px to 64px (and back):
   ```css
   /* admin_dashboard/src/layouts/AppShell.vue:42-48 — current */
   .shell {
     display: grid;
     grid-template-columns: 248px minmax(0, 1fr);
     height: 100vh;
     height: 100dvh;
     min-height: 640px;
   }
   ```
   ```css
   /* admin_dashboard/src/layouts/AppShell.vue:84-86 — current */
   .shell.compact {
     grid-template-columns: 64px minmax(0, 1fr);
   }
   ```
2. In the folded rail the icons are centred with different paddings than in the open rail,
   so every icon jumps sideways; the group headings (`h2`) are removed with
   `display: none`, so every nav item also jumps up; labels are removed at once.
   ```css
   /* admin_dashboard/src/layouts/AppRail.vue:299-333 — current */
   /* Folded rail (toggle, or always on tablets): icons only; links keep their names for screen readers. */
   .compact .brand {
     padding: 16px 14px;
   }
   .compact .brand-text,
   .compact .nav h2,
   .compact .me-text {
     display: none;
   }
   .compact .nav .label {
     position: absolute;
     width: 1px;
     height: 1px;
     overflow: hidden;
     clip-path: inset(50%);
     white-space: nowrap;
   }
   .compact .nav {
     padding: 8px 8px 16px;
   }
   .compact .nav a {
     justify-content: center;
     padding: 9px;
   }
   /* Initials over the sign-out button: the 64px rail still lets the user sign out. */
   .compact .who {
     flex-direction: column;
     justify-content: center;
     padding: 12px 8px;
   }
   .compact .me {
     flex: none;
     padding: 0;
   }
   ```

The open-rail rules these differ from (same file):

```css
/* admin_dashboard/src/layouts/AppRail.vue:133-140 — current */
.rail {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--color-rail);
  color: var(--color-rail-ink);
  border-right: 1px solid var(--color-rail-line);
}
/* :141-146 */
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
}
/* :166-171 */
.nav {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px 16px;
  scrollbar-color: var(--color-rail-line) transparent;
}
/* :180-191 */
.nav a {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 6px;
  color: var(--color-rail-ink);
  font-size: 13.5px;
  text-decoration: none;
  transition: background-color 120ms ease;
}
/* :226-232 */
.who {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 12px 12px 14px;
  border-top: 1px solid var(--color-rail-line);
}
/* :233-243 */
.me {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 4px 6px;
  border-radius: 6px;
  color: inherit;
  text-decoration: none;
}
```

## Target

The rail slides between 248px and 64px; the icons never move; text fades.

- **Width**: the shell's first column interpolates over **240ms** with the drawer curve
  `cubic-bezier(0.32, 0.72, 0, 1)` (new token `--ease-drawer`). Supported for
  `grid-template-columns` in Chrome 107+, Firefox 66+, Safari 16+; older browsers stay
  instant, which is today's behaviour.
- **Icons stay put**: the open and folded rails use the same left offsets, so nothing slides
  sideways. Icon centre in a 64px rail = 32px, so a 16px icon starts at 24px:
  nav padding 8px + link left padding 16px = 24px, in both states. The 36px logo starts at
  14px ((64 − 36) / 2) in both states. The 32px initials disc starts at 16px in both states
  (foot left padding 10px + `.me` left padding 6px).
- **Nothing moves vertically**: group headings keep their height in the folded rail; they
  only fade.
- **Text fades, in the right order**:
  - Folding: labels, headings and the brand name fade out over **100ms** with
    `var(--ease-out-quint)` (`cubic-bezier(0.23, 1, 0.32, 1)`), no delay — they are gone
    before the narrowing rail would cut them.
  - Opening: they fade in over **160ms**, `var(--ease-out-quint)`, after an **80ms** delay —
    so they appear once there is room, not squeezed.
  - A CSS transition uses the rule of the state it goes *to*, so the open-state rule holds
    the "fade in" timing and the `.compact` rule holds the "fade out" timing.
  - Labels stay in the accessibility tree (opacity, not `display: none`), so folded links
    keep their names for screen readers.
- **Clipping**: text is `white-space: nowrap` and the rail and links clip overflow, so no
  label wraps onto two lines while the width changes.
- **The user foot is the one instant part**: in the folded rail the sign-out button sits
  under the initials (column), in the open rail beside the name (row). That switch stays
  instant at the moment the class changes. Do not try to animate it.
- Reduced motion: already handled globally in `admin_dashboard/src/styles/main.css`
  (`@media (prefers-reduced-motion: reduce)` collapses every transition to 1ms). Add no
  other reduced-motion rule.

## Repo conventions to follow

- Easing tokens live in the `@theme` block of `admin_dashboard/src/styles/main.css`; the
  existing one is `--ease-out-quint: cubic-bezier(0.23, 1, 0.32, 1);` at line 45. Add the
  new curve right after it, same style.
- Exemplar of a token used in a component transition:
  `admin_dashboard/src/components/base/AppToast.vue:28-30`
  (`transition: opacity 200ms ease, transform 260ms var(--ease-out-quint);`).
- Component styles are plain CSS in `<style scoped>`; the rail's root `<aside>` carries the
  classes `rail`, `open` (phone drawer) and `compact` (folded).

## Steps

1. `admin_dashboard/src/styles/main.css`, inside `@theme`, directly after the line
   `  --ease-out-quint: cubic-bezier(0.23, 1, 0.32, 1);` add:
   ```css
     /* Panels that slide in or fold (the sidebar). */
     --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
   ```

2. `admin_dashboard/src/layouts/AppShell.vue`, replace the `.shell` rule (lines 42-48) with:
   ```css
   .shell {
     display: grid;
     grid-template-columns: 248px minmax(0, 1fr);
     height: 100vh;
     height: 100dvh;
     min-height: 640px;
     /* The rail slides when it folds or opens. */
     transition: grid-template-columns 240ms var(--ease-drawer);
   }
   ```
   Leave `.shell.compact` (lines 84-86) as it is.

3. `admin_dashboard/src/layouts/AppRail.vue`, in `<style scoped>`:

   a. Replace the `.rail` rule (lines 133-140) with:
   ```css
   .rail {
     display: flex;
     flex-direction: column;
     min-height: 0;
     overflow: hidden; /* clips text while the rail narrows */
     background: var(--color-rail);
     color: var(--color-rail-ink);
     border-right: 1px solid var(--color-rail-line);
   }
   ```

   b. Replace the `.brand` rule (lines 141-146) with:
   ```css
   .brand {
     display: flex;
     align-items: center;
     gap: 12px;
     padding: 20px 14px 16px; /* logo at 14px: centred in the 64px folded rail too */
   }
   ```

   c. Replace the `.nav` rule (lines 166-171) with:
   ```css
   .nav {
     flex: 1;
     overflow-x: hidden;
     overflow-y: auto;
     padding: 8px 8px 16px; /* same in both states, so icons never move */
     scrollbar-color: var(--color-rail-line) transparent;
   }
   ```

   d. In the `.nav h2` rule (lines 172-179), change `margin: 16px 8px 4px;` to
   `margin: 16px 8px 4px 16px;` and add `white-space: nowrap;` as its last declaration.

   e. Replace the `.nav a` rule (lines 180-191) with:
   ```css
   .nav a {
     position: relative;
     display: flex;
     align-items: center;
     gap: 10px;
     padding: 7px 10px 7px 16px; /* icon at 8 + 16 = 24px: centred in the 64px rail */
     overflow: hidden;
     border-radius: 6px;
     color: var(--color-rail-ink);
     font-size: 13.5px;
     text-decoration: none;
     white-space: nowrap;
     transition: background-color 120ms ease;
   }
   ```

   f. Replace the `.who` rule (lines 226-232) with:
   ```css
   .who {
     display: flex;
     align-items: center;
     gap: 4px;
     padding: 12px 12px 12px 10px; /* initials at 10 + 6 = 16px: centred in the 64px rail */
     border-top: 1px solid var(--color-rail-line);
   }
   ```

   g. Directly before the comment line
   `/* Folded rail (toggle, or always on tablets): icons only; links keep their names for screen readers. */`
   (line 299) insert:
   ```css
   /* Text that fades when the rail folds. Opening: fade in after the rail has made room. */
   .brand-text,
   .nav h2,
   .nav .label {
     white-space: nowrap;
     transition: opacity 160ms var(--ease-out-quint) 80ms;
   }
   ```

   h. Replace the whole folded block (lines 299-333, from that comment line through the
   closing `}` of `.compact .me`) with:
   ```css
   /* Folded rail (toggle, or always on tablets): icons only. Icons keep their place; text
      fades out fast (no delay) and stays in the accessibility tree, so links keep their names. */
   .compact .brand-text,
   .compact .nav h2,
   .compact .nav .label {
     opacity: 0;
     transition: opacity 100ms var(--ease-out-quint);
   }
   /* Initials over the sign-out button: the 64px rail still lets the user sign out.
      This switch is instant by design. */
   .compact .who {
     flex-direction: column;
     justify-content: center;
     padding: 12px 8px;
   }
   .compact .me {
     flex: none;
     padding: 0;
   }
   .compact .me-text {
     display: none;
   }
   ```

## Boundaries

- Do NOT change any template, script, prop or class name; CSS only (plus the one token).
- Do NOT touch the phone drawer rules (`@media (max-width: 760px)` in `AppRail.vue` and
  `AppShell.vue`) or the `.open` drawer animation.
- Do NOT animate `width`, `padding`, `margin` or `transform` on the rail or its children;
  only the shell's `grid-template-columns` and the text opacity.
- Do NOT animate the user foot (`.who`, `.me`).
- Do NOT touch `AppTopbar.vue`, `stores/ui.ts`, the day/night theme, or any other component.
- Do NOT add a reduced-motion rule; the global one covers it.
- Do NOT add dependencies.
- If the code does not match the excerpts above (drift since commit ff3524b), STOP and
  report instead of improvising.

## Verification

- **Mechanical** (run in `admin_dashboard/`):
  - `npm run test:unit -- --run` → all tests pass (`src/layouts/__tests__/shell.spec.ts`
    checks the `compact` class and the toggle labels).
  - `npm run type-check` → no errors.
  - `npm run lint` → no errors or warnings.
  - `npm run build` → builds.
  - `npx playwright test` → `e2e/shell-layout.spec.ts` passes (sign-out reachable at
    1280px, 900px and 390px).
- **Feel check**: `npm run dev`, sign in, window wider than 1100px, click the panel button
  at the left of the top bar several times.
  - The rail slides; the work area widens/narrows with it, smoothly.
  - Every nav icon and the logo stay exactly in place, horizontally and vertically, during
    the whole slide. (Check by keeping the mouse pointer on one icon while toggling.)
  - Folding: the labels are gone before the edge reaches them; no label wraps onto two
    lines or is cut mid-word.
  - Opening: the labels appear only after the rail has opened most of the way.
  - Clicking the button again mid-slide reverses smoothly from where it is (transitions
    retarget; nothing restarts from zero).
  - In Chrome DevTools > Animations, set playback to 10%: the width change starts fast and
    eases into place (drawer curve), with no sudden jump at the end.
  - DevTools > Performance, CPU throttling 4x: toggle on `/profile`; the slide stays
    smooth (no long frames). The grid change lays out the page each frame; if it stutters
    there, report it rather than changing the approach.
  - DevTools > Rendering, `prefers-reduced-motion: reduce`: the rail folds at once.
  - With a screen reader or the Accessibility pane, a folded nav link still has its name
    (e.g. "Rooms").
  - Resize the window across 1100px: the rail folds/opens with the same slide.
- **Done when**: all mechanical checks pass, the slide and fades behave as above, and no
  icon moves during the slide.
