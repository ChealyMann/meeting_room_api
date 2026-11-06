<script setup lang="ts">
// One IT setup as a photo card (owner pick, 6 Nov 2026: demo E, "Photo cards"): the room's
// photo with the setup day and time on it, then what and where, the needs as icons (named on
// hover and to screen readers; crimson when the booker wrote a note), and a foot with the
// staff and the buttons the ticket's state allows.
import { Check, MessageSquareText, TriangleAlert, Wrench } from 'lucide-vue-next'
import { computed, toRef } from 'vue'

import type { ITTicketItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import StaffAvatar from '../../components/StaffAvatar.vue'
import { useTicketFacts } from './ticketFacts'

const props = defineProps<{
  ticket: ITTicketItem
  /** The room's cover photo, or null. */
  photo: string | null
  place: string | null
  now: Date
  today: string
  actions: boolean
  current?: boolean
}>()
const emit = defineEmits<{ open: []; assign: []; ready: [] }>()

const { b, isOpen, soon, setupDay, setupTime, meetingTimes, needs, staffNames } = useTicketFacts(
  toRef(props, 'ticket'),
  toRef(props, 'now'),
  toRef(props, 'today'),
)
// The foot is narrow: the first name and how many more ("Chan Bopha +1"); all names on hover.
const staffText = computed(() => {
  const [first, ...rest] = staffNames.value
  if (!first) return 'No staff yet'
  return rest.length ? `${first} +${rest.length}` : first
})
</script>

<template>
  <li class="card" :class="{ current, today: !!soon }" :data-ticket="ticket.id" tabindex="0" @click="emit('open')" @keydown.enter.self="emit('open')">
    <div class="photo">
      <RoomPhoto class="room-photo-fill" :path="photo" :alt="b.room.name_en" />
      <span class="when"><Wrench aria-hidden="true" />{{ setupDay }} · by <b class="mono">{{ setupTime }}</b></span>
      <span v-if="ticket.missed" class="flag missed"><TriangleAlert aria-hidden="true" />Missed</span>
      <span v-else-if="soon" class="flag soon">{{ soon }}</span>
    </div>
    <div class="body">
      <span class="ref mono"><span class="prefix">{{ b.reference_code.slice(0, 3) }}</span>{{ b.reference_code.slice(3) }}</span>
      <h3>{{ b.meeting_title }}</h3>
      <span class="line"><span class="kh">{{ b.room.name_kh }}</span> · {{ b.room.name_en }}</span>
      <span v-if="place" class="line place">{{ place }}</span>
      <span class="line">Meeting <span class="mono">{{ meetingTimes }}</span></span>
      <div class="needs">
        <span v-for="n in needs" :key="n.name" class="need" role="img" :aria-label="n.name" :title="n.name">
          <component :is="n.icon" aria-hidden="true" />
        </span>
        <span
          v-if="ticket.special_requirements"
          class="need note"
          role="img"
          :aria-label="`Note: ${ticket.special_requirements}`"
          :title="ticket.special_requirements"
        >
          <MessageSquareText aria-hidden="true" />
        </span>
      </div>
    </div>
    <div class="foot">
      <span class="who">
        <span v-if="staffNames.length" class="faces" :title="staffNames.join(', ')">
          <StaffAvatar v-for="s in ticket.staff" :key="s.id" :name="s.name_en" :photo="s.avatar_url ?? null" :size="26" />
        </span>
        <!-- Beside the buttons the names would be cut: the faces show, the names are read out. -->
        <span
          class="staff"
          :class="{ none: !staffNames.length, 'sr-only': staffNames.length && actions && isOpen }"
          :title="staffNames.join(', ')"
        >{{ staffText }}</span>
      </span>
      <span v-if="actions && isOpen" class="acts">
        <BaseButton v-if="ticket.status === 'RECEIVED'" variant="primary" @click.stop="emit('assign')">Assign staff</BaseButton>
        <template v-else>
          <BaseButton variant="quiet" @click.stop="emit('assign')">Change</BaseButton>
          <BaseButton variant="primary" @click.stop="emit('ready')"><Check aria-hidden="true" />Mark ready</BaseButton>
        </template>
      </span>
    </div>
  </li>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
  background: var(--color-sheet);
  cursor: pointer;
  transition: border-color 150ms ease;
}
.card:hover {
  border-color: var(--color-rule-strong);
}
.card.today {
  box-shadow: inset 0 3px 0 var(--color-crimson);
}
.card.current {
  border-color: var(--color-crimson);
}
.card:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
.photo {
  position: relative;
  height: 168px;
}
.room-photo-fill {
  width: 100%;
  height: 100%;
}
.when,
.flag {
  position: absolute;
  top: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 9px;
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
}
.when {
  left: 10px;
  background: rgba(38, 7, 7, 0.78);
}
.when b {
  font-weight: 500;
}
.flag {
  right: 10px;
  background: var(--color-crimson-fill);
  font-weight: 500;
}
.when :deep(svg.lucide),
.flag :deep(svg.lucide) {
  width: 13px;
  height: 13px;
}
.body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  padding: 12px 16px 14px;
}
.ref {
  font-size: 11.5px;
  color: var(--color-intaglio);
}
.prefix {
  color: var(--color-crimson);
}
h3 {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
  font-weight: 600;
}
.line {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.line .kh {
  font-family: var(--font-kh);
  font-weight: 500;
  color: var(--color-ink);
}
.line .mono {
  color: var(--color-ink);
}
.needs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.need {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--color-paper);
  color: var(--color-ink);
}
.need.note {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.need :deep(svg.lucide) {
  width: 15px;
  height: 15px;
}
.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 54px;
  padding: 8px 12px 8px 16px;
  border-top: 1px solid var(--color-rule);
  background: var(--color-paper);
  box-sizing: border-box;
}
.who {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 12.5px;
}
.faces {
  display: inline-flex;
  flex: none;
}
.faces > :deep(.staff-avatar) {
  border: 2px solid var(--color-paper);
}
.faces > :deep(.staff-avatar + .staff-avatar) {
  margin-left: -8px;
}
.staff {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.staff.none {
  color: var(--color-intaglio);
}
.acts {
  display: inline-flex;
  flex: none;
  gap: 2px;
}
.acts :deep(.btn) {
  height: 34px;
  padding: 0 12px;
  font-size: 13px;
}
.mono {
  font-family: var(--font-mono);
}
</style>
