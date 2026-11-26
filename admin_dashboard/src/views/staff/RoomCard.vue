<script setup lang="ts">
// One room on Find a room (look A "Clean", owner pick 20 Nov 2026): the photo, the names, the
// facts with icons, the description on one line, then a foot with the live line ("Free until
// 14:00"), Details, and Book (shared) or Request (private: Pitika and the owner both check it).
// The border takes the live line's tone (owner pick, 16 Nov 2026, kept 20 Nov): green free, red
// in use or busy soon, the plain rule when closed or there is nothing to say.
import { CalendarPlus, Clock, Layers, UserLock, Users } from 'lucide-vue-next'

import type { RoomListItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import type { NowLine } from './rules'

const props = defineProps<{ room: RoomListItem; now: NowLine }>()
const emit = defineEmits<{ details: []; book: [] }>()
const bookWord = () => (props.room.is_private ? 'Request' : 'Book')
</script>

<template>
  <article class="room-card" :class="now.tone">
    <button type="button" class="photo" tabindex="-1" aria-hidden="true" @click="emit('details')">
      <RoomPhoto :path="room.cover_photo?.url ?? null" :alt="room.name_en" />
      <span v-if="room.is_private" class="tag"><UserLock :size="12" aria-hidden="true" />Private</span>
    </button>
    <div class="body" @click="emit('details')">
      <div class="names">
        <p class="kh">{{ room.name_kh }}</p>
        <h2>{{ room.name_en }}</h2>
      </div>
      <p class="facts">
        <span><Users :size="14" aria-hidden="true" /><span class="num">{{ room.capacity }}</span> seats</span>
        <span class="floor" :title="room.floor.floor_label"><Layers :size="14" aria-hidden="true" /><span class="cut">{{ room.floor.floor_label }}</span></span>
      </p>
      <p v-if="room.short_desc" class="desc" :title="room.short_desc">{{ room.short_desc }}</p>
    </div>
    <div class="foot">
      <span class="st-now now" :class="now.tone"><Clock :size="14" aria-hidden="true" />{{ now.text }}</span>
      <div class="acts">
        <BaseButton variant="quiet" :aria-label="`Details of ${room.name_en}`" @click="emit('details')">Details</BaseButton>
        <BaseButton variant="primary" :aria-label="`${bookWord()} ${room.name_en}`" @click="emit('book')">
          <CalendarPlus :size="16" aria-hidden="true" />{{ bookWord() }}
        </BaseButton>
      </div>
    </div>
  </article>
</template>

<style scoped>
.room-card {
  display: flex;
  flex-direction: column;
  padding: 8px 8px 10px;
  border: 2px solid var(--color-rule);
  border-radius: 22px;
  transition: border-color 200ms var(--ease-out-quint);
  container: room-card / inline-size;
}
.room-card.ok {
  border-color: color-mix(in srgb, var(--color-ok) 70%, transparent);
}
.room-card.alert {
  border-color: color-mix(in srgb, var(--color-crimson) 70%, transparent);
}
.photo {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  padding: 0;
  border: 0;
  border-radius: 14px;
  background: var(--color-field-disabled);
  cursor: pointer;
}
.photo :deep(.room-photo) {
  width: 100%;
  height: 100%;
}
.photo :deep(img) {
  transition: transform 420ms var(--ease-out-quint);
}
.tag {
  position: absolute;
  top: 12px;
  left: 12px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: #2a1c13;
  font-size: 12px;
  font-weight: 500;
}
.tag svg {
  color: #9a4a06;
}
.body {
  display: grid;
  flex: 1;
  align-content: start;
  gap: 8px;
  min-width: 0;
  padding: 12px 4px 0;
  cursor: pointer;
}
.names {
  display: grid;
  gap: 1px;
  min-width: 0;
}
/* Khmer over English (owner, 20 Nov 2026; DESIGN.md "Two Names Rule"). */
.kh {
  margin: 0;
  color: var(--color-ink);
  font-family: var(--font-kh);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
}
h2 {
  margin: 0;
  color: var(--color-intaglio);
  font-size: 13px;
  font-weight: 400;
}
/* One line too (owner, 20 Nov 2026): seats stay whole, a long floor name is cut with "…". */
.facts {
  display: flex;
  gap: 14px;
  min-width: 0;
  margin: 0;
  color: var(--color-intaglio);
  font-size: 13px;
  white-space: nowrap;
}
.facts > span {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 6px;
}
.facts > .floor {
  flex: 0 1 auto;
  min-width: 0;
}
.cut {
  overflow: hidden;
  text-overflow: ellipsis;
}
.facts svg {
  flex: none;
}
.num {
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
}
/* One line, cut with "…"; the whole text shows on hover (owner, 20 Nov 2026). */
.desc {
  margin: 0;
  overflow: hidden;
  color: var(--color-ink-off);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* The status, Details and Book/Request always share one line (owner, 20 Nov 2026). On a narrow
   card the button drops its icon and a long status ("In use until 11:30") may take two short
   lines; the buttons never move. */
.foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 14px 4px 0;
  padding-top: 10px;
  border-top: 1px solid var(--color-rule);
}
.foot .now {
  flex: 1;
  min-width: 0;
  line-height: 1.3;
  white-space: normal;
}
.acts {
  display: flex;
  flex: none;
  gap: 2px;
  margin-left: auto;
}
.acts :deep(.btn.quiet) {
  padding: 0 10px;
}
@container room-card (max-width: 369px) {
  .acts :deep(.btn.primary svg) {
    display: none;
  }
  .acts :deep(.btn.primary) {
    padding: 0 14px;
  }
}
.acts :deep(.btn) {
  height: 40px;
  border-radius: 12px;
}
@media (hover: hover) and (pointer: fine) {
  .room-card:hover .photo :deep(img) {
    transform: scale(1.04);
  }
}
@media (prefers-reduced-motion: reduce) {
  .room-card,
  .photo :deep(img) {
    transition: none;
  }
}
</style>
