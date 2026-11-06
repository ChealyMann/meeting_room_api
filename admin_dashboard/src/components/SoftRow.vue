<script setup lang="ts">
// One booking in a queue (owner pick, 6 Nov 2026: "Clean 3 · Soft rows", shared by Pitika's and
// the room owner's To review and the IT pages): a white row with the meeting time first and
// biggest, the room's photo with the reference on it, the title, one quiet line, soft tags,
// then the status and the buttons at the end. A click or Enter opens the details.
// Slots: `line` (under the title), `tags` (use <span class="soft-tag">, with `warn` or `alert`
// for amber or crimson), `status` (over the buttons) and `actions` (the buttons).
import RoomPhoto from './RoomPhoto.vue'

defineProps<{
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
}>()
const emit = defineEmits<{ open: [] }>()
</script>

<template>
  <li class="soft-row" :class="{ current }" tabindex="0" @click="emit('open')" @keydown.enter.self="emit('open')">
    <div class="soft-grid">
      <div class="time">
        <span class="start mono">{{ start }}</span>
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
      <div class="side">
        <slot name="status" />
        <div v-if="$slots.actions" class="acts" @click.stop @keydown.enter.stop><slot name="actions" /></div>
      </div>
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
  border-radius: 14px;
  background: var(--color-sheet);
  cursor: pointer;
  transition: border-color 150ms ease;
}
.soft-row + .soft-row {
  margin-top: 10px;
}
@media (hover: hover) and (pointer: fine) {
  .soft-row:hover {
    border-color: var(--color-rule-strong);
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
  grid-template-columns: 76px 148px minmax(0, 1fr) auto;
  grid-template-areas: 'time photo body side';
  align-items: center;
  gap: 20px;
  padding: 14px 18px 14px 20px;
}
.time {
  grid-area: time;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.start {
  font-size: 26px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.02em;
}
.end {
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.more,
.day {
  margin-top: 4px;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--color-intaglio);
  white-space: nowrap;
}
.photo {
  grid-area: photo;
  position: relative;
  width: 148px;
  height: 92px;
  overflow: hidden;
  border-radius: 10px;
}
.photo-fill {
  width: 100%;
  height: 100%;
}
/* The reference sits on the photo, on a small blurred tag (owner decision, 6 Nov 2026). */
.ref {
  position: absolute;
  bottom: 6px;
  left: 6px;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(20, 8, 8, 0.55);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  color: #fff;
  font-size: 11px;
  letter-spacing: 0.02em;
}
.body {
  grid-area: body;
  min-width: 0;
}
h3 {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15.5px;
  font-weight: 600;
}
.line {
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--color-intaglio);
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.tags :slotted(.soft-tag) {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  height: 24px;
  padding: 0 9px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-field-disabled);
  color: var(--color-intaglio);
  font-size: 12px;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.tags :slotted(.soft-tag.warn) {
  background: var(--color-saved-tint);
  color: var(--color-warn);
}
.tags :slotted(.soft-tag.ink) {
  color: var(--color-ink);
}
.tags :slotted(.soft-tag.alert) {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.side {
  grid-area: side;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}
.acts {
  display: flex;
  gap: 6px;
  cursor: default;
}
.acts :slotted(.btn) {
  height: 36px;
  padding: 0 15px;
  border-radius: 10px;
  font-size: 13px;
  transition:
    background-color 140ms ease,
    border-color 140ms ease,
    color 140ms ease,
    transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
/* A press that answers at once: a small scale, not a nudge. */
.acts :slotted(.btn:active) {
  transform: scale(0.97);
}
.mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* Narrow (tablet with the panel open, a phone): time and photo on top, the rest under them. */
@container (max-width: 640px) {
  .soft-grid {
    grid-template-columns: 64px minmax(0, 1fr);
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
  .side {
    align-items: flex-start;
  }
}
@media (prefers-reduced-motion: reduce) {
  .soft-row,
  .acts :slotted(.btn) {
    transition-duration: 1ms;
  }
}
</style>
