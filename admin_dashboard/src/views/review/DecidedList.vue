<script setup lang="ts">
// The Approved and Rejected tabs of To review (spec 2026-11-05-pitika-decided-design): the
// bookings this Pitika decided, as soft cards under decision days, newest first, with where
// each booking is now. Read only: a card opens the review panel with only Close.
import { Check, CircleAlert, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import { api } from '../../api'
import { getBooking } from '../../api/bookings'
import type { BookingDetail, DecidedBookingItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import EmptyState from '../../components/list/EmptyState.vue'
import PagingFoot from '../../components/list/PagingFoot.vue'
import TableSkeleton from '../../components/list/TableSkeleton.vue'
import { usePanelParam } from '../../composables/usePanelParam'
import { usePhnomPenhToday } from '../../composables/usePhnomPenhToday'
import { useResourceList } from '../../composables/useResourceList'
import { decidedTime, groupByDecisionDay, nowPill } from '../../utils/decided'
import { formatDay } from '../../utils/time'
import ReviewPanel from '../bookings/ReviewPanel.vue'
import { REVIEWERS, type Reviewer } from './reviewers'

const props = defineProps<{
  /** Whose decisions: the Pitika's or the room owner's (defaults to the Pitika). */
  reviewer?: Reviewer
  decision: 'APPROVED' | 'REJECTED'
  /** Room id → its cover photo (full size), for the panel's header. */
  covers: Record<number, { url: string } | null>
}>()

// The same address keys as the Waiting list, so the page's one filter bar drives both.
const { list, result, loading, error, filtered, load } = useResourceList<DecidedBookingItem>(
  { room_id: 'int', from: 'string', to: 'string', q: 'string' },
  (params) =>
    (props.reviewer ?? REVIEWERS.pitika).decided({
      decision: props.decision,
      room_id: params.room_id as number | undefined,
      from: params.from as string | undefined,
      to: params.to as string | undefined,
      q: params.q as string | undefined,
      page: params.page as number,
      size: params.size as number,
    }),
  { activeFilter: false },
)
watch(() => props.decision, load)

const today = usePhnomPenhToday()
const items = computed(() => result.value?.items ?? [])
const days = computed(() => groupByDecisionDay(items.value, today.value))
const word = computed(() => (props.decision === 'APPROVED' ? 'approved' : 'rejected'))

/** "Tue 10 Nov 2026" → "Tue 10 Nov" this year. */
const shortDay = (day: string) => {
  const text = formatDay(day)
  return day.slice(0, 4) === today.value.slice(0, 4) ? text.slice(0, -5) : text
}
const meta = (b: DecidedBookingItem) =>
  `${b.room.name_en} · ${shortDay(b.first_session.date)}, ${b.first_session.start_time.slice(0, 5)} · ${b.requester.name_en}`
const note = (b: DecidedBookingItem) =>
  b.decision_note ? `${props.decision === 'REJECTED' ? 'Reason' : 'Notes'}: “${b.decision_note}”` : ''

// --- The read-only panel (the open booking lives in the address, ?id=12) ---------------------
const panel = usePanelParam()
const detail = ref<BookingDetail | null>(null)
let latest = 0
watch(
  () => panel.id.value,
  async (id) => {
    const request = ++latest
    detail.value = null
    if (id === null) return
    try {
      const answer = await getBooking(api, id)
      if (request === latest) detail.value = answer // an older answer that comes late is dropped
    } catch {
      if (request === latest) panel.close() // gone, or not this Pitika's: nothing to show
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="decided">
    <div v-if="error" class="load-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ error }}</b>
        <BaseButton variant="quiet" @click="load">Try again</BaseButton>
      </div>
    </div>
    <TableSkeleton v-else-if="loading && !result" :columns="['32px', '2fr', '160px']" />
    <EmptyState
      v-else-if="result && !items.length"
      :filtered="filtered"
      :title="filtered ? 'No bookings match' : decision === 'APPROVED' ? 'No approved bookings yet' : 'No rejected bookings'"
      :text="filtered ? 'Nothing you decided matches these filters.' : `Bookings you ${decision === 'APPROVED' ? 'approve' : 'reject'} show here.`"
    >
      <BaseButton v-if="filtered" @click="list.reset()">Clear filters</BaseButton>
    </EmptyState>
    <template v-else-if="result">
      <section v-for="day in days" :key="day.key" :aria-labelledby="`day-${day.key}`">
        <div class="day-head">
          <h2 :id="`day-${day.key}`">{{ day.label }}</h2>
          <span class="n mono">{{ day.items.length }} {{ word }}</span>
        </div>
        <ul class="cards" role="list">
          <li
            v-for="b in day.items"
            :key="b.id"
            class="card"
            role="listitem"
            tabindex="0"
            :data-booking="b.id"
            @click="panel.open(b.id)"
            @keydown.enter.prevent="panel.open(b.id)"
          >
            <span class="mark" :class="decision === 'APPROVED' ? 'ok' : 'no'" aria-hidden="true">
              <Check v-if="decision === 'APPROVED'" />
              <X v-else />
            </span>
            <div class="body">
              <div class="title">
                <span class="name">{{ b.meeting_title }}</span>
                <span class="ref mono">{{ b.reference_code }}</span>
              </div>
              <div class="meta">{{ meta(b) }}</div>
              <div v-if="note(b)" class="note">{{ note(b) }}</div>
            </div>
            <span class="now" :class="nowPill(b).tone">{{ nowPill(b).text }}</span>
            <span class="time mono">{{ decidedTime(b) }}</span>
          </li>
        </ul>
      </section>
      <PagingFoot
        v-if="result.total > list.size.value"
        :page="list.page.value"
        :size="list.size.value"
        :total="result.total"
        @update:page="list.page.value = $event"
        @update:size="list.size.value = $event"
      />
    </template>

    <ReviewPanel
      v-if="detail"
      :key="`decided-${detail.id}`"
      :booking="detail"
      :photo-path="covers[detail.room.id]?.url ?? null"
      :starts-in="null"
      :note="(reviewer ?? REVIEWERS.pitika).panelNote(detail)"
      read-only
      @close="panel.close"
    />
  </div>
</template>

<style scoped>
.decided {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 16px;
}
.day-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin: 18px 2px 8px;
}
.day-head h2 {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-ink-off);
}
.day-head .n {
  font-size: 11.5px;
  color: var(--color-ink-off);
}
.cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--color-sheet);
  box-shadow: 0 1px 2px rgba(42, 28, 19, 0.05);
  cursor: pointer;
  transition: box-shadow 0.15s ease;
}
.card:hover {
  box-shadow: 0 2px 8px rgba(42, 28, 19, 0.08);
}
.card:focus-visible {
  outline: 2px solid var(--color-thread);
  outline-offset: 2px;
}
.mark {
  display: grid;
  flex: none;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
}
.mark svg {
  width: 16px;
  height: 16px;
  stroke-width: 2.5;
}
.mark.ok {
  background: color-mix(in srgb, var(--color-ok) 12%, var(--color-sheet));
  color: var(--color-ok);
}
.mark.no {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.body {
  flex: 1;
  min-width: 0;
}
.title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
  font-weight: 500;
}
.name {
  overflow-wrap: anywhere;
}
.ref {
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--color-field-disabled);
  font-size: 11.5px;
  font-weight: 400;
  letter-spacing: 0.02em;
  color: var(--color-ink);
}
.meta,
.note {
  margin-top: 3px;
  font-size: 12px;
  color: var(--color-ink-off);
  overflow-wrap: anywhere;
}
.note {
  color: var(--color-intaglio);
}
.now {
  flex: none;
  padding: 4px 10px;
  border-radius: 20px;
  background: var(--color-field-disabled);
  font-size: 12px;
  color: var(--color-intaglio);
  white-space: nowrap;
}
.now.ok {
  background: color-mix(in srgb, var(--color-ok) 12%, var(--color-sheet));
  color: var(--color-ok);
}
.now.warn {
  background: color-mix(in srgb, var(--color-warn) 10%, var(--color-sheet));
  color: var(--color-warn);
}
.now.no {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.time {
  flex: none;
  width: 44px;
  font-size: 11.5px;
  text-align: right;
  color: var(--color-ink-off);
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
.load-error svg {
  flex: none;
  width: 18px;
  height: 18px;
}
@media (max-width: 640px) {
  .card {
    flex-wrap: wrap;
    gap: 10px 12px;
  }
  .body {
    flex-basis: calc(100% - 46px);
  }
  .now {
    margin-left: 46px;
  }
  .time {
    margin-left: auto;
  }
}
@media (prefers-reduced-motion: reduce) {
  .card {
    transition: none;
  }
}
</style>
