<script setup lang="ts">
// One IT list (spec 2026-11-05-owner-and-it-pages-design, Part B): a tab of the IT Lead's IT setup,
// or IT Staff's My tasks (`mine`, read only). Rows are grouped by setup day (Ready: by the day it
// was made ready), a row opens the panel, and the IT Lead assigns staff or marks a setup ready in
// the Ledger pop-up. The filters live in the address (`from`, `to`, `q`), shared with the page.
import { CircleAlert, Search } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { getBooking } from '../../api/bookings'
import { ApiError } from '../../api/errors'
import { assignStaff, listItStaff, listTicketPage, markReady } from '../../api/it'
import type { BookingDetail, ITStaffOut, ITTicketItem, RoomListItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import EmptyState from '../../components/list/EmptyState.vue'
import PagingFoot from '../../components/list/PagingFoot.vue'
import TableSkeleton from '../../components/list/TableSkeleton.vue'
import { usePanelParam } from '../../composables/usePanelParam'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { useResourceList } from '../../composables/useResourceList'
import { useToast } from '../../composables/useToast'
import { groupByDoneDay, groupBySetupDay, setupText, type ItTab } from '../../utils/itQueue'
import { formatDay } from '../../utils/time'
import BookingActionDialog from '../bookings/BookingActionDialog.vue'
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
const staff = ref<ITStaffOut[]>([])
const picked = ref<number[]>([])
const staffSearch = ref('')
const toast = useToast()

const shownStaff = computed(() => {
  const term = staffSearch.value.trim().toLowerCase()
  return term ? staff.value.filter((s) => `${s.name_en} ${s.name_kh}`.toLowerCase().includes(term)) : staff.value
})

async function ask(step: Step, ticket: ITTicketItem) {
  asking.value = { step, ticket }
  notes.value = ticket.technician_notes ?? ''
  askError.value = ''
  picked.value = ticket.staff.map((s) => s.id)
  staffSearch.value = ''
  if (step === 'assign' && !staff.value.length) {
    try {
      staff.value = (await listItStaff(api)).items
    } catch (err) {
      askError.value = err instanceof ApiError ? err.message : 'Could not load the IT Staff.'
    }
  }
}
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
        <ul class="rows">
          <ITRow
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
      :title="asking.step === 'assign' ? 'Assign IT Staff' : 'Mark this setup ready?'"
      :confirm-label="asking.step === 'assign' ? 'Save' : 'Mark ready'"
      field-label="Technician notes (optional)"
      :max="1000"
      :no-field="asking.step === 'ready'"
      :meeting="asking.ticket.booking.meeting_title"
      :reference="asking.ticket.booking.reference_code"
      :day="`${formatDay(asking.ticket.booking.first_session.date)} · ${setupText(asking.ticket)}`"
      :times="askTimes"
      :effect="
        asking.step === 'assign'
          ? 'Pick who sets it up. They see it in My tasks.'
          : 'The booking is confirmed and the booker gets the door pass.'
      "
      :busy="busy"
      :allowed="asking.step === 'ready' || picked.length > 0"
      :error="askError"
      @back="asking = null"
      @confirm="save"
    >
      <div v-if="asking.step === 'assign'" class="staff-pick">
        <label class="staff-search">
          <Search aria-hidden="true" />
          <input v-model="staffSearch" type="search" placeholder="Search IT Staff" aria-label="Search IT Staff" />
        </label>
        <ul class="staff-list" aria-label="IT Staff">
          <li v-for="s in shownStaff" :key="s.id">
            <label>
              <input type="checkbox" :checked="picked.includes(s.id)" :disabled="busy" @change="toggle(s.id)" />
              <span>{{ s.name_en }}</span>
              <span class="kh">{{ s.name_kh }}</span>
            </label>
          </li>
          <li v-if="!shownStaff.length" class="none">No IT Staff match.</li>
        </ul>
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
.rows {
  margin: 0;
  padding: 0;
  list-style: none;
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
.staff-list {
  max-height: 180px;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  border: 1px solid var(--color-rule);
  border-radius: 8px;
}
.staff-list li + li {
  border-top: 1px solid var(--color-rule);
}
.staff-list label {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  font-size: 13.5px;
  cursor: pointer;
}
.staff-list input {
  width: 16px;
  height: 16px;
  accent-color: var(--color-crimson);
}
.staff-list .kh {
  margin-left: auto;
  font-family: var(--font-kh);
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.staff-list .none {
  padding: 8px 10px;
  font-size: 13px;
  color: var(--color-ink-off);
}
</style>
