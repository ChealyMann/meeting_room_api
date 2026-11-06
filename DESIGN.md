---
name: NBC Meeting Rooms Admin
description: The National Bank of Cambodia's room-booking admin, where every record is handled like a numbered riel banknote.
colors:
  rail: "#260707"
  rail-raised: "#3A0D0D"
  rail-line: "#4A1414"
  rail-ink: "#F3E3DC"
  rail-muted: "#C9A9A0"
  thread: "#E2B33C"
  paper: "#F9F7F5"
  sheet: "#FFFFFF"
  rule: "#E9E3DD"
  rule-strong: "#D8CFC7"
  ink: "#2A1C13"
  intaglio: "#6B5243"
  ink-off: "#7A6355"
  placeholder: "#75604F"
  ink-disabled: "#8A7466"
  field-disabled: "#F3EFEA"
  off-ring: "#9C877A"
  crimson: "#991B1B"
  crimson-deep: "#7F1D1D"
  crimson-wash: "#F7ECEA"
  danger-line: "#E3C2BE"
  error-field: "#FFFBFA"
  ok: "#2F6B3F"
  warn: "#9A4A06"
  row-hover: "#FBF7F3"
  saved-tint: "#FBF1E6"
  skeleton: "#EFE8E1"
  skeleton-light: "#F7F2EC"
  scrim: "rgba(38, 7, 7, 0.045)"
typography:
  headline:
    fontFamily: "Poppins, Kantumruy Pro, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Poppins, Kantumruy Pro, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.45
  title-sm:
    fontFamily: "Poppins, Kantumruy Pro, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.45
  body:
    fontFamily: "Poppins, Kantumruy Pro, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  body-dense:
    fontFamily: "Poppins, Kantumruy Pro, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Poppins, Kantumruy Pro, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 500
    lineHeight: 1.45
  caption:
    fontFamily: "Poppins, Kantumruy Pro, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.45
  label-caps:
    fontFamily: "Poppins, Kantumruy Pro, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: "0.08em"
  khmer:
    fontFamily: "Kantumruy Pro, Poppins, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.5
  serial:
    fontFamily: "JetBrains Mono, ui-monospace, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "0.04em"
    fontFeature: "tnum"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, Consolas, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "0.02em"
    fontFeature: "tnum"
rounded:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  full: "9999px"
spacing:
  xxs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  2xl: "32px"
  3xl: "40px"
  4xl: "56px"
components:
  rail:
    backgroundColor: "{colors.rail}"
    textColor: "{colors.rail-ink}"
    width: "248px"
  nav-item:
    textColor: "{colors.rail-ink}"
    typography: "{typography.body-dense}"
    rounded: "{rounded.sm}"
    padding: "7px 10px"
  nav-item-active:
    backgroundColor: "{colors.rail-raised}"
    textColor: "{colors.rail-ink}"
    rounded: "{rounded.sm}"
    padding: "7px 10px"
  topbar:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.intaglio}"
    height: "56px"
    padding: "0 24px"
  button-primary:
    backgroundColor: "{colors.crimson}"
    textColor: "{colors.sheet}"
    typography: "{typography.body-dense}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.crimson-deep}"
    textColor: "{colors.sheet}"
  button-secondary:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.body-dense}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "36px"
  button-quiet:
    textColor: "{colors.intaglio}"
    typography: "{typography.body-dense}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "36px"
  button-quiet-hover:
    backgroundColor: "{colors.crimson-wash}"
    textColor: "{colors.crimson}"
  button-danger:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.crimson}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "36px"
  button-danger-hover:
    backgroundColor: "{colors.crimson-wash}"
    textColor: "{colors.crimson}"
  icon-button:
    textColor: "{colors.intaglio}"
    rounded: "{rounded.sm}"
    size: "32px"
  input:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "36px"
  input-error:
    backgroundColor: "{colors.error-field}"
    textColor: "{colors.ink}"
  input-disabled:
    backgroundColor: "{colors.field-disabled}"
    textColor: "{colors.ink-disabled}"
  segmented:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.intaglio}"
    rounded: "{rounded.md}"
    padding: "3px"
    height: "36px"
  segmented-active:
    backgroundColor: "{colors.crimson-wash}"
    textColor: "{colors.crimson}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
  switch:
    backgroundColor: "{colors.rule-strong}"
    rounded: "{rounded.full}"
    width: "36px"
    height: "20px"
  switch-on:
    backgroundColor: "{colors.crimson}"
  table-header:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.intaglio}"
    typography: "{typography.label-caps}"
    padding: "10px 12px"
  table-cell:
    textColor: "{colors.ink}"
    typography: "{typography.body-dense}"
    padding: "9px 12px"
  table-row-hover:
    backgroundColor: "{colors.row-hover}"
  serial:
    textColor: "{colors.intaglio}"
    typography: "{typography.serial}"
  pager-item:
    textColor: "{colors.ink}"
    typography: "{typography.serial}"
    rounded: "{rounded.sm}"
    size: "32px"
  pager-item-current:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.crimson}"
  side-panel:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    width: "440px"
  panel-foot:
    backgroundColor: "{colors.paper}"
    padding: "12px 20px"
  error-summary:
    backgroundColor: "{colors.crimson-wash}"
    textColor: "{colors.crimson}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  toast:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "10px 16px 10px 10px"
  inline-confirm:
    backgroundColor: "{colors.error-field}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "12px 14px"
---

# Design System: NBC Meeting Rooms Admin

## Overview

**Creative North Star: "The Riel Security Print"**

Every record is handled like a numbered riel banknote: precise, engraved, verified. A deep note-crimson rail holds the navigation; the work happens on cream paper where tables are open sheets ruled with engraved hairlines, not white cards floating on grey. Secondary text is printed in intaglio brown rather than grey, and every id, time, count and page number is set as a banknote serial in mono with a crimson prefix (RM·0012).

The system is dense and quiet because the Admin edits many records every day. Ornament is rationed to exactly two places: a windowed gold security thread on the active navigation item, and one guilloche rosette that appears only as a faint watermark behind an empty list. Everything else earns its place by function. Saving is deliberately unceremonious (owner decision, 26 Oct 2026): a toast with a check icon and a soft tint on the new row that fades out.

The system refuses the default admin kit of floating white cards and coloured pill badges. State is carried by shape, not by colour chips.

**Key Characteristics:**
- Crimson rail, cream paper, white sheet only where something is filled in or floats.
- Single hairline rules (1px) as the only structure; no card boxes around lists.
- Intaglio brown for every secondary line of text.
- Mono serials for ids, times, counts, pager numbers and character counters.
- Khmer name over English name, always both.
- State by shape: circle check, dashed circle, eye-off line, calendar-x line.
- Soft shadow only on things that float over the sheet (side panel, toast).

## Colors

A warm, low-saturation paper-and-ink palette under one deep crimson; gold exists only inside the rail.

### Primary
- **Note Crimson** (#991B1B): primary buttons, focus ring and focused field border, serial prefixes, field errors and the error summary, the selected segment, the current pager page, quiet-button hover, the switch when on, text selection, and the empty-state watermark (at 7% opacity).
- **Deep Note Crimson** (#7F1D1D): primary button hover and press.
- **Crimson Wash** (#F7ECEA): tinted ground for the error summary, selected segment, and quiet/icon/danger button hover.
- **Danger Line** (#E3C2BE): border of the danger button and of the inline turn-off confirm.
- **Error Field** (#FFFBFA): ground of a field carrying an API error and of the inline confirm.

### Secondary
- **Security Thread Gold** (#E2B33C): the dashed thread on the active nav item, the active item's icon, and the user initials in the rail foot. Never on the paper.

### Tertiary
- **Ledger Green** (#2F6B3F): the solid "active" state dot and the toast's check icon.
- **Lock Amber** (#9A4A06): the "Private" mark.

### Neutral
- **Note Crimson Rail** (#260707): rail background.
- **Rail Raised** (#3A0D0D): active nav item ground and the initials disc.
- **Rail Line** (#4A1414): rail right edge and the hairline above the user foot.
- **Rail Ink** (#F3E3DC) / **Rail Muted** (#C9A9A0): rail labels / nav group labels, counts, inactive icons, the email line.
- **Cream Paper** (#F9F7F5): the canvas, top bar, sticky table header, panel footer.
- **Sheet White** (#FFFFFF): inputs, buttons, side panel, toast, current pager page.
- **Engraved Hairline** (#E9E3DD): row rules, top bar rule, panel section rules.
- **Strong Hairline** (#D8CFC7): the sheet's top rule, header underline, paging foot rule, control borders, switch track off, scrollbar thumb.
- **Ink** (#2A1C13): primary text.
- **Intaglio Brown** (#6B5243): all secondary text: place lines, Khmer names, serials, hints, table headers, the page path.
- **Off Ink** (#7A6355): the "Inactive" state label and the "Not bookable" mark; the text tone for anything turned off.
- **Placeholder** (#75604F): input placeholders.
- **Disabled Ink** (#8A7466) on **Disabled Field** (#F3EFEA): disabled inputs only.
- **Off Ring** (#9C877A): the outlined ring of the "Inactive" mark.
- **Row Hover** (#FBF7F3), **Saved Tint** (#FBF1E6), **Skeleton** (#EFE8E1 to #F7F2EC): row hover, the fading new-row tint, the loading shimmer.
- **Scrim** (crimson at 4.5%): the barely-there veil behind the side panel.

### Named Rules
**The One Thread Rule.** Gold appears only inside the rail: the active item's thread and icon, and the user initials. It never reaches the paper.

**The Brown, Not Grey Rule.** Secondary text is intaglio brown (#6B5243). No neutral greys anywhere; every neutral leans warm.

**The Crimson Means Act-or-Attend Rule.** Crimson marks what the Admin can act on (primary action, focus, current page) or must attend to (errors). It is never a decorative fill.

## Typography

**Display/Body Font:** Poppins (with Kantumruy Pro for Khmer glyphs, then system-ui)
**Khmer Font:** Kantumruy Pro (with Poppins)
**Label/Mono Font:** JetBrains Mono (with ui-monospace, Consolas), tabular numerals

**Character:** A plain geometric sans for reading and acting, Kantumruy Pro matched to it for Khmer, and a mono that turns every number into a printed serial.

### Hierarchy
- **Headline** (600, 24px, 1.2, -0.01em): the page title ("Rooms"). Sits on the baseline beside its mono serial count ("057 rooms", zero-padded).
- **Title** (600, 17px): side panel heading. Empty-state heading uses 600 at 15px.
- **Title Small** (600, 13px): form group headings inside the panel.
- **Body** (400, 14px, 1.45): base text and input values.
- **Body Dense** (400, 13.5px): table cells, nav items, buttons, toast title (500).
- **Label** (500, 12.5px): field labels; the right-hand hint inside the label is 400 intaglio.
- **Caption** (400, 12px): hints, field errors, place sub-lines, toast detail, private/not-bookable marks.
- **Label Caps** (500, 11px, 0.08em, uppercase): table column headers and nav group labels only.
- **Khmer** (Kantumruy Pro 500, 14px, 1.5): the first line of a name plate, in ink; the English line under it is 12.5px intaglio.
- **Serial** (JetBrains Mono 400, 12px, 0.04em, tabular): record serials, pager numbers. Hours use mono at 12.5px; counts, seats, character counters and the clock use mono at inherited size.

### Named Rules
**The Serial Rule.** Ids, times, counts, page numbers and character counters are set in JetBrains Mono with tabular numerals. A record id is always a serial: resource prefix in crimson, a middle dot, four zero-padded digits (RM·0012). Prefixes: RM room, OF office, BL building, FL floor, RT room type, EQ equipment, CP catering package, IS IT service, DP department, DV division, PS position, US user. A booking has no serial: its reference code (NBC-26-48213) is set in mono instead.

**The Two Names Rule.** A record with both names shows Khmer (Kantumruy Pro 500, ink) directly over English (12.5px, intaglio) (owner decision, 27 Oct 2026). Never one without the other.

## Layout

The shell is a two-column grid: a 248px rail and a fluid work column. The work column stacks a 56px top bar (page path on the left, Phnom Penh clock on the right), then the page with 24px side padding: headline row, one filter row (20px above, 16px below), and the sheet, which fills the remaining height and scrolls internally while its header stays sticky and the paging foot stays pinned.

Spacing snaps to an 8px module with a 4px half-step (4, 8, 12, 16, 20, 24, 32, 40, 56). Control internals tighten off-module for density (nav item 7px/10px, cell 9px/12px, button 14px side padding); those are component values, not new steps.

The side panel is 440px, anchored to the right edge under the top bar, over a faint scrim; the table stays visible beside it. Panel body: 16px/20px padding, groups 20px apart, fields 12px apart, two- and three-up field rows on a 12px gap.

The real app is a full-height shell (100vh, min 640px). The 960px max-height on the direction page exists only so the "States and parts" section can follow it; it is not a system rule.

**Responsive:**
- **At or below 1100px:** the rail collapses to 64px icons only (brand text, group labels, nav labels, counts and the user's name hide; the sign-out icon stays, under the initials); the Type and Owner columns hide.
- **At or below 760px:** the rail hides; page and top bar padding drop to 16px; the side panel goes full width; the Serial and Hours columns hide; three-up field rows stack.

### Named Rules
**The Open Sheet Rule.** Lists sit directly on the paper, opened by a strong hairline and ruled by engraved hairlines between rows. No card, no box, no rounded container around a table.

## Elevation & Depth

Flat by default; depth comes from hairlines and the paper/sheet tone step. Shadows appear only on surfaces that float above the sheet. The owner kept the soft panel shadow and single hairline rules (26 Oct 2026).

### Shadow Vocabulary
- **Panel** (`box-shadow: -18px 0 40px rgba(42, 28, 19, 0.12), -2px 0 6px rgba(42, 28, 19, 0.06)`): the right side panel, cast leftward over the table.
- **Toast** (`box-shadow: 0 8px 20px rgba(42, 28, 19, 0.13), 0 1px 3px rgba(42, 28, 19, 0.10)`): the floating saved toast. An inline toast (inside a layout) drops the shadow and takes a hairline border.
- **Switch thumb** (`box-shadow: 0 1px 2px rgba(42, 28, 19, 0.25)`): the switch knob only.
- **Focus halo** (`box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.12)`): focused inputs.

### Named Rules
**The Overlay-Only Shadow Rule.** If it does not float over the sheet, it has no shadow. Tables, filters, headers and buttons are flat.

## Shapes

Gently softened, never pill-shaped except where the form is a switch or avatar. Buttons, inputs, the segmented control, the error summary and the inline confirm share an 8px corner; nav items, icon buttons, pager buttons and segment chips use 6px; the toast 10px; skeleton bars and the focus ring 4px; the switch track and initials disc are full rounds. All borders are 1px; the only thicker strokes are the 2px focus outline and the 1.5px inactive ring. Icons are Lucide strokes at 16px, stroke 1.75 (12px in table headers, 13px in marks, 14px in field errors, 20px in the toast).

## Components

### Rail and Navigation
Crimson, quiet, one point of gold.
- **Rail:** #260707 ground, 1px rail-line right edge. Brand block (36px logo, "Meeting Rooms" 600 14px over "Admin" 12px muted) at 20px padding. User foot at the bottom: 32px initials disc (rail-raised, gold initials), name 500 13px, email 12px muted, sign-out icon button; separated by a rail-line hairline.
- **Group labels:** label-caps in rail-muted, 16px above, 4px below.
- **Order (owner decision, 4 Nov 2026, "daily first, setup folds"):** "Daily" first (Bookings, Food list, Rooms), then a "Setup" label over four groups that fold: Places, Catalog, Organisation, People. A group header is a row like a link (its icon, name, a mono count of its links, a 14px chevron); an open group's links sit under it, indented on a 1px rail-line. The group holding the current page opens by itself; the others stay as the Admin left them. The folded (icon-only) rail (owner decision, 4 Nov 2026, option A) shows the three daily links, a 1px rail-line, then one icon per setup group; the icon of the group holding the current page carries the raised ground, gold icon and security thread. Clicking a group icon pops its links out in a white pointer card beside it (owner decision, 4 Nov 2026: sheet ground, rule border, 12px corners, soft shadow, a small turned-square pointer level with the group icon; a head row with the group icon on a crimson-wash tile, the group name 14px 600 and a mono count; each link with its 16px intaglio icon; the current page on crimson wash in crimson, no dot); a pick, the same icon, Escape or a click outside closes it.
- **Nav item:** 13.5px rail-ink, muted 16px icon, optional mono count right-aligned in muted. Hover: white at 5%. 
- **Active item:** rail-raised ground, gold icon, and the **security thread**: a 1px vertical line at the item's left edge, inset 6px top and bottom, drawn as gold dashes (5px gold, 3px gap). Mark with `aria-current="page"`.
- **Collapsed (1100px):** 64px, icons centred at 9px padding.

- **Roles (owner decision, 5 Nov 2026):** the menu follows the user's roles. An Admin sees the menu above. A Pitika sees only Daily: To review (with a crimson count of bookings waiting), Bookings (their province's, read only, no province filter) and Food list; the rail's subtitle reads "Pitika". Someone with both roles sees both, To review first. Every page lists the roles that may open it; a page for other roles sends the user to their home (Rooms for an Admin, To review for a Pitika), and a user with neither role sees "No access".

### Top Bar
56px, paper ground, engraved hairline beneath, 24px side padding. Left: page path in 13px intaglio with a chevron, current page in ink 500. Right: mono clock "Phnom Penh 14:32" in 12px intaglio with a clock icon (API time is UTC; people read Cambodia time). The user lives in the rail foot, not the top bar.

### Buttons
- **Shape:** 36px tall, 8px corner, 14px side padding, 8px icon gap, 13.5px 500.
- **Primary:** crimson ground and border, white text and icon; hover deep crimson. One per view region (page head, panel foot).
- **Secondary:** sheet ground, strong-hairline border, ink text; hover darkens the border to intaglio.
- **Quiet:** transparent, intaglio text; hover crimson wash with crimson text. Used for Cancel, Keep on, More filters.
- **Danger:** sheet ground, danger-line border, crimson text, power icon; hover crimson wash with crimson border. Never used for delete.
- **Disabled:** 45% opacity, not-allowed cursor, no press motion.
- **Busy:** pointer events off, label changes to the verb in progress ("Saving", "Creating") with a 14px spinner (1.5px ring, white on the primary).
- **Press:** 1px downward nudge (120ms).
- **Icon button:** 32px square, 6px corner, intaglio icon; hover crimson wash and crimson icon.

### Inputs / Fields
- **Field:** label (12.5px 500) over control, 6px gap; optional hint right-aligned inside the label row (counter in mono "16/100", or "optional", "shown only on request").
- **Input / select / textarea:** 36px tall (textarea min 72px, 8px/10px padding, vertical resize), sheet ground, strong-hairline border, 8px corner, 10px padding. Select uses a drawn Lucide chevron at 10px from the right. Leading icon variant pads to 34px; unit suffix variant (m²) pads right to 40px.
- **Hover:** border to intaglio. **Focus:** crimson border plus 3px crimson halo at 12%.
- **Error:** crimson border, error-field ground, and below it a 12px crimson message with a 14px alert icon, wired by `aria-describedby`. Messages are the API's own words.
- **Disabled:** disabled-field ground, disabled ink, engraved-hairline border.
- **Numbers, times, codes** in fields use mono. Door codes are a password field.

### Segmented Control
36px, sheet ground, strong-hairline border, 8px corner, 3px inset. Segments are 13px intaglio buttons with `aria-pressed`; the pressed segment takes crimson wash, crimson text, 500 weight, 6px corner.

### Switch
36 x 20px track (strong hairline off, crimson on), 16px white thumb with the thumb shadow, travels 16px. Label sits left with an optional 12px intaglio explanation beneath; `role="switch"`.

**The Active switch.** Every record panel (rooms, places, catalog, organisation, users) starts its foot with a switch named "Active", apart from the buttons at the end, with the state beside it in 13px 500: "Active" in ink, "Inactive" in intaglio (owner decision, 27 Oct 2026: replaces the "Turn off" / "Turn on" buttons, so the panel uses the same words as the list's State column). Flipping it off asks first ("Make Head Office inactive?", button "Make inactive"); flipping it on does not ask. The switch moves only after the API answers; while it waits it is at half strength. A refusal shows in a bubble above it. The toast says "Head Office is now inactive" (or "now active").

### Table
- **Header:** sticky, paper ground, label-caps intaglio, 10px/12px padding, strong-hairline underline. Sortable headers are bare buttons with a 12px arrow.
- **Rows:** 13.5px, 9px/12px padding, engraved hairline between rows, vertical middle. Hover: row-hover tint (120ms).
- **Serial column:** serial typography, intaglio, crimson resource prefix.
- **Name plate:** Khmer (Kantumruy Pro 500, ink) over English 12.5px intaglio.
- **Place:** office 400 over the "Building · Floor" line in 12px intaglio.
- **Numbers** right-aligned in mono; **hours** in mono 12.5px as "08:00–17:00".
- **No owner:** the words "No owner", in the off tone.
- **State cell:** a column of marks, 3px apart. Active: 16px `CircleCheck` line in ledger green plus "Active". Inactive: 16px `CircleDashed` line in off-ring plus "Inactive" in off ink (owner decision, 27 Oct 2026: icons, not a dot and ring). Private: 13px eye-off line (owner decision, 27 Oct 2026: not a lock) plus "Private" in lock amber. Not bookable: 13px calendar-x line plus "Not bookable" in off ink.
- **Inactive row:** all cells except state and actions drop to the off tone.
- **Row actions:** a 48px column holding one ellipsis icon button.

### Paging Foot
Strong hairline above, 12px/16px padding, 13px intaglio. Left: mono range "1–20 of 57" and a "Rows" select (32px tall). Right: pager of 32px mono buttons, 6px corner, transparent until hover (strong hairline). Current page: crimson border and text on sheet. Disabled arrows fade and keep a not-allowed cursor.

### Side Panel
440px, sheet ground, panel shadow, engraved hairline on its left edge, over the scrim; full window height, covering the top bar (owner decision, 27 Oct 2026). Head: the 17px title, then one intaglio line with the second name and the mono serial ("Head Office · OF·0003"; just "RM·new" for a new record), close icon button at the top right; hairline below. Body scrolls; groups are titled (13px 600) and separated by engraved hairlines. Foot: paper ground, hairline above, actions right-aligned (quiet Cancel, primary verb). Escape and the scrim close it. Opening moves focus to the first field that needs attention. A saved record opens only after it has loaded, so the panel slides in once with its content: the clicked row shows a small spinner if loading takes over 150ms, and a failure is said above the list with "Try again" and "Close" (owner decision, 27 Oct 2026).

### Error Summary
At the top of the panel body, `role="alert"`: crimson wash, 8px corner, 10px/12px padding, alert icon, crimson bold count ("2 fields need attention.") followed by ink instruction ("Fix them and save again.").

### Toast
`role="status"`, bottom-right 24px, sheet ground, 10px corner, toast shadow, 12px gap. A 20px ledger-green circle-check icon, then the title (13.5px 500, "Mekong Room saved") over a mono intaglio detail line with the serial and place path ("RM·0058 · Head Office › Building A › 3rd floor"). Dismisses after about 4 seconds.

### Saved Row
The newly saved row enters at the top of the table with the saved tint, which fades to transparent over 2.4s ease-out. This and the toast are the entire save feedback.

### Empty State
Centred under the table head, 40px top and 36px bottom padding, an engraved hairline below. On top, a seal (owner decision, 30 Oct 2026; replaces the rosette watermark): a 72px dashed off-ring circle around a 54px crimson-wash disc holding a 24px crimson icon (1.75 stroke), like the Confirm Dialog's circle. The icon is the page's own menu icon ("No rooms yet" shows the open door), or Inbox on a page without one; when filters hide every record it is SearchX, so "nothing here yet" and "nothing matches" never look the same. The seal is hidden from assistive tech. Heading 15px 600, a 13px intaglio sentence that names the actual filters (max 40ch), then actions: secondary "Clear filters" and primary create.

### Loading Skeleton
Rows that match the table's column grid, 14px vertical padding, engraved hairline between. Bars are 10px tall (22px for the name plate column), 4px corner, a skeleton-to-light shimmer over 1.4s. Hidden from assistive tech.

### Confirm Dialog
Making something inactive or deleting it is confirmed in a SweetAlert-style dialog (owner decision, 27 Oct 2026; replaces the inline confirm): a centred 400px sheet card with 14px corners and a deep shadow over a dark crimson veil (rgba(23, 4, 4, 0.45)); a 72px crimson-wash circle with a 2px danger-line ring holding a 32px crimson icon (Power for turn off, Trash for delete or remove, a warning triangle otherwise); the question in 20px 600 ink, centred; one line of consequence in 14px intaglio; then two 42px buttons, secondary "Cancel" and primary (filled crimson) action. It pops in (opacity 180ms, scale 0.94 → 1 over 260ms ease-out-quint), takes focus on Cancel, keeps Tab inside, closes on Escape or a click outside, and gives focus back to the button that opened it. `role="alertdialog"`, `aria-modal="true"`. One dialog serves the whole app.

### Sign-in Frame
The pages outside the shell (sign-in, new password, no access) are the one place with a scene (owner decisions, 27 Oct 2026). They show one card in the middle of the paper (owner decision, 30 Oct 2026; replaces the two-panel layout): a 420px sheet card with a hairline border, 16px corners and a soft shadow. In it, centred: the NBC logo at 56px on its own (no filled disc behind it), the title at 26px with an intaglio subtitle, then the form (46px inputs and button, the primary button casting a soft crimson shadow), and one centred footer under a hairline: "National Bank of Cambodia" and "Authorised NBC personnel only". Behind the card, the Bakong temple fills the window as a diamond halftone at 16% opacity, 5px cells, fading in along a wavy left edge. At or below 680px the card moves near the top, loses its shadow and takes less padding; the temple stays behind it. "Forgot password?" opens a note (there is no self-service reset). These pages carry no status pills, clocks, version labels or badges.

### Night Theme
A sun/moon button at the right of the top bar switches day and night. The app always starts in day; night is used only after the user picks it, and the choice is kept in that browser (owner decision, 27 Oct 2026). Night is "midnight slate" (owner decision, 27 Oct 2026, replacing warm brown-black): it swaps the colour tokens on `<html data-theme="dark">` to paper #0E1217, sheet #151B22, rules #222A33 / #364250, ink #E6EBF1, intaglio #9BA7B5, off ink #8693A2, placeholder #8A96A5, row hover #19212A. Crimson splits in two: crimson text, focus and error colour is #F2766D (6.8:1 on paper), and a separate fill token, crimson-fill, carries white text (by day #991B1B, at night #B3332B, 6.1:1) on the primary button and the switch. The rail keeps the bank's crimson (#230808, raised #3A0F0F), so the brand stands out against the cool grey. The signature sheet stays white in both themes, because a signature is black ink on a transparent ground. The sign-in temple is drawn on the theme's paper with the halftone token: ink by day, crimson #F2766D at night (owner decision, 27 Oct 2026).

### Folding the Sidebar
On screens wider than 1100px, a menu button (three lines, the same icon as the phone Menu button) at the left of the top bar folds the rail to the 64px icons-only rail and opens it again; the choice is kept in that browser. From 761px to 1100px the rail is always folded and the button is hidden; at or below 760px the rail is the drawer opened by the Menu button.

### Room Panel
A room opens in the side panel: Khmer name over English in the head, the serial at the end of the English line, then three tabs (Details, Photos n/20, Equipment n) underlined in crimson when selected. Details is a two-column list (label in intaglio, value in ink). The door code row shows five masked dots (•••••, mono, off-ring color) and a round 36px eye button ("Show door code"); only after the click is the code fetched, then it shows in mono 18px on the same line, with a round copy button (a check after copying) and a crimson round eye-off button to hide it again. One line and one height in every state, nothing wraps (owner decision, 4 Nov 2026). Photos are a two-column grid of 4:3 thumbnails with a small caption ("Cover" in crimson for the first) and icon buttons to move earlier/later and delete; dragging also reorders. Equipment is a two-column checklist; an item that is off shows "(off)" in off ink. The fourth tab, Schedule, lists one week of the room's bookings by day ("Thu 5 Nov 2026"): mono times, the title as a link to the booking, the reference and booker in intaglio, the status at the end; a private session the viewer may not see reads "Reserved (Private Session)" in off ink after a small lock, with no link. After creating a room, a quiet step line on paper ("Step 2 of 3 · Photos" → "Step 3 of 3 · Equipment") leads with "Next: equipment" and "Done".

### Record Panels
Offices, buildings, floors, room types, equipment, departments, divisions and positions open in the same side panel as a room's form, with no tabs: Khmer name over English in the head (a floor shows its label, with "building · office" below), the serial at the end of that line, then grouped fields ("Names", "Where", "Floor", "About"). Moving a building or floor is just choosing another parent; the field's hint says "Change to move the building" (or floor). The foot holds the Active switch at the start, apart from "Cancel" and the primary button at the end. Making a record inactive asks in the Confirm Dialog and names what it costs: "12 rooms in this office stop being bookable. You can make it active again." ("1 room … stops", "No rooms are affected." when there are none, and "Its rooms stop being bookable." when the count cannot be read). A refusal (for example "Turn on its office first.") shows as an error summary just above the switch. Making a room type or an item inactive changes no room's bookability, so it says what it does keep: "12 rooms use this room type and keep it. It cannot be chosen for other rooms." and "12 rooms have this item and keep it. It cannot be added to other rooms." While the form has unsaved changes, the switch refuses with "Save or cancel your changes first." Equipment has one name (no Khmer name), so its head shows the name over the serial. Making a department, division or position inactive changes nobody either, so the warning counts active users: "12 users work in this department and stay in it. Its divisions stay active, but no new division can be added to it.", "12 users work in this division and stay in it. No new user can join it.", "12 users have this position and keep it. No new user can get it." Moving a department says what follows it, with the Office hint "Change to move the department" and a help line under the select: "Its users' province changes with it." (a division's: "Its users' province follows the new department's office.") A department select is grouped by office (one optgroup per office, "(off)" after an office that is off), because the same department name exists in many offices.

### User Panel
A user opens in the side panel like a room: their round 42px photo leads the head (paper ground, hairline ring; their initials in crimson when there is no photo), then the Khmer name over "Ms. Sok Dara · US·0007" (title before the English name), then four tabs (Details, Roles, Password, Signature) underlined in crimson. The panel stays open after a save. Details holds the grouped form (Name, Contact, Work); its foot has "Cancel" (which undoes the changes) and "Save changes". Roles is a checklist of the six roles in a fixed order (Admin, Room owner, Staff, Pitika, IT Lead, IT Staff), each English over its Khmer name with a hairline between; Pitika, IT Lead and IT Staff carry the intaglio note "Needs a division". Ticking one of them for a user with no division shows the crimson line "Pitika, IT Lead and IT Staff need a division. Choose one on the Details tab first." and keeps "Save roles" off. Password has the password field with "Generate" and "Copy", and "Set temporary password", which asks first ("Set a temporary password for Sok Dara?", "They are signed out everywhere and must choose a new password when they next sign in.", "Set password"). Signature is the same field as on My profile. Making a user inactive says "They cannot sign in, their bookings that have not ended are cancelled, and 2 rooms lose their owner. You can make them active again." ("They cannot sign in, and their bookings that have not ended are cancelled." when they own no room). After making them inactive or removing Room owner, a paper notice above the tabs says "These rooms have no owner now:" with each room's serial as a crimson link to its panel; a second notice says "These bookings were cancelled:" with each booking (#12) as a crimson link to its panel on Bookings.

**Locked actions.** An action the signed-in user may never take on their own record stays one line: the Active switch keeps its place at half strength (no lock icon: owner decision, 27 Oct 2026), names the reason on hover, and a click shows "You cannot make yourself inactive." in the same bubble as other refusals instead of changing (owner decision, 27 Oct 2026: a reason squeezed beside the control wrapped into four lines). It stays focusable (`aria-disabled`) and carries the reason for screen readers. The Admin box is disabled with "You cannot remove your own Admin role." under it.

**Roles in the user list** are plain text, never pills (owner decision, 27 Oct 2026): one role per line like the Work column, at most two, and "+2" in mono intaglio after the second, naming the rest on hover. "No roles" in off ink.

### Booking Panel
A booking opens read only in the side panel: the meeting title in the head, then the status in words and the mono reference code ("Confirmed · NBC-26-48213"), then four tabs (Details, Sessions n, Services, History). There is no form. The foot shows only the actions the API allows now: "Cancel booking" (quiet, crimson text), "Reject" and "Approve" (primary), grouped at the end; "Close" and "Calendar file" are grouped at the start. When both groups do not fit on one row, the decisions take their own row above (owner report, 5 Nov 2026: five buttons in one row pushed out of the 440px panel). Each action asks in a pop-up (owner decisions, 5 Nov 2026: a pop-up instead of a step inside the panel; the "Ledger" style, option B of five, with rounded corners): a 480px sheet card, 14px corners, over the dark veil, with no rule on top (owner decision, 5 Nov 2026). The head is left aligned: a 56px tile with 12px corners holding a 28px icon (calendar-x for cancel and circle-x for reject in crimson on crimson wash; circle-check for approve in ledger green on a green wash), beside the question in 19px 600, "You act for Pitika." or "You act for the room owner." in crimson when the Admin stands in, and one intaglio line on what happens next. Under it, the booking as a small two-column table on hairlines: Meeting, Reference (mono, "NBC" in crimson), When ("Fri 6 Nov 2026 · 14:00–15:30 +2 more"). Then the optional reason or notes box (focused on open) with a mono counter, and a paper foot under a hairline with "Back" and the filled confirm button at the end. A refusal shows under the box on crimson wash, and the confirm button turns off when the action is no longer allowed. Escape and a click outside close only the pop-up, never while it is sending. History (owner decisions, 5 Nov 2026) has two parts. On top, a process bar on a paper box with 10px corners: the route's steps as 28px circles joined by a 2px line (Sent, then Pitika, Room owner on route R2, IT setup when IT help was asked, Confirmed, and Ended once the meeting is over); a done step is filled ledger green with a check, the step that stopped a rejected booking is filled crimson with an x, the current step is a dashed amber ring with a clock, and steps not reached are empty rings. A cancelled booking keeps only the steps it reached and ends with a crimson "Cancelled". Under it, a timeline, oldest first: a 32px circle per step on a 1px line, its icon and colour telling the action (envelope for Sent; circle-check green for Approved and IT ready; calendar-check green for "Confirmed · door pass ready"; circle-x crimson for Rejected; hourglass crimson for Expired; calendar-x crimson for Cancelled; monitor for Sent to IT; users for Staff assigned; circle-minus for "Pitika not needed"; flag for Meeting ended; a dashed amber clock for "Waiting for …"). Each row: the action in 600 and its colour with the mono Phnom Penh time at the right, then who acted and their role as plain intaglio text with a 13px icon, no pill (owner decision: badges looked cluttered): "Chan Sophea · Pitika". Role icons (owner pick): Booker user, Pitika clipboard-check, Room owner door-open, IT Lead wrench, System refresh arrows, Admin user-cog. The Admin's role is crimson, and a stand-in names the role taken: "Mann Chealy · Admin for Room owner". A note or reason sits under the row on paper with 8px corners. The API does not record which IT Lead acted, so those rows show only the role; a booking the system confirmed because IT was not ready in time has no Confirmed row (no time is recorded), only the done step in the bar. Status words: Waiting for Pitika, Waiting for owner, IT setup, Confirmed, Completed, Rejected, Cancelled. Details holds the room (a link to its panel), route, meeting type, purpose, attendees and the booker as copied when sent. The door pass follows the door code rule and uses the same masked-dots row: for a confirmed booking, the eye fetches it, and the code shows in mono with a small crimson-outlined "Expired" tag beside it when it has passed (the end time is on the Sessions tab). "Calendar file" downloads the .ics. The Bookings list and the Food list are plain sheets like the other lists; the Food list has no paging and moves by day ("Previous day", "Today", "Next day", a date field).

### Review Queue
The Pitika's To review page (owner decisions, 5 Nov 2026; spec `docs/superpowers/specs/2026-11-05-pitika-review-design.md`). Under the title, one short line: "Bookings in your province waiting for your decision." The filter row: search, a room picker (only the Pitika's province, always with its own search box), From and To date pickers, and "Clear filters" while any is set; all kept in the address. Every booking waiting for Pitika in their province, on one sheet, grouped by urgency under sticky heads (11px 600 caps with a mono count): **Today** in crimson with a 2px crimson underline and "Decide before they start, or they expire" at the right, then **Tomorrow**, **This week**, **Later**; empty groups are left out. A row: the room's cover photo (168px, 16:10, 8px corners; a paper tile with a door when the room has none), the mono reference ("NBC" crimson), the title in 15px 600, Khmer · English room, the first session's day and mono times (+n more), the booker and the attendees; under them, "what to check" labels on paper with a hairline and 6px corners: the food packages × servings, the IT items, a crimson "Private · reason given" (or "no reason") on a private room, "Food and IT only" when the owner books their own room. At the right: for Today only a crimson pill "Starts in 4 h 40 min" (or "Started"), the row bar, then Reject (danger) and Approve (primary). **The row bar ("gap is you", owner pick):** Sent done, then a dashed amber line into the first step after Pitika, with no Pitika circle: the decision waiting; then Room owner, IT setup, Confirmed as they apply. A click (or Enter) opens the side panel: the room photo at the top of the body (188px, Khmer over "English · office" on a dark gradient), the full process bar on paper with Pitika as the current step, amber notes when it starts today or when only food and IT are checked, then Meeting, Food and IT help; the foot holds Close, Reject and Approve. Both decisions ask in the Ledger pop-up: Approve says what comes next ("It goes to IT setup next. The food is approved with it.") with optional notes; Reject needs a reason of at least 5 characters (the button stays off, "At least 5 characters." under the box). After a decision the row leaves and a toast names it. Nothing waiting: "Nothing to review" / "New bookings in your province show here.".

### IT Pages
IT setup (IT Lead) and My tasks (IT Staff) show the same setups two ways (owner decision, 6 Nov 2026, demos C and E of five, picked over the earlier busy row): a **Rows / Cards** switch (the segmented control with a Rows3 and a LayoutGrid icon) at the end of the filter row (on My tasks, beside the title), kept in that browser.
- **Rows ("Day timeline"):** under the same day groups, each setup sits on a time line: at the left the setup time in 15px mono 500 with "Set up by" above it and the day ("Today", "Sun 8 Nov") under it; then a 20px dot on a 1px rule-strong line (dashed amber: needs staff; ledger green with a check: has staff or is ready; crimson with an x: missed); then the setup on a sheet slip (hairline border, 10px corners): the room's 104px photo, the title with the mono reference, "Khmer · English · place · meeting 09:00–10:30" on one line, the IT items with an icon picked from the name (projector, mic, speaker, video, laptop, wifi, cable, printer; a monitor otherwise) and the booker's note cut to one line, then the staff's faces (photo, else initials on crimson wash) with their names, "Starts in …" or "Missed · not marked ready" in crimson, and the buttons. These slips are an exception to the Open Sheet Rule, by the owner's pick.
- **Cards ("Photo cards"):** cards of at least 300px, as many as fit: the 168px room photo with "Today · by 23:00" on a dark tile at its top left and the crimson "Starts in …" or "Missed" at its top right (a card due today has a 3px crimson top edge), then the mono reference, the title, Khmer · English room, the place, the meeting time, and the needs as 28px icon squares (named on hover and for screen readers; the note square in crimson). A paper foot holds the staff's faces (only "No staff yet" in words; with buttons beside them the names are read out and shown on hover) and the buttons ("Change", "Mark ready").
- **Assign pop-up ("Avatar list", demo 1 of five):** the Ledger pop-up with a user-plus tile, "Assign IT Staff" and "They see it in My tasks."; in place of the table, a paper box with the room's 56px photo, the title, "Room · Fri 6 Nov · set up by 08:30" and the needs with icons. Then a search box and the IT Staff as rows: a 36px face, English over Khmer, how many other setups they have that day ("Free that day" in green, "2 other setups that day"), and a checkbox; a checked row is crimson wash. On a phone the "other setups" line goes under the names. The note box is hidden behind "+ Add a note for staff" until asked, and open at once when the setup has a note. The foot says "2 picked" at the start, then Back and "Assign 2 staff".

### Roles Page
The six roles in one table with no filters, paging or "New" button: the code in mono, Khmer over English, the count of active users in mono ("–" until it loads) and "Needs a division" in intaglio for Pitika, IT Lead and IT Staff. A role's panel has only the two names, under the note "The code and the rules of a role never change."

### Icon Picker
An equipment item's icon is a Lucide name chosen from a fixed list of 50 meeting-room icons. The picker shows a preview first (a 56px paper square holding the icon at 32px, then its label and the stored name in mono; a dashed empty square for "No icon"; a `CircleHelp` in off ink with "Unknown icon" and the stored text for a name not on the list, which is kept unless changed), then a search box with a "No icon" button, then a grid of 40px icon buttons (hairline border, crimson border and wash when chosen) that scrolls after four rows. The grid is one radio group: one tab stop, arrow keys and Home/End move and choose. No match says "No icons match.". In the list the icon is 20px in its own column after the serial.

### Search Picker
Every dropdown in the dashboard is a search picker, never a browser list (owner decision, 27 Oct 2026): filters, form fields and the rows-per-page box. A list longer than five items gets the search box; a shorter one opens as a plain list (arrow keys, Enter and Space still work). In a form the picker is full width, shows its prompt greyed ("Choose an office"), takes the field's red border and error text, has no ×, and offers the empty choice only for an optional field ("No owner"); a child picker is greyed until its parent is chosen (Building until Office). The list is fixed to the window, so a panel's scroll area never cuts it, and opens upward when there is no room below (the owner field, the rows box). Filter pickers are 184px; Building, Floor and Type on Rooms are 136px so the first filter row fits at 1366px. The main filter of a list page is a search picker too: the office filter on Rooms, Buildings, Floors and Departments, the province filter on Offices, and the department filter on Divisions (with each office as a small uppercase heading over its departments). It is a 184px button in the filter box style (owner decision, 27 Oct 2026), not a browser list: the name fills it ("All offices" or the chosen office, ending in "…" with the full name on hover) and the arrow, or × to clear once one is chosen, sits 10px from the right edge like the other selects. It opens a 300px sheet card: a search box ("Search offices", "Search provinces", "Search departments"; matching the English name, the Khmer name, and the province or office, the match set in bold), then one line per office with a crimson tick and crimson name for the chosen one; "All offices" first, main offices next, a hairline, then the branches. Offices that are off are hidden unless chosen ("(off)"); an unknown chosen id reads "Unknown office". Arrow keys, Home/End, Enter and Escape work; a click outside closes it. On a phone it opens from the bottom over the scrim.

### Time Picker
Times (a room's opening and closing) use the dashboard's own picker, never the browser's time box (owner decision, 30 Oct 2026). The field is an input-styled button with the time in mono, 24-hour "08:00", and a `Clock` icon at the right; open, it takes the crimson border. The pop-up is placed like the Search Picker (fixed to the window, above the field when there is no room below, a bottom sheet on phones) and holds two columns, "Hour" 00–23 and "Min" in 5-minute steps (a minute already set off the steps is kept), each 224px tall with the themed scrollbar. The chosen value has the crimson wash and crimson mono text. Clicking an hour moves to the minutes; clicking a minute sets it and closes. Keyboard: arrows move, Left/Right switch columns, Enter picks, Escape closes (and leaves the side panel open).

Dates use the dashboard's own picker too, never the browser's date box (owner decision, 5 Nov 2026): the Bookings From/To filters, the Food list day and a holiday's date. The field is an input-styled button showing the day in words ("Thu 5 Nov 2026") or a greyed placeholder ("Any day" on a filter, "Choose a day" otherwise), with a `CalendarDays` icon at the right; open, it takes the crimson border. The 292px pop-up is placed like the Time Picker (fixed to the window, above the field when there is no room below, a bottom sheet on phones): the month name in 600 with previous and next month icon buttons, then six weeks, Monday first, in mono. Today has a 1.5px crimson ring and crimson text; the chosen day is filled crimson with white text; days of the next and last month are faded; days outside the allowed range are struck through and cannot be picked (a filter's To cannot be before its From). Under a hairline: "Clear" at the left on a filter, and "Today" at the right, both crimson text. Keyboard: arrows move a day or a week, Page Up/Down a month (31 Jan becomes 28 Feb), Home/End the start or end of the week, Enter picks, Escape closes (and leaves the side panel open).

### Scrollbars
Every scroll area uses the theme scrollbar: a slim pill in rule-strong with transparent track and no arrow buttons, intaglio on hover (Chrome, Edge and Safari); Firefox gets its thin scrollbar in the same colour.

### Motion
Ease-out-quint (`cubic-bezier(0.23, 1, 0.32, 1)`) for things that travel (toast 260ms, switch thumb 180ms); the drawer curve (`cubic-bezier(0.32, 0.72, 0, 1)`) for the sidebar fold (240ms) and the side panel (opens in 340ms, closes in 240ms, its scrim fading at the same pace; a panel that replaces another one starts where the old one was, and a panel the page removes still slides out); plain `ease` for colour (120 to 200ms). Under `prefers-reduced-motion: reduce`, all animation and transition durations collapse to 1ms.

**Page change.** A new page fades in over 160ms (ease-out), and nothing moves (owner decision, 28 Oct 2026). The rail and top bar stay still. It plays only when a page appears: opening a panel keeps the same page, so nothing fades then. It uses no fill mode, so after the fade nothing remains that could trap pop-ups under the top bar. It is off when the person asks for reduced motion.

### Accessibility
- Global focus: 2px crimson outline, 2px offset, 4px corner. Inputs replace it with the crimson border and halo.
- Contrast on paper and sheet: ink 15.4:1, intaglio 6.8:1, crimson 8.3:1, off ink 5.6:1, lock amber 6.3:1, ledger green 6.4:1. In the rail: rail-ink 13.5:1 and gold 8.6:1 on the active ground, rail-muted 8.7:1.
- State never relies on colour alone: each mark has a distinct shape and a word.
- Field errors are tied to inputs with `aria-describedby`; the summary is an alert; the toast is a status.

## Do's and Don'ts

### Do:
- **Do** set every record id as a serial: crimson prefix, middle dot, four zero-padded mono digits (RM·0012).
- **Do** show Khmer over English for every bilingual record.
- **Do** carry state by shape and word: circle check Active, dashed circle Inactive, eye-off line Private, calendar-x Not bookable.
- **Do** keep tables as open sheets on the paper, ruled by 1px hairlines.
- **Do** confirm turning something off or deleting it in the confirm dialog (SweetAlert style), focus starting on Cancel.
- **Do** show the API's own error text under the field it belongs to, plus a count summary at the top of the panel.
- **Do** confirm a save with the toast and a fading row tint, nothing more.
- **Do** keep the user in the rail foot and the clock in the top bar.

### Don't:
- **Don't** animate a seal, stamp or rosette on save; the guilloche rosette is only the empty-state watermark (owner decision, 26 Oct 2026).
- **Don't** use badges, pills or coloured chips for state.
- **Don't** put card boxes, rounded containers or shadows around tables, filters or lists.
- **Don't** add ornament anywhere except the security thread on the active nav item and the empty-state watermark.
- **Don't** use gold outside the rail.
- **Don't** use double rules or heavier frames; rules are single 1px hairlines (owner decision, 26 Oct 2026).
- **Don't** use neutral greys for secondary text; use intaglio brown.
- **Don't** use emoji; icons are Lucide strokes.
