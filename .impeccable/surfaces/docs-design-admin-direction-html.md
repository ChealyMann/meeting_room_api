---
version: 1
slug: "docs-design-admin-direction-html"
primary_target: "docs/design/admin-direction.html"
related_targets: []
---

# Admin dashboard: design direction page

Scope: one static page that sets the visual direction for the Vue admin dashboard (`admin_dashboard/`), shown on its busiest screen, Rooms. Mode: Operate.

Audience and task: NBC Admin, daily, many edits. Must read as a working admin product first. Owner said "wrong" = looks like a template, or too busy. Pinned brand: NBC crimson/cream palette, Poppins + Kantumruy Pro + JetBrains Mono, Lucide icons, NBC logo, no emoji.

## Direction contract

THESIS: Every record is handled like a numbered riel banknote: precise, engraved, verified. Refuses the default admin kit of floating white cards, soft shadows and coloured pill badges.

OWN-WORLD: Deep note-crimson rail with one gold security thread on the active item; cream paper canvas; tables are open sheets ruled with engraved hairlines, no card boxes; secondary text in intaglio brown; ids, times and counts set as banknote serials in mono; one guilloche rosette, used only as the empty-state watermark. State by shape: active solid mark, inactive outlined, private a lock line.

STORY: The Admin scans rooms, filters to a place, opens "New room", fixes the two errors the API returned, saves, and sees a short "saved" message while the new row is softly tinted.

FIRST VIEWPORT: Left rail 248px (logo, grouped nav). Top bar with page path and user. Title "Rooms" with serial count, one filter row, dense table (serial, name plate EN over KH, type, place, seats, hours, owner, state), paging foot. Right: New room panel 440px over the table with two field errors, footer actions.

FORM: Riel Security Print, position 1 on the ordered list (taken as the pick); seed key dd057648.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Signature interaction

Serials: every record carries its serial (RM·0012) in mono with a crimson prefix. Saving stays quiet by the owner's choice (26 Oct 2026): no seal animation; a toast with a check icon, and a soft tint on the new row that fades out.

## Owner decisions (26 Oct 2026)

- Kept the pre-review version: soft panel shadow, single hairline rules, user in the rail foot. The reviewer's double-rule and top-bar changes were rolled back on request.
- Removed the guilloche save seal ("not clean"); the rosette stays only as the empty-state watermark.

## Unresolved

- Exact serial prefixes per resource (RM rooms, US users, ...) to be confirmed when building.
