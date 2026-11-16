<script setup lang="ts">
// One room on Find a room: the photo, the names, the facts, a live line ("Free until 14:00"),
// then Details and Book (shared) or Request (private: Pitika and the owner both check it).
import { CalendarPlus, Clock, Lock } from 'lucide-vue-next'

import type { RoomListItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import type { NowLine } from './rules'

const props = defineProps<{ room: RoomListItem; now: NowLine }>()
const emit = defineEmits<{ details: []; book: [] }>()
const bookWord = () => (props.room.is_private ? 'Request' : 'Book')
</script>

<template>
  <article class="room-card">
    <button type="button" class="photo" tabindex="-1" aria-hidden="true" @click="emit('details')">
      <RoomPhoto :path="room.cover_photo?.url ?? null" :alt="room.name_en" />
      <span v-if="room.is_private" class="tag"><Lock :size="12" aria-hidden="true" />Private</span>
    </button>
    <div class="body" @click="emit('details')">
      <div class="top">
        <h2>{{ room.name_en }}</h2>
        <span class="st-now now" :class="now.tone"><Clock :size="14" aria-hidden="true" />{{ now.text }}</span>
      </div>
      <p class="kh">{{ room.name_kh }}</p>
      <p class="facts">
        {{ room.capacity }} seats · {{ room.floor.floor_label }}<template v-if="room.short_desc"> · {{ room.short_desc }}</template>
      </p>
    </div>
    <div class="acts">
      <BaseButton :aria-label="`Details of ${room.name_en}`" @click="emit('details')">Details</BaseButton>
      <BaseButton variant="primary" :aria-label="`${bookWord()} ${room.name_en}`" @click="emit('book')">
        <CalendarPlus :size="16" aria-hidden="true" />{{ bookWord() }}
      </BaseButton>
    </div>
  </article>
</template>

<style scoped>
.room-card {
  display: flex;
  flex-direction: column;
}
.photo {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  padding: 0;
  border: 0;
  border-radius: 18px;
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
.body {
  display: grid;
  flex: 1;
  align-content: start;
  gap: 2px;
  padding: 12px 2px 0;
  cursor: pointer;
}
.top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
h2 {
  margin: 0;
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.kh {
  margin: 0;
  color: var(--color-intaglio);
  font-family: var(--font-kh);
  font-size: 13px;
}
.facts {
  margin: 0;
  color: var(--color-ink-off);
  font-size: 13px;
}
.acts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
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
  .photo :deep(img) {
    transition: none;
  }
}
</style>
