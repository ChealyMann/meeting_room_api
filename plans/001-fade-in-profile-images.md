# 001 — Fade the profile photo and signature in instead of popping

- **Status**: DONE
- **Commit**: 17e4ef5
- **Severity**: LOW
- **Category**: Missed opportunities (state changes that teleport)
- **Estimated scope**: 2 files, about 10 lines of CSS and 2 attributes

## Problem

On My profile (`/profile`), the photo and the signature are private images: each one is
downloaded with the user's token and shown from an object URL. When the download finishes,
the `<img>` appears in a single frame. The same happens after the user uploads a new photo
or signature: the old image is replaced by the new one in one frame. Every visit to the
profile page shows this pop twice (photo and signature), so it is the most frequently seen
motion seam on the page.

The `<img>` keeps the same element when its `src` changes, so even a CSS entrance would
only run the first time, not on replace.

```vue
<!-- admin_dashboard/src/components/AvatarField.vue:67-70 — current -->
      <div class="disc" :aria-busy="loading || undefined">
        <img v-if="imageUrl" :src="imageUrl" alt="Your photo" />
        <span v-else-if="!loading" class="empty">No photo yet</span>
      </div>
```

```css
/* admin_dashboard/src/components/AvatarField.vue:134-139 — current */
.disc img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
```

```vue
<!-- admin_dashboard/src/components/SignatureField.vue:100-104 — current -->
    <div class="sheet" :aria-busy="loading || undefined">
      <div v-if="loading" class="skeleton-bar" aria-hidden="true" />
      <img v-else-if="imageUrl" :src="imageUrl" alt="Your signature" />
      <p v-else class="empty">No signature yet</p>
    </div>
```

```css
/* admin_dashboard/src/components/SignatureField.vue:165-170 — current */
.sheet img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
```

## Target

Each image fades in over 200ms with the repo's strong ease-out curve, both on first load
and every time it is replaced. Opacity only: the image sits in a fixed frame (a circle, a
sheet), so it should not move or scale.

- Entry uses CSS `@starting-style`. No JavaScript, no Vue `<Transition>`, no keyframes.
- `:key="imageUrl"` on the `<img>` makes Vue create a new element for each new object URL,
  so `@starting-style` applies again on replace.
- Browsers without `@starting-style` (older than Chrome 117, Safari 17.5, Firefox 129)
  simply show the image at once, which is today's behaviour.

```css
/* target, in both components' image rules */
  opacity: 1;
  transition: opacity 200ms var(--ease-out-quint);

  @starting-style {
    opacity: 0;
  }
```

`--ease-out-quint` is `cubic-bezier(0.23, 1, 0.32, 1)`, already defined in
`admin_dashboard/src/styles/main.css:43`. Do not add a new token.

## Repo conventions to follow

- Easing tokens live in the `@theme` block of `admin_dashboard/src/styles/main.css`; the
  strong ease-out is `--ease-out-quint` (line 43). Use it by name.
- DESIGN.md: "Ease-out-quint for things that travel …; plain `ease` for colour". An image
  entrance is an entrance, so it takes the ease-out curve (the toast does the same).
- Exemplar of an entrance in this repo:
  `admin_dashboard/src/components/base/AppToast.vue:27-31`
  (`transition: opacity 200ms ease, transform 260ms var(--ease-out-quint);`).
- Reduced motion is already handled globally in `admin_dashboard/src/styles/main.css:440-448`
  (every transition collapses to 1ms). Do not add a second reduced-motion rule.
- Component styles are `<style scoped>` plain CSS inside each `.vue` file.

## Steps

1. `admin_dashboard/src/components/AvatarField.vue`, template: add `:key="imageUrl"` to the
   `<img>`. Result:
   ```vue
        <img v-if="imageUrl" :key="imageUrl" :src="imageUrl" alt="Your photo" />
   ```
2. `admin_dashboard/src/components/AvatarField.vue`, `<style scoped>`: replace the
   `.disc img` rule with:
   ```css
   .disc img {
     display: block;
     width: 100%;
     height: 100%;
     object-fit: cover;
     /* Fades in on load and on every replace (a new key = a new element). */
     opacity: 1;
     transition: opacity 200ms var(--ease-out-quint);

     @starting-style {
       opacity: 0;
     }
   }
   ```
3. `admin_dashboard/src/components/SignatureField.vue`, template: add `:key="imageUrl"` to
   the `<img>`. Result:
   ```vue
      <img v-else-if="imageUrl" :key="imageUrl" :src="imageUrl" alt="Your signature" />
   ```
4. `admin_dashboard/src/components/SignatureField.vue`, `<style scoped>`: replace the
   `.sheet img` rule with:
   ```css
   .sheet img {
     display: block;
     width: 100%;
     height: 100%;
     object-fit: contain;
     /* Fades in on load and on every replace (a new key = a new element). */
     opacity: 1;
     transition: opacity 200ms var(--ease-out-quint);

     @starting-style {
       opacity: 0;
     }
   }
   ```

## Boundaries

- Do NOT touch `admin_dashboard/src/composables/usePrivateImage.ts`, the download logic,
  object-URL handling, or any script code.
- Do NOT change anything else in the two components' markup besides the `:key` attribute.
- Do NOT animate `transform`, `scale`, `filter` or size: opacity only.
- Do NOT add a Vue `<Transition>`, keyframes, a new easing token, or a reduced-motion rule.
- Do NOT touch the rail photo in `admin_dashboard/src/layouts/AppRail.vue`.
- Do NOT add dependencies.
- If the current code does not match the excerpts above (drift since commit 17e4ef5), STOP
  and report instead of improvising.

## Verification

- **Mechanical** (run in `admin_dashboard/`):
  - `npm run test:unit -- --run` → all tests pass (avatar and signature specs included).
  - `npm run type-check` → no errors.
  - `npm run lint` → no errors or warnings.
  - `npm run build` → builds.
- **Feel check**: run the API (`run.bat`) and `npm run dev`, sign in, open My profile.
  - On load, the photo and the signature fade in; neither pops in a single frame.
  - Upload a new photo, then a new signature: each new image fades in again.
  - Nothing moves or changes size during the fade; the circle and the sheet stay still.
  - In Chrome DevTools > Animations, set playback to 10% and reload: the fade starts at
    opacity 0 and rises quickly, then settles (ease-out, not linear).
  - In DevTools > Rendering, emulate `prefers-reduced-motion: reduce` and reload: the images
    appear at once (the global rule makes the fade 1ms). That is expected.
- **Done when**: both `<img>` elements have `:key="imageUrl"`, both image rules carry the
  opacity transition with `@starting-style`, all four mechanical checks pass, and the feel
  check shows a fade on load and on replace.
