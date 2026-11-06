<script setup lang="ts">
// One IT list (spec 2026-11-05-owner-and-it-pages-design, Part B): a tab of the IT Lead's IT setup,
// or IT Staff's My tasks (`mine`, read only). Rows are grouped by setup day (Ready: by the day it
// was made ready), a row opens the panel, and the IT Lead assigns staff or marks a setup ready in
// the Ledger pop-up. The filters live in the address (`from`, `to`, `q`), shared with the page.
import { CircleAlert, Plus, Search, UserPlus } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { getBooking } from '../../api/bookings'
import { ApiError } from '../../api/errors'
import { assignStaff, listItStaff, listTicketPage, markReady } from '../../api/it'
import type { BookingDetail, ITTicketItem, RoomListItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import StaffAvatar from '../../components/StaffAvatar.vue'
import EmptyState from '../../components/list/EmptyState.vue'
import PagingFoot from '../../components/list/PagingFoot.vue'
import TableSkeleton from '../../components/list/TableSkeleton.vue'
import { usePanelParam } from '../../composables/usePanelParam'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { useResourceList } from '../../composables/useResourceList'
import { useToast } from '../../composables/useToast'
import { useUiStore } from '../../stores/ui'
import { groupByDoneDay, groupBySetupDay, itItemIcon, setupText, type ItTab } from '../../utils/itQueue'
import { formatDay } from '../../utils/time'
import BookingActionDialog from '../bookings/BookingActionDialog.vue'
import ITCard from './ITCard.vue'
import ITPanel from './ITPanel.vue'
import ITRow from './ITRow.vue'

const props = defineProps<{
  /** A tab of IT setup, or `mine`: my tasks (assigned to me, not ready). */
  tab: ItTab | 'mine'
  rooms: RoomListItem[]
  /** false: read only (My tasks). */
  actions: boolean
}>()
const emit = defineEmits<{ changed: []; loaded: [items: ITTicketItem[], total: number] }>()

const paged = props.tab === 'ready'
const STATE = { to_assign: 'to_assign', in_progress: 'in_progress', ready: 'done', mine: 'in_progress' } as const
const { list, result, loading, error, filtered, load } = useResourceList<ITTicketItem>(
  { from: 'string', to: 'string', q: 'string' },
  // To assign, In progress and My tasks on one page (short, grouped); Ready is paged.
  (params) =>
    listTicketPage(api, {
      state: STATE[props.tab],
      mine: props.tab === 'mine',
      from: params.from as string | undefined,
      to: params.to as string | undefined,
      q: params.q as string | undefined,
      page: paged ? (params.page as number) : 1,
      size: paged ? (params.size as number) : 100,
    }),
  { activeFilter: false, paged },
)
const items = computed(() => result.value?.items ?? [])
watch(result, (r) => r && emit('loaded', r.items, r.total))

// Rows (a time line) or Cards (photo cards): the switch on the page, kept in this browser.
const ui = useUiStore()

const today = usePhnomPenhToday()
const now = ref(new Date())
let tick: ReturnType<typeof setInterval> | undefined
onMounted(() => (tick = setInterval(() => (now.value = new Date()), 60_000)))
onBeforeUnmount(() => clearInterval(tick))

const groups = computed(() =>
  props.tab === 'ready'
    ? groupByDoneDay(items.value, today.value).map((g) => ({ ...g, today: false }))
    : groupBySetupDay(items.value, today.value).map((g) => ({ ...g, today: g.key === 'today' })),
)

// Where the room is, and its photo, from the rooms list (no extra call per row).
const roomOf = (id: number) => props.rooms.find((r) => r.id === id) ?? null
const placeOf = (t: ITTicketItem) => {
  const r = roomOf(t.booking.room.id)
  return r ? `${r.location.name_en} · ${r.building.name_en} · ${r.floor.floor_label}` : null
}
const thumbOf = (t: ITTicketItem) => roomOf(t.booking.room.id)?.cover_photo?.thumbnail_url ?? null
const photoOf = (t: ITTicketItem) => roomOf(t.booking.room.id)?.cover_photo?.url ?? null

const EMPTY: Record<ItTab | 'mine', [string, string]> = {
  to_assign: ['Nothing to assign', 'New IT setups show here once the bookings are approved.'],
  in_progress: ['Nothing in progress', 'Setups with staff assigned show here.'],
  ready: ['Nothing ready yet', 'Setups marked ready, and missed ones, show here.'],
  mine: ['Nothing to set up', 'Setups assigned to you show here.'],
}

// --- The panel (the open ticket lives in the address, ?id=5) --------------------------------
const panel = usePanelParam()
const openTicket = computed(() => items.value.find((t) => t.id === panel.id.value) ?? null)
const detail = ref<BookingDetail | null>(null)
let latest = 0
watch(
  openTicket,
  async (t) => {
    const request = ++latest
    detail.value = null
    if (!t) return
    try {
      const answer = await getBooking(api, t.booking.id)
      if (request === latest) detail.value = answer
    } catch {
      // the panel still shows the setup; only the process bar is left out
    }
  },
  { immediate: true },
)

// --- Assign staff and mark ready (the Ledger pop-up) ----------------------------------------
type Step = 'assign' | 'ready'
const asking = ref<{ step: Step; ticket: ITTicketItem } | null>(null)
const notes = ref('')
const busy = ref(false)
const askError = ref('')
type StaffPick = Awaited<ReturnType<typeof listItStaff>>['items'][number]
const staff = ref<StaffPick[]>([])
const picked = ref<number[]>([])
const staffSearch = ref('')
/** The note box shows when asked, or at once when the setup already has a note. */
const noteOpen = ref(false)
const toast = useToast()

const shownStaff = computed(() => {
  const term = staffSearch.value.trim().toLowerCase()
  return term ? staff.value.filter((s) => `${s.name_en} ${s.name_kh}`.toLowerCase().includes(term)) : staff.value
})

async function ask(step: Step, ticket: ITTicketItem) {
  asking.value = { step, ticket }
  notes.value = ticket.technician_notes ?? ''
  noteOpen.value = !!ticket.technician_notes
  askError.value = ''
  picked.value = ticket.staff.map((s) => s.id)
  staffSearch.value = ''
  if (step === 'assign') {
    // Asked each time: how busy each person is depends on the setup's day.
    staff.value = []
    try {
      staff.value = (await listItStaff(api, ticket.booking.first_session.date)).items
    } catch (err) {
      askError.value = err instanceof ApiError ? err.message : 'Could not load the IT Staff.'
    }
  }
}
/** Their other setups that day: this one is left out when they are already on it. */
function loadText(s: StaffPick): string | null {
  if (s.setups_that_day == null || !asking.value) return null
  const others = s.setups_that_day - (asking.value.ticket.staff.some((x) => x.id === s.id) ? 1 : 0)
  if (others <= 0) return 'Free that day'
  return `${others} other ${others === 1 ? 'setup' : 'setups'} that day`
}
const askNeeds = computed(() =>
  (asking.value?.ticket.items ?? []).map((item) => {
    const name = String((item as Record<string, unknown>).name)
    return { name, ...itItemIcon(name) }
  }),
)
const assignLabel = computed(() => (picked.value.length ? `Assign ${picked.value.length} staff` : 'Assign staff'))
function toggle(id: number) {
  picked.value = picked.value.includes(id) ? picked.value.filter((x) => x !== id) : [...picked.value, id]
}
const askTimes = computed(() => {
  const b = asking.value?.ticket.booking
  return b ? `${b.first_session.start_time.slice(0, 5)}–${b.first_session.end_time.slice(0, 5)}` : ''
})

async function save() {
  if (!asking.value) return
  const { step, ticket } = asking.value
  const version = ticket.booking.version
  busy.value = true
  askError.value = ''
  try {
    if (step === 'assign') {
      // In the order of the list, so the same choice always sends the same body.
      const ids = staff.value.map((s) => s.id).filter((id) => picked.value.includes(id))
      await assignStaff(api, ticket.id, { user_ids: ids, technician_notes: notes.value.trim() || null, version })
      toast.show(`${ticket.booking.reference_code} staff assigned`, ticket.booking.meeting_title)
    } else {
      await markReady(api, ticket.id, { version })
      toast.show(`${ticket.booking.reference_code} ready`, ticket.booking.meeting_title)
    }
    asking.value = null
    if (step === 'ready' && panel.id.value === ticket.id) panel.close()
    await load()
    emit('changed')
  } catch (err) {
    askError.value = err instanceof ApiError ? err.message : 'Something went wrong.'
    // Changed by someone else, or a staff member was turned off: show the list as it is now.
    if (err instanceof ApiError && [403, 404, 409].includes(err.status)) {
      await load()
      emit('changed')
    }
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="queue">
    <div v-if="error" class="load-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ error }}</b>
        <BaseButton variant="quiet" @click="load">Try again</BaseButton>
      </div>
    </div>
    <TableSkeleton v-else-if="loading && !result" :columns="['168px', '2fr', '220px']" />
    <EmptyState
      v-else-if="result && !items.length"
      :filtered="filtered"
      :title="filtered ? 'No setups match' : EMPTY[tab][0]"
      :text="filtered ? 'Nothing here matches these filters.' : EMPTY[tab][1]"
    >
      <BaseButton v-if="filtered" @click="list.reset()">Clear filters</BaseButton>
    </EmptyState>
    <template v-else-if="result">
      <section v-for="group in groups" :key="group.key" :aria-labelledby="`group-${group.key}`">
        <div class="group-head" :class="{ today: group.today }">
          <h2 :id="`group-${group.key}`">{{ group.label }}</h2>
          <span class="n mono">{{ group.items.length }}</span>
        </div>
        <ul :class="ui.itView === 'cards' ? 'cards' : 'timeline'">
          <component
            :is="ui.itView === 'cards' ? ITCard : ITRow"
            v-for="t in group.items"
            :key="t.id"
            :ticket="t"
            :photo="thumbOf(t)"
            :place="placeOf(t)"
            :now="now"
            :today="today"
            :actions="actions"
            :current="panel.id.value === t.id"
            @open="panel.open(t.id)"
            @assign="ask('assign', t)"
            @ready="ask('ready', t)"
          />
        </ul>
      </section>
      <PagingFoot
        v-if="paged && result.total > list.size.value"
        :page="list.page.value"
        :size="list.size.value"
        :total="result.total"
        @update:page="list.page.value = $event"
        @update:size="list.size.value = $event"
      />
    </template>

    <ITPanel
      v-if="openTicket"
      :key="`it-${openTicket.id}`"
      :ticket="openTicket"
      :detail="detail"
      :photo="photoOf(openTicket)"
      :place="placeOf(openTicket)"
      :actions="actions"
      @close="panel.close"
      @assign="ask('assign', openTicket)"
      @ready="ask('ready', openTicket)"
    />

    <BookingActionDialog
      v-if="asking"
      v-model="notes"
      action="approve"
      :icon="asking.step === 'assign' ? UserPlus : undefined"
      :title="asking.step === 'assign' ? 'Assign IT Staff' : 'Mark this setup ready?'"
      :confirm-label="asking.step === 'assign' ? assignLabel : 'Mark ready'"
      field-label="Technician notes (optional)"
      :max="1000"
      :no-field="true"
      :meeting="asking.ticket.booking.meeting_title"
      :reference="asking.ticket.booking.reference_code"
      :day="`${formatDay(asking.ticket.booking.first_session.date)} · ${setupText(asking.ticket)}`"
      :times="askTimes"
      :effect="asking.step === 'assign' ? 'They see it in My tasks.' : 'The booking is confirmed and the booker gets the door pass.'"
      :busy="busy"
      :allowed="asking.step === 'ready' || picked.length > 0"
      :error="askError"
      @back="asking = null"
      @confirm="save"
    >
      <template v-if="asking.step === 'assign'" #summary>
        <div class="room-box">
          <RoomPhoto class="room-thumb" :path="thumbOf(asking.ticket)" :alt="asking.ticket.booking.room.name_en" />
          <div class="room-text">
            <b>{{ asking.ticket.booking.meeting_title }}</b>
            <span>
              {{ asking.ticket.booking.room.name_en }} · {{ formatDay(asking.ticket.setup_date).slice(0, -5) }} · set up by
              <span class="mono">{{ asking.ticket.setup_time.slice(0, 5) }}</span>
            </span>
            <span class="room-needs">
              <span v-for="n in askNeeds" :key="n.name"><component :is="n.icon" aria-hidden="true" />{{ n.name }}</span>
            </span>
          </div>
        </div>
      </template>
      <template v-if="asking.step === 'assign'" #foot-start>
        <span class="picked"><span class="mono">{{ picked.length }}</span> picked</span>
      </template>

      <div v-if="asking.step === 'assign'" class="staff-pick">
        <label class="staff-search">
          <Search aria-hidden="true" />
          <input v-model="staffSearch" type="search" placeholder="Search IT Staff" aria-label="Search IT Staff" />
        </label>
        <ul class="staff-list" aria-label="IT Staff">
          <li v-for="s in shownStaff" :key="s.id">
            <label class="staff-row" :class="{ on: picked.includes(s.id) }">
              <StaffAvatar :name="s.name_en" :photo="s.avatar_url" :size="36" />
              <span class="names">
                <span class="en">{{ s.name_en }}</span>
                <span class="kh">{{ s.name_kh }}</span>
              </span>
              <span v-if="loadText(s)" class="load" :class="{ free: loadText(s) === 'Free that day' }">{{ loadText(s) }}</span>
              <input type="checkbox" :checked="picked.includes(s.id)" :disabled="busy" @change="toggle(s.id)" />
            </label>
          </li>
          <li v-if="!shownStaff.length" class="none">No IT Staff match.</li>
        </ul>
        <button v-if="!noteOpen" type="button" class="add-note" @click="noteOpen = true">
          <Plus aria-hidden="true" />Add a note for staff
        </button>
        <label v-else class="note-field">
          <span>Note for staff <em>optional</em></span>
          <textarea v-model="notes" rows="2" maxlength="1000" :disabled="busy" />
        </label>
      </div>
    </BookingActionDialog>
  </div>
</template>

<style scoped>
.queue {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-top: 1px solid var(--color-rule-strong);
}
.group-head {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 14px 12px 8px;
  border-bottom: 1px solid var(--color-rule-strong);
  background: var(--color-paper);
}
.group-head h2 {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-intaglio);
}
.group-head .n {
  font-size: 11px;
  color: var(--color-intaglio);
}
.group-head.today {
  border-bottom-color: transparent;
  box-shadow: inset 0 -2px 0 var(--color-crimson);
}
.group-head.today h2,
.group-head.today .n {
  color: var(--color-crimson);
}
.timeline,
.cards {
  margin: 0;
  padding: 0;
  list-style: none;
}
.timeline {
  padding: 8px 0 12px;
}
/* Photo cards (owner pick, 6 Nov 2026: Cards view): as many 300px+ columns as fit. */
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(300px, 100%), 1fr));
  gap: 16px;
  padding: 16px 12px 20px;
}
.mono {
  font-family: var(--font-mono);
}
.load-error {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  color: var(--color-crimson);
}
.load-error :deep(svg.lucide) {
  flex: none;
  width: 18px;
  height: 18px;
}
.staff-pick {
  display: grid;
  gap: 8px;
  /* Inside the pop-up's 24px sides, like the booking table and the notes box. */
  margin: 16px 24px 0;
}
.staff-search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-sheet);
}
.staff-search :deep(svg.lucide) {
  width: 15px;
  height: 15px;
  color: var(--color-intaglio);
}
.staff-search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font: inherit;
  font-size: 13.5px;
}
/* The assign pop-up (owner pick, 6 Nov 2026: demo 1, "Avatar list"). */
.room-box {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 24px 0;
  padding: 10px;
  border-radius: 10px;
  background: var(--color-paper);
}
.room-thumb {
  flex: none;
  width: 56px;
  height: 56px;
  border-radius: 8px;
}
.room-text {
  display: grid;
  gap: 1px;
  min-width: 0;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.room-text b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-ink);
}
.room-needs {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 10px;
  margin-top: 2px;
  font-size: 12px;
  color: var(--color-ink);
}
.room-needs > span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.room-needs :deep(svg.lucide) {
  width: 13px;
  height: 13px;
}
.staff-list {
  max-height: 236px;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  border: 1px solid var(--color-rule);
  border-radius: 10px;
}
.staff-list li + li {
  border-top: 1px solid var(--color-rule);
}
.staff-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 120ms ease;
}
.staff-row:hover {
  background: var(--color-row-hover);
}
.staff-row.on {
  background: var(--color-crimson-wash);
}
.names {
  display: grid;
  flex: 1;
  min-width: 0;
}
.names .en {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
}
.names .kh {
  font-family: var(--font-kh);
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.load {
  flex: none;
  font-size: 12px;
  color: var(--color-intaglio);
}
.load.free {
  color: var(--color-ok);
}
.staff-row input {
  flex: none;
  width: 18px;
  height: 18px;
  margin: 0;
  accent-color: var(--color-crimson);
}
/* A phone: the "other setups" line goes under the names, so the names keep their width. */
@media (max-width: 520px) {
  .staff-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    column-gap: 12px;
  }
  .staff-row > :first-child {
    grid-row: span 2;
  }
  .load {
    grid-column: 2;
    grid-row: 2;
  }
  .staff-row input {
    grid-column: 3;
    grid-row: 1 / span 2;
  }
}
.staff-list .none {
  padding: 8px 10px;
  font-size: 13px;
  color: var(--color-ink-off);
}
.add-note {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  gap: 6px;
  margin-top: 4px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-crimson);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.add-note :deep(svg.lucide) {
  width: 15px;
  height: 15px;
}
.note-field {
  display: grid;
  gap: 6px;
  margin-top: 4px;
  font-size: 12.5px;
  font-weight: 500;
}
.note-field em {
  float: right;
  font-style: normal;
  font-weight: 400;
  color: var(--color-intaglio);
}
.note-field textarea {
  min-height: 60px;
  padding: 8px 10px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-sheet);
  font: inherit;
  font-size: 14px;
  font-weight: 400;
  resize: vertical;
}
.note-field textarea:focus {
  border-color: var(--color-crimson);
  outline: none;
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.12);
}
.picked {
  align-self: center;
  margin-right: auto;
  font-size: 13px;
  color: var(--color-intaglio);
}
</style>
