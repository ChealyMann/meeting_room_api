<script setup lang="ts">
// Step 4, Review & confirm: what people most want to double-check first (room, time), then four
// tiles you click to change, each with a quiet pencil. The API's holiday warnings sit above them.
import { CircleAlert, Lock, Pencil } from 'lucide-vue-next'
import { computed } from 'vue'

import RoomPhoto from '../../../components/RoomPhoto.vue'
import UserAvatar from '../../../components/UserAvatar.vue'
import type { ServiceOut } from '../../../api/services'
import type { BookingCheckResult, RoomDetail } from '../../../api/types'
import { useSessionStore } from '../../../stores/session'
import { dateNumber, dayLabel, lenText, monthShort, toTime, weekdayShort } from '../rules'
import type { BookingDraft } from './useBookingDraft'

const props = defineProps<{
  draft: BookingDraft
  room: RoomDetail
  foods: ServiceOut[]
  its: ServiceOut[]
  check: BookingCheckResult | null
  /** The step that owns the check's problem, when it names one. */
  problemStep: number | null
}>()
const emit = defineEmits<{ jump: [number] }>()
const session = useSessionStore()

const sessions = computed(() =>
  [...props.draft.sessions].sort((x, y) => (x.date === y.date ? x.a - y.a : x.date < y.date ? -1 : 1)),
)
const one = computed(() => (sessions.value.length === 1 ? sessions.value[0]! : null))
const longDay = (iso: string) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', { weekday: 'long', timeZone: 'UTC' })
const total = computed(() => sessions.value.reduce((sum, s) => sum + s.b - s.a, 0))

const typeText = computed(() => `${props.draft.external ? 'External' : 'Internal'}${props.draft.governor ? ' · The Governor attends' : ''}`)
const names = (list: ServiceOut[], ids: number[]) => list.filter((s) => ids.includes(s.id)).map((s) => s.name)
const foodNames = computed(() => names(props.foods, props.draft.foods))
const itNames = computed(() => names(props.its, props.draft.its))

const holidayNotes = computed(() =>
  (props.check?.warnings ?? [])
    .filter((w) => w.code === 'PUBLIC_HOLIDAY' && typeof w.date === 'string')
    .map((w) => `${dayLabel(w.date as string)} is ${String(w.name ?? 'a public holiday')}`),
)
const cover = computed(() => props.room.photos[0]?.url ?? null)
</script>

<template>
  <div class="rv">
    <div class="rv-room">
      <div class="ph"><RoomPhoto :path="cover" :alt="room.name_en" /></div>
      <div>
        <b>{{ room.name_en }}</b>
        <span class="kh">{{ room.name_kh }}</span>
      </div>
      <span v-if="room.is_private" class="pill"><Lock :size="12" aria-hidden="true" />Private</span>
    </div>

    <button type="button" class="rv-time" aria-label="Change the times" @click="emit('jump', 1)">
      <template v-if="one">
        <span class="tile">
          <small>{{ weekdayShort(one.date).toUpperCase() }}</small><b>{{ dateNumber(one.date) }}</b
          ><small>{{ monthShort(one.date).toUpperCase() }}</small>
        </span>
        <span class="big">
          <b class="mono">{{ toTime(one.a) }}–{{ toTime(one.b) }}</b>
          <span>{{ longDay(one.date) }} {{ dateNumber(one.date) }} {{ monthShort(one.date) }} · {{ lenText(one.b - one.a) }}</span>
        </span>
      </template>
      <span v-else class="big">
        <b>{{ sessions.length }} sessions</b>
        <span class="chips">
          <span v-for="s in sessions" :key="`${s.date}-${s.a}`" class="chip">{{ dayLabel(s.date) }} <span class="mono">{{ toTime(s.a) }}–{{ toTime(s.b) }}</span></span>
        </span>
        <span>{{ lenText(total) }} in all</span>
      </span>
      <Pencil class="pen" :size="15" aria-hidden="true" />
    </button>

    <p v-if="check?.problem" class="rv-problem" role="alert">
      <CircleAlert :size="16" aria-hidden="true" /><span>{{ check.problem.message }}</span>
      <button v-if="problemStep" type="button" @click="emit('jump', problemStep)">Change</button>
    </p>
    <p v-for="n in holidayNotes" :key="n" class="rv-warn">{{ n }}</p>

    <div class="tiles">
      <button type="button" class="t" @click="emit('jump', 2)">
        <small>Meeting</small>
        <b>{{ draft.title }}</b>
        <span>{{ typeText }} · {{ draft.people }} {{ draft.people === 1 ? 'person' : 'people' }}</span>
        <span v-if="draft.emails.length">{{ draft.emails.length }} invited by email</span>
        <Pencil class="pen" :size="14" aria-hidden="true" />
      </button>
      <button type="button" class="t" @click="emit('jump', 3)">
        <small>Food &amp; drinks</small>
        <b v-if="foodNames.length">{{ foodNames.join(', ') }}</b>
        <b v-else class="off">None</b>
        <span v-if="foodNames.length">× {{ draft.people }} each</span>
        <span v-if="draft.foodNote">{{ draft.foodNote }}</span>
        <Pencil class="pen" :size="14" aria-hidden="true" />
      </button>
      <button type="button" class="t" @click="emit('jump', 3)">
        <small>IT help</small>
        <b v-if="itNames.length">{{ itNames.join(', ') }}</b>
        <b v-else class="off">None</b>
        <span v-if="draft.itNote">{{ draft.itNote }}</span>
        <Pencil class="pen" :size="14" aria-hidden="true" />
      </button>
      <button type="button" class="t" @click="emit('jump', 2)">
        <small>{{ room.is_private ? 'Why this room' : 'Notes' }}</small>
        <b v-if="room.is_private ? draft.justification : draft.notes" class="para">{{ room.is_private ? draft.justification : draft.notes }}</b>
        <b v-else class="off">None</b>
        <span v-if="room.is_private && draft.notes" class="para">{{ draft.notes }}</span>
        <Pencil class="pen" :size="14" aria-hidden="true" />
      </button>
    </div>

    <div v-if="session.user" class="by">
      <UserAvatar :path="session.user.avatar_url" :name="session.user.name_en" />
      <span><small>Booked by</small>{{ session.user.name_en }}</span>
      <span class="mail">{{ session.user.email }}</span>
    </div>
  </div>
</template>

<style scoped>
.rv {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  overflow: auto;
  padding: 2px;
  scrollbar-width: thin;
}
.rv-room {
  display: flex;
  align-items: center;
  gap: 14px;
}
.rv-room .ph {
  flex: none;
  width: 64px;
  height: 48px;
  overflow: hidden;
  border-radius: 12px;
}
.rv-room .ph :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.rv-room b {
  display: block;
  font-size: 15px;
}
.kh {
  color: var(--color-intaglio);
  font-family: var(--font-kh);
  font-size: 13px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-left: auto;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--color-saved-tint);
  color: var(--color-warn);
  font-size: 12px;
  font-weight: 500;
}
.rv-time,
.t {
  position: relative;
  border: 0;
  border-radius: 18px;
  background: var(--color-paper);
  color: var(--color-ink);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
.rv-time:active,
.t:active {
  transform: scale(0.99);
}
.rv-time {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 18px 20px;
}
.tile {
  display: grid;
  flex: none;
  justify-items: center;
  width: 64px;
  padding: 8px 0;
  border-radius: 14px;
  background: var(--color-sheet);
  box-shadow: 0 1px 3px rgba(42, 28, 19, 0.1);
}
.tile small {
  color: var(--color-crimson);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
}
.tile small:last-child {
  color: var(--color-intaglio);
}
.tile b {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.1;
}
.big {
  display: grid;
  gap: 4px;
}
.big > b {
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.big > span {
  color: var(--color-intaglio);
  font-size: 14px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font-size: 12.5px;
}
.pen {
  position: absolute;
  top: 16px;
  right: 16px;
  color: var(--color-ink-off);
}
.rv-problem {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-size: 13.5px;
}
.rv-problem span {
  flex: 1;
}
.rv-problem button {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.rv-warn {
  margin: 0;
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--color-saved-tint);
  color: var(--color-warn);
  font-size: 13px;
}
.tiles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.t {
  display: grid;
  align-content: start;
  gap: 4px;
  min-height: 108px;
  padding: 16px 40px 16px 18px;
}
.t small {
  color: var(--color-ink-off);
  font-size: 12px;
}
.t b {
  font-size: 15px;
  font-weight: 600;
}
.t b.off {
  color: var(--color-ink-off);
  font-weight: 500;
}
.t span {
  color: var(--color-intaglio);
  font-size: 13px;
}
.para {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
.by {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--color-rule);
  font-size: 14px;
}
.by small {
  display: block;
  color: var(--color-ink-off);
  font-size: 11.5px;
}
.by .mail {
  margin-left: auto;
  color: var(--color-intaglio);
  font-size: 13px;
}
@media (hover: hover) and (pointer: fine) {
  .rv-time:hover,
  .t:hover {
    background: var(--color-field-disabled);
  }
  .rv-time:hover .pen,
  .t:hover .pen {
    color: var(--color-ink);
  }
}
@media (max-width: 760px) {
  .tiles {
    grid-template-columns: 1fr;
  }
}
@media (prefers-reduced-motion: reduce) {
  .rv-time,
  .t {
    transition: none;
  }
}
</style>
