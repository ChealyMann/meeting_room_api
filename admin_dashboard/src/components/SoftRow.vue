<script setup lang="ts">
// One booking in a queue, shared by Pitika's and the room owner's To review (and their Approved /
// Rejected tabs) and the IT pages. Look E (owner pick, 18 Nov 2026, from the "signed rows"
// demos): a time tile (calendar icon, start, a short dash, end; crimson wash when `soon`), the
// room's photo with the reference on it, the meeting (title, one room line, soft tags) and the
// buttons; under it a soft cream footer with who booked (face, name, position · department),
// the status and when it was sent. A click or Enter opens the details.
// Slots: `line` (the room line: put `.sep` spans between its parts, Lucide icons are sized),
// `tags` (<span class="soft-tag">, `warn` or `alert` for amber or crimson), `status` (in the
// footer, before "Sent") and `actions` (the buttons, top right).
import { CalendarDays, Send } from 'lucide-vue-next'
import { computed } from 'vue'

import { bookerRole, type RowBooker } from '../utils/booker'
import RoomPhoto from './RoomPhoto.vue'
import StaffAvatar from './StaffAvatar.vue'

const props = defineProps<{
  /** "14:00" and "15:30": the meeting's first session. */
  start: string
  end: string
  /** "Wed 11 Nov" under the time, or null when the group head already says the day. */
  day?: string | null
  /** "+2 more" for a booking with more sessions. */
  more?: string | null
  photo: string | null
  photoAlt: string
  reference: string
  title: string
  current?: boolean
  /** Today's meeting: the time tile takes the crimson wash. */
  soon?: boolean
  booker?: RowBooker | null
  /** "Sent yesterday, 16:20" (utils/time sentLabel). */
  sent?: string | null
}>()
const emit = defineEmits<{ open: [] }>()

const role = computed(() => (props.booker ? bookerRole(props.booker) : ''))
</script>

<template>
  <li class="soft-row" :class="{ current }" tabindex="0" @click="emit('open')" @keydown.enter.self="emit('open')">
    <div class="soft-grid" :class="{ 'no-side': !$slots.actions }">
      <div class="time" :class="{ 'is-soon': soon }">
        <CalendarDays class="cal" aria-hidden="true" />
        <span class="start mono">{{ start }}</span>
        <span class="dash" aria-hidden="true" />
        <span class="end mono">{{ end }}</span>
        <span v-if="more" class="more">{{ more }}</span>
        <span v-if="day" class="day">{{ day }}</span>
      </div>
      <div class="photo">
        <RoomPhoto class="photo-fill" :path="photo" :alt="photoAlt" />
        <span class="ref mono">{{ reference }}</span>
      </div>
      <div class="body">
        <h3>{{ title }}</h3>
        <div class="line"><slot name="line" /></div>
        <div v-if="$slots.tags" class="tags"><slot name="tags" /></div>
      </div>
      <div v-if="$slots.actions" class="side">
        <div class="acts" @click.stop @keydown.enter.stop><slot name="actions" /></div>
      </div>
    </div>
    <div v-if="booker || $slots.status || sent" class="foot">
      <template v-if="booker">
        <StaffAvatar class="face" :name="booker.name" :photo="booker.photo" :size="30" />
        <span class="booked-by">Booked by</span>
        <span class="who">{{ booker.name }}</span>
        <span v-if="role" class="role" :title="role">{{ role }}</span>
      </template>
      <span class="foot-end">
        <slot name="status" />
        <span v-if="sent" class="sent"><Send aria-hidden="true" />{{ sent }}</span>
      </span>
    </div>
  </li>
</template>

<style scoped>
.soft-row {
  /* Holds hidden text (sr-only, absolute) inside the row: without it, that text is placed against
     the page and makes the whole page scroll instead of the list. */
  position: relative;
  container-type: inline-size;
  list-style: none;
  border: 1px solid var(--color-rule);
  border-radius: 18px;
  background: var(--color-sheet);
  box-shadow:
    0 1px 2px rgba(42, 28, 19, 0.04),
    0 10px 28px -16px rgba(42, 28, 19, 0.16);
  cursor: pointer;
  transition:
    border-color 150ms ease,
    box-shadow 200ms ease;
}
.soft-row + .soft-row {
  margin-top: 12px;
}
@media (hover: hover) and (pointer: fine) {
  .soft-row:hover {
    border-color: var(--color-rule-strong);
    box-shadow:
      0 1px 2px rgba(42, 28, 19, 0.05),
      0 14px 32px -16px rgba(42, 28, 19, 0.22);
  }
}
.soft-row.current {
  border-color: var(--color-danger-line);
  background: var(--color-crimson-wash);
}
.soft-row:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
.soft-grid {
  display: grid;
  grid-template-columns: 76px 144px minmax(0, 1fr) auto;
  grid-template-areas: 'time photo body side';
  align-items: center;
  gap: 0 18px;
  padding: 16px 18px 12px 16px;
}
.soft-grid.no-side {
  grid-template-columns: 76px 144px minmax(0, 1fr);
  grid-template-areas: 'time photo body';
}

/* The time tile */
.time {
  grid-area: time;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 100px;
  padding: 10px 4px;
  border-radius: 14px;
  background: var(--color-field-disabled);
  color: var(--color-intaglio);
}
.time.is-soon {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.cal {
  width: 19px;
  height: 19px;
  margin-bottom: 5px;
}
.start {
  font-family: var(--font-sans);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--color-ink);
}
.dash {
  width: 14px;
  height: 1.5px;
  margin: 6px 0 5px;
  border-radius: 1px;
  background: var(--color-rule-strong);
}
.time.is-soon .dash {
  background: var(--color-danger-line);
}
.end {
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--color-intaglio);
}
.more,
.day {
  margin-top: 4px;
  font-size: 11px;
  font-weight: 500;
  color: var(--color-intaglio);
  white-space: nowrap;
}

.photo {
  grid-area: photo;
  position: relative;
  width: 144px;
  height: 100px;
  overflow: hidden;
  border-radius: 12px;
}
.photo-fill {
  width: 100%;
  height: 100%;
}
/* The reference sits on the photo, on a small blurred tag (owner decision, 6 Nov 2026). */
.ref {
  position: absolute;
  bottom: 7px;
  left: 7px;
  padding: 2px 7px;
  border-radius: 7px;
  background: rgba(20, 8, 8, 0.58);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  color: #fff;
  font-size: 11px;
  letter-spacing: 0.02em;
}

.body {
  grid-area: body;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding-left: 18px;
  border-left: 1px solid var(--color-rule);
}
h3 {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
/* The parts never shrink into each other: when the row is narrow, the line wraps between them. */
.line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 3px 9px;
  min-width: 0;
  margin-top: 5px;
  white-space: nowrap;
  font-size: 13.5px;
  color: var(--color-intaglio);
}
.line :slotted(.bit) {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 6px;
  max-width: 100%;
}
.line :slotted(svg),
.line :slotted(.bit svg) {
  flex: none;
  width: 15px;
  height: 15px;
  color: var(--color-ink-off);
}
.line :slotted(.sep) {
  flex: none;
  width: 1px;
  height: 14px;
  background: var(--color-rule-strong);
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 10px;
}
.tags :slotted(.soft-tag) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  height: 27px;
  padding: 0 11px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-field-disabled);
  color: var(--color-ink);
  font-size: 12.5px;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.tags :slotted(.soft-tag svg) {
  flex: none;
  width: 14px;
  height: 14px;
  color: var(--color-intaglio);
}
/* A text-only tag (a note) is a plain box, so a long one ends in "…" instead of being cut. */
.tags :slotted(.soft-tag.note) {
  display: inline-block;
  line-height: 27px;
}
.tags :slotted(.soft-tag.warn),
.tags :slotted(.soft-tag.warn svg) {
  color: var(--color-warn);
}
.tags :slotted(.soft-tag.warn) {
  background: var(--color-saved-tint);
}
.tags :slotted(.soft-tag.ink) {
  color: var(--color-ink);
}
.tags :slotted(.soft-tag.alert),
.tags :slotted(.soft-tag.alert svg) {
  color: var(--color-crimson);
}
.tags :slotted(.soft-tag.alert) {
  background: var(--color-crimson-wash);
}

.side {
  grid-area: side;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  padding-left: 18px;
  border-left: 1px solid var(--color-rule);
}
.acts {
  display: flex;
  gap: 8px;
  cursor: default;
}
.acts :slotted(.btn) {
  height: 40px;
  padding: 0 17px;
  border-radius: 11px;
  font-size: 13.5px;
  font-weight: 600;
  transition:
    background-color 140ms ease,
    border-color 140ms ease,
    color 140ms ease,
    transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.acts :slotted(.btn svg) {
  width: 16px;
  height: 16px;
  stroke-width: 2.4;
}
/* A press that answers at once: a small scale, not a nudge. */
.acts :slotted(.btn:active) {
  transform: scale(0.97);
}

/* The footer: who booked, the status, when it was sent */
.foot {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  margin: 2px 12px 12px;
  padding: 8px 14px 8px 10px;
  border-radius: 14px;
  background: var(--color-paper);
  font-size: 13px;
  color: var(--color-intaglio);
}
.face {
  box-shadow:
    0 0 0 2px var(--color-sheet),
    0 1px 5px rgba(42, 28, 19, 0.14);
}
.booked-by {
  padding-right: 12px;
  border-right: 1px solid var(--color-rule-strong);
  color: var(--color-ink-off);
  white-space: nowrap;
}
.who {
  color: var(--color-ink);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}
.role {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.foot-end {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 14px;
  margin-left: auto;
}
.sent {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--color-ink-off);
  font-size: 12.5px;
  white-space: nowrap;
}
.sent svg {
  width: 15px;
  height: 15px;
}
.mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.start.mono,
.end.mono {
  font-family: var(--font-sans);
}

/* A laptop next to the side menu: a smaller photo, so the meeting keeps its room. */
@container (max-width: 1000px) {
  .soft-grid {
    grid-template-columns: 72px 120px minmax(0, 1fr) auto;
    gap: 0 16px;
  }
  .soft-grid.no-side {
    grid-template-columns: 72px 120px minmax(0, 1fr);
  }
  .photo {
    width: 120px;
    height: 96px;
  }
  .time {
    min-height: 96px;
  }
  .body,
  .side {
    padding-left: 16px;
  }
}
/* Narrow (tablet with the panel open, a phone): time and photo on top, the rest under them. */
@container (max-width: 640px) {
  .soft-grid,
  .soft-grid.no-side {
    grid-template-columns: 76px minmax(0, 1fr);
    grid-template-areas:
      'time photo'
      'body body'
      'side side';
    gap: 12px 14px;
    padding: 14px;
  }
  .photo {
    width: 100%;
    height: 112px;
  }
  .body,
  .side {
    padding-left: 0;
    border-left: 0;
  }
  .side {
    align-items: flex-start;
  }
  .foot {
    flex-wrap: wrap;
    row-gap: 6px;
    margin: 0 10px 10px;
  }
  .role {
    flex-basis: 100%;
    order: 4;
    padding-left: 42px;
    margin-top: -4px;
  }
  .foot-end {
    flex-basis: 100%;
    order: 5;
    justify-content: space-between;
    margin-left: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .soft-row,
  .acts :slotted(.btn) {
    transition-duration: 1ms;
  }
}
</style>
