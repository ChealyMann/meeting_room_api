<script setup lang="ts">
// Book a room (Staff): four steps on the left, the side card on the right, no page scroll on a
// computer. Step 1 is the week table; the time picked on the room page arrives in the query.
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../../api'
import { getRoomSchedule } from '../../api/bookings'
import { getRoom } from '../../api/rooms'
import { listHolidays } from '../../api/staff'
import type { PublicHolidayOut, RoomDetail, ScheduleItem } from '../../api/types'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { addDays, phnomPenhClock } from '../../utils/time'
import SideCard from './book/SideCard.vue'
import StepBar from './book/StepBar.vue'
import { useBookingDraft } from './book/useBookingDraft'
import WeekTable from './book/WeekTable.vue'
import { dayLabel, roomHours, toMin, workdaysFrom, type PickedSession } from './rules'
import './staff.css'

const STEPS = ['Schedule', 'Meeting details', 'Food & IT', 'Review']
const WEEK = 5

const route = useRoute()
const router = useRouter()
const today = usePhnomPenhToday()
const tomorrow = computed(() => addDays(today.value, 1))
const roomId = Number(route.params.roomId)

/** The time picked on the room page, when the query holds a whole one. */
function fromQuery(): PickedSession | null {
  const { date, start, end } = route.query
  if (typeof date !== 'string' || typeof start !== 'string' || typeof end !== 'string') return null
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(start) || !/^\d{2}:\d{2}$/.test(end)) return null
  const a = toMin(start)
  const b = toMin(end)
  return b > a ? { date, a, b } : null
}
const first = fromQuery()
const { draft, addSession, removeSession } = useBookingDraft(roomId, first)

const room = ref<RoomDetail | null>(null)
const busy = ref<ScheduleItem[]>([])
const holidays = ref<PublicHolidayOut[]>([])
const failed = ref(false)
const message = ref('')
const reached = ref(1)

const now = () => toMin(phnomPenhClock(new Date()))
const hours = computed(() => (room.value ? roomHours(room.value) : { open: 480, close: 1080 }))

// The week window: page 0 is the next 5 working days from today; the arrows move 5 working days.
const firstPage = () => {
  if (!first) return 0
  const index = workdaysFrom(today.value, WEEK * 12).indexOf(first.date)
  return index < 0 ? 0 : Math.floor(index / WEEK)
}
const page = ref(firstPage())
const days = computed(() => workdaysFrom(today.value, WEEK * (page.value + 1)).slice(WEEK * page.value))
const range = computed(() => `${dayLabel(days.value[0]!)} – ${dayLabel(days.value[days.value.length - 1]!)}`)

async function loadWeek() {
  const from = days.value[0]!
  const to = days.value[days.value.length - 1]!
  const [schedule, offDays] = await Promise.all([getRoomSchedule(api, roomId, from, to), listHolidays(api, from, to)])
  busy.value = schedule.items
  holidays.value = offDays
}
onMounted(async () => {
  try {
    room.value = await getRoom(api, roomId)
    await loadWeek()
  } catch {
    failed.value = true
  }
})
watch(page, () => loadWeek().catch(() => (failed.value = true)))

function add(s: PickedSession) {
  addSession(s)
  message.value = ''
}

function go(step: number) {
  if (step > 1 && draft.sessions.length === 0) {
    message.value = 'Pick at least one time in the table.'
    return
  }
  message.value = ''
  draft.step = step as 1 | 2 | 3 | 4
  reached.value = Math.max(reached.value, step)
}
const nextLabel = computed(() => (draft.step < STEPS.length ? `Next: ${STEPS[draft.step]}` : 'Send request'))
function back() {
  if (draft.step > 1) go(draft.step - 1)
  else router.push({ name: 'staff-room', params: { roomId } })
}
</script>

<template>
  <section class="st-page book-page">
    <p v-if="failed" class="st-empty" role="alert"><b>This room could not load</b></p>
    <template v-else-if="room">
      <header class="bf-head">
        <h1>Book {{ room.name_en }}</h1>
        <StepBar :steps="STEPS" :current="draft.step" :reachable="(n) => n <= reached" @jump="go" />
      </header>
      <div class="bf">
        <main class="bf-main">
          <template v-if="draft.step === 1">
            <div class="week-nav">
              <button type="button" class="arrow" aria-label="Earlier days" :disabled="page === 0" @click="page--">
                <ChevronLeft :size="16" aria-hidden="true" />
              </button>
              <span class="range">{{ range }}</span>
              <button type="button" class="arrow" aria-label="Later days" @click="page++">
                <ChevronRight :size="16" aria-hidden="true" />
              </button>
            </div>
            <WeekTable
              :days="days"
              :hours="hours"
              :busy="busy"
              :holidays="holidays"
              :sessions="draft.sessions"
              :today="today"
              :now="now()"
              @add="add"
              @remove="removeSession"
            />
          </template>
          <p v-else class="st-empty">{{ STEPS[draft.step - 1] }}</p>
        </main>
        <SideCard
          :room="room"
          :sessions="draft.sessions"
          :holidays="holidays"
          :today="today"
          :tomorrow="tomorrow"
          :message="message"
          @remove="removeSession"
        >
          <template #actions>
            <button type="button" class="bf-btn quiet" @click="back">{{ draft.step === 1 ? 'Cancel' : 'Back' }}</button>
            <button type="button" class="bf-btn next" @click="go(draft.step + 1)">{{ nextLabel }}</button>
          </template>
        </SideCard>
      </div>
    </template>
  </section>
</template>

<style scoped>
.book-page {
  padding: 22px 28px 24px;
  overflow: hidden;
}
.bf-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 24px;
  margin-bottom: 18px;
}
.bf-head h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.025em;
}
.bf {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 20px;
  min-height: 0;
}
.bf-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 16px 18px 18px;
  border-radius: 20px;
  background: var(--color-sheet);
  box-shadow: 0 10px 36px rgba(30, 22, 17, 0.06), 0 1px 4px rgba(30, 22, 17, 0.04);
}
.week-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.range {
  font-size: 14px;
  font-weight: 500;
}
.arrow {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 10px;
  background: var(--color-field-disabled);
  color: var(--color-ink);
  cursor: pointer;
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
.arrow:disabled {
  color: var(--color-ink-off);
  cursor: default;
}
.arrow:active:not(:disabled),
.bf-btn:active {
  transform: scale(0.97);
}
.bf-btn {
  flex: 1;
  height: 42px;
  padding: 0 16px;
  border: 0;
  border-radius: 12px;
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
.bf-btn.quiet {
  flex: none;
  background: var(--color-field-disabled);
  color: var(--color-ink);
}
.bf-btn.next {
  background: var(--color-crimson-fill);
  color: #fff;
}
@media (hover: hover) and (pointer: fine) {
  .bf-btn.next:hover {
    background: var(--color-crimson-deep);
  }
  .arrow:not(:disabled):hover,
  .bf-btn.quiet:hover {
    background: var(--color-rule);
  }
}
@media (max-width: 1000px) {
  .book-page {
    overflow: auto;
  }
  .bf {
    grid-template-columns: 1fr;
  }
  .bf-main {
    min-height: 520px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .arrow,
  .bf-btn {
    transition: none;
  }
}
</style>
