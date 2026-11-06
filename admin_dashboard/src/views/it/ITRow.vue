<script setup lang="ts">
// One IT setup on the time line (owner pick, 6 Nov 2026: demo C, "Day timeline"): the setup
// time at the left, a dot on the line (dashed amber: needs staff; green check: has staff or is
// ready; crimson: missed), then the setup on a sheet: the room's photo, what, where, the needs
// with icons, the staff and the buttons the ticket's state allows.
import { Check, CircleAlert, MessageSquareText, TriangleAlert, X } from 'lucide-vue-next'
import { toRef } from 'vue'

import type { ITTicketItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import StaffAvatar from '../../components/StaffAvatar.vue'
import { useTicketFacts } from './ticketFacts'

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

const { b, isOpen, soon, setupDay, setupTime, meetingTimes, needs, staffNames, state } = useTicketFacts(
  toRef(props, 'ticket'),
  toRef(props, 'now'),
  toRef(props, 'today'),
)
</script>

<template>
  <li class="row" :class="{ current }" :data-ticket="ticket.id" tabindex="0" @click="emit('open')" @keydown.enter.self="emit('open')">
    <div class="when">
      <span class="time-label">Set up by</span>
      <b class="time mono">{{ setupTime }}</b>
      <span class="day">{{ setupDay }}</span>
    </div>
    <div class="line" aria-hidden="true">
      <span class="node" :class="`state-${state}`">
        <Check v-if="state === 'staffed' || state === 'ready'" />
        <X v-else-if="state === 'missed'" />
      </span>
    </div>
    <div class="slip">
      <RoomPhoto class="thumb" :path="photo" :alt="b.room.name_en" />
      <div class="info">
        <div class="title">
          <h3>{{ b.meeting_title }}</h3>
          <span class="ref mono"><span class="prefix">{{ b.reference_code.slice(0, 3) }}</span>{{ b.reference_code.slice(3) }}</span>
        </div>
        <div class="room">
          <span class="kh">{{ b.room.name_kh }}</span> · {{ b.room.name_en }}<template v-if="place"> · <span class="place">{{ place }}</span></template>
          · meeting <span class="mono">{{ meetingTimes }}</span>
        </div>
        <div class="checks">
          <span v-for="n in needs" :key="n.name" class="chk"><component :is="n.icon" aria-hidden="true" /><b>{{ n.name }}</b></span>
          <span v-if="ticket.special_requirements" class="note" :title="ticket.special_requirements">
            <MessageSquareText aria-hidden="true" /><span class="needs">{{ ticket.special_requirements }}</span>
          </span>
        </div>
      </div>
      <div class="who">
        <span v-if="staffNames.length" class="faces">
          <StaffAvatar v-for="s in ticket.staff" :key="s.id" :name="s.name_en" :photo="s.avatar_url ?? null" :size="26" />
        </span>
        <span class="staff" :class="{ none: !staffNames.length }">{{ staffNames.length ? staffNames.join(', ') : 'No staff yet' }}</span>
      </div>
      <div v-if="ticket.missed || soon || (actions && isOpen)" class="side">
        <span v-if="ticket.missed" class="missed"><TriangleAlert aria-hidden="true" />Missed · not marked ready</span>
        <span v-else-if="soon" class="soon"><CircleAlert aria-hidden="true" />{{ soon }}</span>
        <div v-if="actions && isOpen" class="acts">
          <BaseButton v-if="ticket.status === 'RECEIVED'" variant="primary" @click.stop="emit('assign')">Assign staff</BaseButton>
          <template v-else>
            <BaseButton variant="quiet" @click.stop="emit('assign')">Change staff</BaseButton>
            <BaseButton variant="primary" @click.stop="emit('ready')"><Check aria-hidden="true" />Mark ready</BaseButton>
          </template>
        </div>
      </div>
    </div>
  </li>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 64px 28px minmax(0, 1fr);
  column-gap: 12px;
  padding: 0 12px;
  cursor: pointer;
}
.row:focus-visible {
  outline: none;
}
.row:focus-visible .slip {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
.when {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding-top: 12px;
  text-align: right;
}
.time {
  font-size: 15px;
  font-weight: 500;
  line-height: 1.25;
}
.time-label,
.day {
  font-size: 11px;
  color: var(--color-intaglio);
  white-space: nowrap;
}
.line {
  display: flex;
  flex-direction: column;
  align-items: center;
}
/* The line runs through every dot of a group; it starts at the first dot and ends at the last. */
.line::before,
.line::after {
  content: '';
  width: 1px;
  background: var(--color-rule-strong);
}
.line::before {
  height: 22px;
  flex: none;
}
.line::after {
  flex: 1;
}
.row:first-child .line::before,
.row:last-child .line::after {
  background: transparent;
}
.node {
  display: grid;
  flex: none;
  place-items: center;
  width: 20px;
  height: 20px;
  box-sizing: border-box;
  border-radius: 50%;
  color: #fff;
}
.node.state-waiting {
  border: 1.5px dashed var(--color-warn);
  background: var(--color-paper);
}
.node.state-staffed,
.node.state-ready {
  background: var(--color-ok);
}
.node.state-missed {
  background: var(--color-crimson);
}
.node :deep(svg.lucide) {
  width: 12px;
  height: 12px;
  stroke-width: 2.75;
}
.slip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 16px;
  min-width: 0;
  margin: 6px 0;
  padding: 10px 14px;
  border: 1px solid var(--color-rule);
  border-radius: 10px;
  background: var(--color-sheet);
  transition:
    background-color 150ms ease,
    border-color 150ms ease;
}
.row:hover .slip {
  border-color: var(--color-rule-strong);
}
.row.current .slip {
  border-color: var(--color-danger-line);
  background: var(--color-crimson-wash);
}
.thumb {
  flex: none;
  width: 104px;
  height: 66px;
  border-radius: 8px;
}
.info {
  display: grid;
  flex: 1 1 300px;
  gap: 3px;
  min-width: 0;
}
.title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}
.title h3 {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
  font-weight: 600;
}
.ref {
  flex: none;
  font-size: 11.5px;
  color: var(--color-intaglio);
}
.prefix {
  color: var(--color-crimson);
}
.room {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.room .kh {
  font-family: var(--font-kh);
  font-weight: 500;
  color: var(--color-ink);
}
.room .mono {
  color: var(--color-ink);
}
.checks {
  display: flex;
  align-items: center;
  gap: 4px 14px;
  min-width: 0;
  margin-top: 2px;
  font-size: 12.5px;
}
.chk,
.note {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.chk {
  flex: none;
}
.chk b {
  font-weight: 400;
}
.note {
  min-width: 0;
  color: var(--color-intaglio);
}
.needs {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.checks :deep(svg.lucide) {
  flex: none;
  width: 14px;
  height: 14px;
}
.who {
  display: flex;
  flex: 0 1 190px;
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
  border: 2px solid var(--color-sheet);
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
.side {
  display: grid;
  justify-items: end;
  gap: 8px;
  margin-left: auto;
}
.soon,
.missed {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
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
  gap: 4px;
}
.acts :deep(.btn) {
  height: 34px;
  padding: 0 13px;
  font-size: 13px;
}
.mono {
  font-family: var(--font-mono);
}
@media (max-width: 760px) {
  .row {
    grid-template-columns: 56px 20px minmax(0, 1fr);
    column-gap: 8px;
    padding: 0 4px 0 0;
  }
  .time-label {
    display: none;
  }
  .checks {
    flex-wrap: wrap;
  }
  .thumb {
    width: 100%;
    height: 120px;
  }
  .side {
    justify-items: start;
    margin-left: 0;
  }
}
</style>
