<script setup lang="ts">
// Book a room (Staff): four steps on the left, the side card on the right, no page scroll on a
// computer. Step 1 is the week table; the time picked on the room page arrives in the query.
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../../api'
import { getRoomSchedule } from '../../api/bookings'
import { uploadAttachment } from '../../api/attachments'
import { getRoom } from '../../api/rooms'
import type { ServiceOut } from '../../api/services'
import { ApiError } from '../../api/errors'
import { checkBooking, listActiveServices, listHolidays, sendBooking } from '../../api/staff'
import type { BookingCheckResult, BookingStep, PublicHolidayOut, RoomDetail, ScheduleItem } from '../../api/types'
import { useLiveRefresh } from '../../composables/useLiveRefresh'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { useToast } from '../../composables/useToast'
import { addDays, phnomPenhClock } from '../../utils/time'
import MeetingStep from './book/MeetingStep.vue'
import { meetingErrors, type MeetingErrors } from './book/meetingErrors'
import ReviewStep from './book/ReviewStep.vue'
import ServicesStep from './book/ServicesStep.vue'
import SideCard from './book/SideCard.vue'
import StepBar from './book/StepBar.vue'
import { useBookingDraft } from './book/useBookingDraft'
import WeekTable from './book/WeekTable.vue'
import { dayLabel, roomHours, toMin, daysFrom, type PickedSession } from './rules'
import './staff.css'

const STEPS = ['Schedule', 'Meeting details', 'Food & IT', 'Review']
const WEEK = 7

const route = useRoute()
const router = useRouter()
const today = usePhnomPenhToday()
const tomorrow = computed(() => addDays(today.value, 1))
const roomId = Number(route.params.roomId)

/**
 * The time picked before (the room page, or Find a room), when the query holds a whole one:
 * `date` for one day, or `dates` (a comma list, Find a room's "day to day") for several, with
 * `start` and `end` the same every day.
 */
function fromQuery(): PickedSession[] {
  const { date, dates, start, end } = route.query
  const list = typeof dates === 'string' ? dates.split(',') : typeof date === 'string' ? [date] : []
  if (typeof start !== 'string' || typeof end !== 'string') return []
  if (!/^\d{2}:\d{2}$/.test(start) || !/^\d{2}:\d{2}$/.test(end)) return []
  const a = toMin(start)
  const b = toMin(end)
  if (b <= a || !list.length || !list.every((d) => /^\d{4}-\d{2}-\d{2}$/.test(d))) return []
  return list.map((d) => ({ date: d, a, b }))
}
const picked = fromQuery()
const first = picked[0] ?? null
const { draft, addSession, removeSession, toCheckBody, toCreateBody } = useBookingDraft(roomId, picked)
const toast = useToast()

const room = ref<RoomDetail | null>(null)
const busy = ref<ScheduleItem[]>([])
const holidays = ref<PublicHolidayOut[]>([])
const foods = ref<ServiceOut[]>([])
const its = ref<ServiceOut[]>([])
const failed = ref(false)
const message = ref('')
const reached = ref(1)

const now = () => toMin(phnomPenhClock(new Date()))
const hours = computed(() => (room.value ? roomHours(room.value) : { open: 480, close: 1080 }))

// The week window: page 0 is the next 7 days from today (weekends too); the arrows move 7 days.
const firstPage = () => {
  if (!first) return 0
  const index = daysFrom(today.value, WEEK * 12).indexOf(first.date)
  return index < 0 ? 0 : Math.floor(index / WEEK)
}
const page = ref(firstPage())
const days = computed(() => daysFrom(today.value, WEEK * (page.value + 1)).slice(WEEK * page.value))
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
    // Food and IT lists are not needed for step 1: a failure leaves them empty, the booking goes on.
    const [f, i] = await Promise.all([
      listActiveServices(api, 'catering').catch(() => []),
      listActiveServices(api, 'it').catch(() => []),
    ])
    foods.value = f
    its.value = i
  } catch {
    failed.value = true
  }
})
watch(page, () => loadWeek().catch(() => (failed.value = true)))
// Quiet refresh: a time someone else just booked turns busy here with no click.
useLiveRefresh(() => (room.value ? loadWeek() : undefined))

function add(s: PickedSession) {
  addSession(s)
  message.value = ''
}

// Step 2 shows its errors once someone tried to leave it; they then follow the typing.
const tried = ref(false)
/** Messages the API gave for step 2 fields on send; they go once that step is left again. */
const serverErrors = ref<MeetingErrors>({})
const errors = computed<MeetingErrors>(() => ({
  ...(tried.value && room.value ? meetingErrors(draft, room.value) : {}),
  ...serverErrors.value,
}))

/** The step that owns an API field name, or null when no step does. */
function stepOfField(field: string): number | null {
  if (field.startsWith('sessions') || field === 'room_id') return 1
  if (/^(meeting_|attendees|participant_emails|private_justification)/.test(field)) return 2
  if (/^(catering|it)\b/.test(field)) return 3
  return null
}
const STEP_FIELDS: Record<string, keyof MeetingErrors> = {
  meeting_title: 'title',
  attendees: 'people',
  private_justification: 'justification',
}

function go(step: number) {
  if (step > 1 && draft.sessions.length === 0) {
    draft.step = 1
    message.value = 'Pick at least one time in the table.'
    return
  }
  if (step > 2 && room.value && Object.keys(meetingErrors(draft, room.value)).length) {
    tried.value = true
    draft.step = 2
    reached.value = Math.max(reached.value, 2)
    return
  }
  message.value = ''
  if (draft.step === 2) serverErrors.value = {}
  draft.step = step as 1 | 2 | 3 | 4
  reached.value = Math.max(reached.value, step)
}

// Step 4 asks the API first: its steps feed "After you send"; a problem keeps Send off.
const check = ref<BookingCheckResult | null>(null)
const checking = ref(false)
const sending = ref(false)
const problemStep = computed(() => {
  const fields = Object.keys(check.value?.problem?.fields ?? {})
  return fields.map(stepOfField).find((n) => n !== null) ?? null
})
watch(
  () => draft.step,
  async (step) => {
    if (step !== 4) return
    check.value = null
    checking.value = true
    try {
      check.value = await checkBooking(api, toCheckBody())
    } catch (error) {
      message.value = error instanceof ApiError ? error.message : 'The booking could not be checked.'
    } finally {
      checking.value = false
    }
  },
)
const PATH: Record<BookingStep, string> = {
  PITIKA: 'Pitika checks it',
  OWNER: 'The room owner checks it',
  IT_SETUP: 'IT gets the room ready',
  CONFIRMED: 'Confirmed',
}

/** The booking is sent; now its files, one by one. A file that fails never undoes the booking:
 *  the booker adds it again from My bookings. Returns how many failed. */
async function uploadFiles(bookingId: number): Promise<number> {
  let failed = 0
  for (const file of draft.files) {
    try {
      await uploadAttachment(api, bookingId, file)
    } catch {
      failed += 1
    }
  }
  return failed
}

async function send() {
  if (!room.value || sending.value) return
  sending.value = true
  message.value = ''
  try {
    const saved = await sendBooking(api, toCreateBody())
    const failed = await uploadFiles(saved.id)
    if (failed) toast.show(`Request sent. ${failed} file${failed === 1 ? '' : 's'} could not be added — add ${failed === 1 ? 'it' : 'them'} from My bookings.`)
    else toast.show(room.value.is_private ? 'Request sent. Pitika and the room owner check it next.' : 'Request sent. Pitika checks it next.')
    await router.push({ name: 'my-bookings' })
  } catch (error) {
    if (!(error instanceof ApiError)) {
      message.value = 'The request could not be sent. Try again.'
      return
    }
    // Back to the step that owns the field, with everything typed kept.
    const owned = Object.keys(error.fields)
      .map((field) => ({ field, step: stepOfField(field) }))
      .filter((x): x is { field: string; step: number } => x.step !== null)
    const target = owned.length ? Math.min(...owned.map((x) => x.step)) : null
    if (target === 2) {
      serverErrors.value = Object.fromEntries(
        owned.filter((x) => STEP_FIELDS[x.field]).map((x) => [STEP_FIELDS[x.field], error.fields[x.field]]),
      )
    }
    if (target) draft.step = target as 1 | 2 | 3
    message.value = target === 2 && Object.keys(serverErrors.value).length ? '' : error.message
    if (target === 1) loadWeek().catch(() => undefined)
  } finally {
    sending.value = false
  }
}
const sendOff = computed(() => draft.step === 4 && (checking.value || sending.value || !!check.value?.problem))
function next() {
  if (draft.step === 4) send()
  else go(draft.step + 1)
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
          <MeetingStep v-else-if="draft.step === 2" :draft="draft" :room="room" :errors="errors" />
          <ServicesStep v-else-if="draft.step === 3" :draft="draft" :foods="foods" :its="its" />
          <ReviewStep
            v-else
            :draft="draft"
            :room="room"
            :foods="foods"
            :its="its"
            :check="check"
            :problem-step="problemStep"
            @jump="go"
          />
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
          <div v-if="draft.step === 4" class="after">
            <h3>After you send</h3>
            <ol class="bf-path">
              <li class="on"><i />You send it<small>Now</small></li>
              <li v-for="s in check?.steps ?? []" :key="s"><i />{{ PATH[s] }}</li>
              <li class="end"><i />You can cancel any time before it starts</li>
            </ol>
            <p v-if="checking" class="checking">Checking…</p>
          </div>
          <template #actions>
            <button type="button" class="bf-btn quiet" @click="back">{{ draft.step === 1 ? 'Cancel' : 'Back' }}</button>
            <button type="button" class="bf-btn next" :disabled="sendOff" @click="next">{{ nextLabel }}</button>
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
.bf-btn.next:disabled {
  background: var(--color-rule-strong);
  cursor: not-allowed;
  transform: none;
}
.after {
  margin-top: 18px;
}
.after h3 {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
}
.bf-path {
  margin: 0;
  padding: 0;
  list-style: none;
}
.bf-path li {
  position: relative;
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 0 0 14px 22px;
  font-size: 13.5px;
}
.bf-path li::before {
  content: '';
  position: absolute;
  top: 10px;
  bottom: -2px;
  left: 5px;
  width: 1.5px;
  background: var(--color-rule);
}
.bf-path li:last-child::before {
  display: none;
}
.bf-path i {
  position: absolute;
  top: 5px;
  left: 1px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-sheet);
  box-shadow: inset 0 0 0 1.5px var(--color-rule-strong);
}
.bf-path li.on i {
  background: var(--color-crimson-fill);
  box-shadow: none;
}
.bf-path li.end {
  color: var(--color-intaglio);
}
.bf-path small {
  margin-left: auto;
  color: var(--color-ink-off);
  font-size: 12px;
}
.checking {
  margin: 0;
  color: var(--color-ink-off);
  font-size: 13px;
}
@media (hover: hover) and (pointer: fine) {
  .bf-btn.next:not(:disabled):hover {
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
