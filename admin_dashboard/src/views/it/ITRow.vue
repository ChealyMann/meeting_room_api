<script setup lang="ts">
// One IT setup (spec 2026-11-05-owner-and-it-pages-design, Part B, "Row"): the room and where it
// is, when to set up, what to set up, the staff, and the buttons the ticket's state allows.
import { CalendarDays, Check, MapPin, Monitor, TriangleAlert, UserRound, Wrench } from 'lucide-vue-next'
import { computed } from 'vue'

import type { ITTicketItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { setupText } from '../../utils/itQueue'
import { startsIn } from '../../utils/reviewQueue'
import { formatDay } from '../../utils/time'

const props = defineProps<{
  ticket: ITTicketItem
  /** The room's cover thumbnail, or null. */
  photo: string | null
  /** "Head Office · Building A · Floor 2", or null when the rooms list did not load. */
  place: string | null
  now: Date
  today: string
  /** false: read only (My tasks). */
  actions: boolean
  current?: boolean
}>()
const emit = defineEmits<{ open: []; assign: []; ready: [] }>()

const b = computed(() => props.ticket.booking)
const hhmm = (time: string) => time.slice(0, 5)
const names = computed(() => props.ticket.items.map((i) => String((i as Record<string, unknown>).name)))
const isOpen = computed(() => !props.ticket.missed && props.ticket.status !== 'READY')
const soon = computed(() => (isOpen.value && props.ticket.setup_date <= props.today ? startsIn(b.value, props.now) : null))
const day = computed(() => (b.value.first_session.date === props.today ? 'Today' : formatDay(b.value.first_session.date).slice(0, -5)))
const staffText = computed(() => (props.ticket.staff.length ? props.ticket.staff.map((s) => s.name_en).join(', ') : 'No staff yet'))
</script>

<template>
  <li class="row" :class="{ current }" :data-ticket="ticket.id" tabindex="0" @click="emit('open')" @keydown.enter.self="emit('open')">
    <RoomPhoto class="thumb" :path="photo" :alt="b.room.name_en" />
    <div class="info">
      <span class="ref mono"><span class="prefix">{{ b.reference_code.slice(0, 3) }}</span>{{ b.reference_code.slice(3) }}</span>
      <h3>{{ b.meeting_title }}</h3>
      <div class="room"><span class="kh">{{ b.room.name_kh }}</span> · {{ b.room.name_en }}</div>
      <div v-if="place" class="where"><MapPin aria-hidden="true" /><span class="place">{{ place }}</span></div>
      <div class="facts">
        <span class="setup"><Wrench aria-hidden="true" />{{ setupText(ticket) }}</span>
        <span>
          <CalendarDays aria-hidden="true" />{{ day }} · meeting
          <span class="mono">{{ hhmm(b.first_session.start_time) }}–{{ hhmm(b.first_session.end_time) }}</span>
        </span>
        <span><UserRound aria-hidden="true" /><span class="staff">{{ staffText }}</span></span>
      </div>
      <div class="checks">
        <span v-for="n in names" :key="n" class="chk"><Monitor aria-hidden="true" /><b>{{ n }}</b></span>
      </div>
      <p v-if="ticket.special_requirements" class="needs">{{ ticket.special_requirements }}</p>
    </div>
    <div class="side">
      <span v-if="ticket.missed" class="missed"><TriangleAlert aria-hidden="true" />Missed · not marked ready</span>
      <span v-else-if="soon" class="soon"><TriangleAlert aria-hidden="true" />{{ soon }}</span>
      <div v-if="actions && isOpen" class="acts">
        <BaseButton v-if="ticket.status === 'RECEIVED'" variant="primary" @click.stop="emit('assign')">Assign staff</BaseButton>
        <template v-else>
          <BaseButton variant="quiet" @click.stop="emit('assign')">Change staff</BaseButton>
          <BaseButton variant="primary" @click.stop="emit('ready')"><Check aria-hidden="true" />Mark ready</BaseButton>
        </template>
      </div>
    </div>
  </li>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr) 232px;
  gap: 20px;
  align-items: center;
  padding: 16px 12px;
  border-bottom: 1px solid var(--color-rule);
  cursor: pointer;
  transition: background-color 150ms ease;
}
.row:hover {
  background: var(--color-row-hover);
}
.row.current {
  background: var(--color-crimson-wash);
}
.row:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: -2px;
}
.thumb {
  width: 168px;
  aspect-ratio: 16 / 10;
  border-radius: 8px;
}
.info {
  min-width: 0;
}
.ref {
  font-size: 11.5px;
  color: var(--color-intaglio);
}
.prefix {
  color: var(--color-crimson);
}
.info h3 {
  margin: 2px 0;
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.room,
.where {
  font-size: 13px;
  color: var(--color-intaglio);
}
.where {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 2px;
}
.room .kh {
  font-family: var(--font-kh);
  font-weight: 500;
  color: var(--color-ink);
}
.facts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-top: 8px;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.facts > span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.facts .setup {
  font-weight: 600;
  color: var(--color-ink);
}
.facts .mono {
  font-size: 12px;
  color: var(--color-ink);
}
.facts :deep(svg.lucide),
.where :deep(svg.lucide),
.chk :deep(svg.lucide) {
  width: 14px;
  height: 14px;
  flex: none;
}
.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.chk {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 24px;
  padding: 2px 8px;
  border: 1px solid var(--color-rule);
  border-radius: 6px;
  background: var(--color-paper);
  font-size: 12px;
}
.chk :deep(svg.lucide) {
  color: var(--color-intaglio);
}
.chk b {
  font-weight: 500;
}
.needs {
  margin: 8px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.side {
  display: grid;
  gap: 10px;
  align-content: center;
}
.soon,
.missed {
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-size: 12px;
  font-weight: 500;
}
.soon :deep(svg.lucide),
.missed :deep(svg.lucide) {
  width: 13px;
  height: 13px;
}
.acts {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.acts :deep(.btn) {
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
}
.mono {
  font-family: var(--font-mono);
}
@media (max-width: 1100px) {
  .row {
    grid-template-columns: 132px minmax(0, 1fr);
  }
  .thumb {
    width: 132px;
  }
  .side {
    grid-column: 1 / -1;
  }
  .soon,
  .missed {
    justify-self: start;
  }
  .acts {
    justify-content: flex-start;
  }
}
@media (max-width: 560px) {
  .row {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .thumb {
    width: 100%;
  }
}
</style>
