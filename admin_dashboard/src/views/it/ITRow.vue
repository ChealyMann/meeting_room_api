<script setup lang="ts">
// One IT setup as a row (owner pick, 6 Nov 2026: sketch G, "State stripe"): a sheet slip with a
// stripe at its left edge for the state (dashed amber: needs staff; green: staff set; grey:
// ready; crimson: missed), then columns parted by hairlines: the setup time and day, the room's
// photo with the reference on it, the meeting and the room with the needs, the meeting time,
// the state in words with the staff, and the buttons the ticket's state allows. The row is a
// container: narrower, the meeting time joins the room line and the buttons go under the state;
// on a phone everything stacks.
import { Check, CircleAlert, CircleCheck, Clock, DoorOpen, MessageSquareText, TriangleAlert, UserPlus } from 'lucide-vue-next'
import { computed, toRef } from 'vue'

import type { ITTicketItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import StaffAvatar from '../../components/StaffAvatar.vue'
import { phnomPenhClock } from '../../utils/time'
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

const stateWord = computed(() => {
  if (state.value === 'missed') return 'Missed · not marked ready'
  if (state.value === 'ready') return props.ticket.ready_at ? `Ready · ${phnomPenhClock(new Date(props.ticket.ready_at))}` : 'Ready'
  return state.value === 'staffed' ? 'Staff set · not ready' : 'Needs staff'
})
</script>

<template>
  <li
    class="row"
    :class="[`state-${state}`, { current }]"
    :data-ticket="ticket.id"
    tabindex="0"
    @click="emit('open')"
    @keydown.enter.self="emit('open')"
  >
    <div class="slip">
      <span class="stripe" aria-hidden="true" />
      <div class="when">
        <span class="time-label">Set up by</span>
        <b class="time mono">{{ setupTime }}</b>
        <span class="day" :class="{ today: setupDay === 'Today' }">{{ setupDay }}</span>
        <span v-if="soon" class="soon"><CircleAlert aria-hidden="true" />{{ soon }}</span>
      </div>
      <div class="photo">
        <RoomPhoto class="photo-fill" :path="photo" :alt="b.room.name_en" />
        <span class="ref mono">{{ b.reference_code }}</span>
      </div>
      <div class="info">
        <h3>{{ b.meeting_title }}</h3>
        <div class="room">
          <DoorOpen aria-hidden="true" />
          <span class="room-text">
            <span class="kh">{{ b.room.name_kh }}</span> · {{ b.room.name_en }}<template v-if="place"> · <span class="place">{{ place }}</span></template>
            <span class="meet-inline"> · <span class="mono">{{ meetingTimes }}</span></span>
          </span>
        </div>
        <div class="checks">
          <span v-for="n in needs" :key="n.name" class="chk"><component :is="n.icon" aria-hidden="true" />{{ n.name }}</span>
          <span v-if="ticket.special_requirements" class="note" :title="ticket.special_requirements">
            <MessageSquareText aria-hidden="true" />Note
            <span class="sr-only">: {{ ticket.special_requirements }}</span>
          </span>
        </div>
      </div>
      <span class="rule rule-1" aria-hidden="true" />
      <div class="meet">
        <span class="cap">Meeting</span>
        <span class="mono">{{ meetingTimes }}</span>
      </div>
      <span class="rule rule-2" aria-hidden="true" />
      <div class="who">
        <span class="state-word">
          <TriangleAlert v-if="state === 'missed'" aria-hidden="true" />
          <Check v-else-if="state === 'ready'" aria-hidden="true" />
          <CircleCheck v-else-if="state === 'staffed'" aria-hidden="true" />
          <Clock v-else aria-hidden="true" />{{ stateWord }}
        </span>
        <span class="people">
          <span v-if="staffNames.length" class="faces">
            <StaffAvatar v-for="s in ticket.staff" :key="s.id" :name="s.name_en" :photo="s.avatar_url ?? null" :size="24" />
          </span>
          <span class="staff" :class="{ none: !staffNames.length }">{{ staffNames.length ? staffNames.join(', ') : 'No staff yet' }}</span>
        </span>
      </div>
      <div v-if="actions && isOpen" class="acts">
        <BaseButton v-if="ticket.status === 'RECEIVED'" variant="primary" @click.stop="emit('assign')">
          <UserPlus aria-hidden="true" />Assign staff
        </BaseButton>
        <template v-else>
          <BaseButton aria-label="Change staff" @click.stop="emit('assign')">Change</BaseButton>
          <BaseButton variant="primary" @click.stop="emit('ready')"><Check aria-hidden="true" />Mark ready</BaseButton>
        </template>
      </div>
    </div>
  </li>
</template>

<style scoped>
.row {
  container-type: inline-size;
  padding: 0 12px;
  cursor: pointer;
}
.row + .row {
  margin-top: 10px;
}
.row:focus-visible {
  outline: none;
}
.row:focus-visible .slip {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
.slip {
  position: relative;
  display: grid;
  grid-template-columns: 76px 112px minmax(0, 1fr) 1px 96px 1px 180px auto;
  grid-template-areas: 'when photo info r1 meet r2 who acts';
  align-items: center;
  gap: 12px;
  padding: 12px 14px 12px 20px;
  overflow: hidden;
  border: 1px solid var(--color-rule);
  border-radius: 10px;
  background: var(--color-sheet);
  transition:
    border-color 150ms ease,
    background-color 150ms ease;
}
.row:hover .slip {
  border-color: var(--color-rule-strong);
}
.row.current .slip {
  border-color: var(--color-danger-line);
  background: var(--color-crimson-wash);
}
.row.state-ready .slip {
  background: var(--color-row-hover);
}
.stripe {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 4px;
}
.state-waiting .stripe {
  background: repeating-linear-gradient(var(--color-warn) 0 6px, transparent 6px 10px);
}
.state-staffed .stripe {
  background: var(--color-ok);
}
.state-ready .stripe {
  background: var(--color-off-ring);
}
.state-missed .stripe {
  background: var(--color-crimson);
}
.when {
  grid-area: when;
  display: grid;
  min-width: 0;
}
.time-label,
.cap {
  font-size: 10.5px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-intaglio);
}
.time {
  font-size: 22px;
  font-weight: 500;
  line-height: 1.1;
}
.state-ready .time {
  color: var(--color-intaglio);
}
.day {
  font-size: 12.5px;
  color: var(--color-intaglio);
  white-space: nowrap;
}
.day.today {
  color: var(--color-crimson);
  font-weight: 500;
}
.soon {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-top: 2px;
  color: var(--color-crimson);
  font-size: 11px;
  font-weight: 500;
  line-height: 1.3;
}
.soon :deep(svg.lucide) {
  width: 12px;
  height: 12px;
}
.photo {
  grid-area: photo;
  position: relative;
  width: 112px;
  height: 60px;
  overflow: hidden;
  border-radius: 8px;
}
.photo-fill {
  width: 100%;
  height: 100%;
}
.ref {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 12px 6px 4px;
  background: linear-gradient(to top, rgba(23, 4, 4, 0.85), rgba(23, 4, 4, 0));
  color: #fff;
  font-size: 11px;
  text-align: center;
}
.info {
  grid-area: info;
  display: grid;
  gap: 3px;
  min-width: 0;
}
.info h3 {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
  font-weight: 600;
}
.room {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.room-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.room .kh {
  font-family: var(--font-kh);
  font-weight: 500;
  color: var(--color-ink);
}
.meet-inline {
  display: none;
}
.meet-inline .mono {
  color: var(--color-ink);
}
.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
  font-size: 12px;
  color: var(--color-intaglio);
}
.chk,
.note {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.note {
  color: var(--color-crimson);
}
.info :deep(svg.lucide) {
  flex: none;
  width: 13px;
  height: 13px;
}
.rule {
  width: 1px;
  height: 44px;
  background: var(--color-rule);
}
.rule-1 {
  grid-area: r1;
}
.rule-2 {
  grid-area: r2;
}
.meet {
  grid-area: meet;
  display: grid;
}
.meet .mono {
  font-size: 14px;
  white-space: nowrap;
}
.who {
  grid-area: who;
  display: grid;
  gap: 4px;
  min-width: 0;
}
.state-word {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-ok);
}
.state-waiting .state-word {
  color: var(--color-warn);
}
.state-missed .state-word {
  color: var(--color-crimson);
}
.state-word :deep(svg.lucide) {
  flex: none;
  width: 13px;
  height: 13px;
}
.people {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 13px;
}
.faces {
  display: inline-flex;
  flex: none;
}
.faces > :deep(.staff-avatar) {
  border: 2px solid var(--color-sheet);
}
.faces > :deep(.staff-avatar + .staff-avatar) {
  margin-left: -7px;
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
  grid-area: acts;
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.acts :deep(.btn) {
  height: 34px;
  padding: 0 12px;
  font-size: 13px;
}
.mono {
  font-family: var(--font-mono);
}

/* Narrower: the meeting time joins the room line, and the buttons go under the state. */
@container (max-width: 1000px) {
  .slip {
    grid-template-columns: 76px 112px minmax(0, 1fr) 1px 220px;
    grid-template-areas:
      'when photo info r2 who'
      'when photo info r2 acts';
    row-gap: 8px;
  }
  .rule-1,
  .meet {
    display: none;
  }
  .meet-inline {
    display: inline;
  }
  .rule-2 {
    align-self: stretch;
    height: auto;
  }
  .acts {
    justify-content: flex-start;
  }
}

/* A phone: one column. */
@container (max-width: 560px) {
  .slip {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: 'when' 'photo' 'info' 'who' 'acts';
    gap: 10px;
    padding-left: 18px;
  }
  .when {
    grid-template-columns: auto auto 1fr;
    align-items: baseline;
    column-gap: 8px;
  }
  .time-label {
    grid-column: 1 / -1;
  }
  .soon {
    justify-self: end;
    white-space: nowrap;
  }
  .photo {
    width: 100%;
    height: 120px;
  }
  .rule-2 {
    display: none;
  }
}
</style>
