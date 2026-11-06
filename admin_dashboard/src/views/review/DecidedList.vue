<script setup lang="ts">
// The Approved and Rejected tabs of To review (spec 2026-11-05-pitika-decided-design): the
// bookings this reviewer decided, under decision days, newest first, as the same soft rows as the
// Waiting tab (owner decision, 6 Nov 2026): the meeting time, the photo with the reference, the
// note as a tag, then my decision with its time and where the booking is now. Read only: a row
// opens the review panel with only Close.
import { Check, CircleAlert, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import { api } from '../../api'
import { getBooking } from '../../api/bookings'
import type { BookingDetail, DecidedBookingItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import EmptyState from '../../components/list/EmptyState.vue'
import PagingFoot from '../../components/list/PagingFoot.vue'
import SoftRow from '../../components/SoftRow.vue'
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
  /** Room id → its cover photo: the thumbnail for the row, full size for the panel's header. */
  covers: Record<number, { url: string; thumbnail_url: string } | null>
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
const hhmm = (time: string) => time.slice(0, 5)
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
        <ul class="rows">
          <SoftRow
            v-for="b in day.items"
            :key="b.id"
            :data-booking="b.id"
            :start="hhmm(b.first_session.start_time)"
            :end="hhmm(b.first_session.end_time)"
            :day="shortDay(b.first_session.date)"
            :more="b.session_count > 1 ? `+${b.session_count - 1} more` : null"
            :photo="covers[b.room.id]?.thumbnail_url ?? null"
            :photo-alt="b.room.name_en"
            :reference="b.reference_code"
            :title="b.meeting_title"
            :current="panel.id.value === b.id"
            @open="panel.open(b.id)"
          >
            <template #line>
              <span class="kh">{{ b.room.name_kh }}</span> · {{ b.room.name_en }} · {{ b.requester.name_en }}
            </template>
            <template v-if="note(b)" #tags>
              <span class="soft-tag note" :class="{ alert: decision === 'REJECTED' }" :title="b.decision_note ?? ''">{{ note(b) }}</span>
            </template>
            <template #status>
              <span class="mark" :class="decision === 'APPROVED' ? 'ok' : 'no'">
                <Check v-if="decision === 'APPROVED'" aria-hidden="true" />
                <X v-else aria-hidden="true" />{{ decision === 'APPROVED' ? 'Approved' : 'Rejected' }} ·
                <span class="decided-at mono">{{ decidedTime(b) }}</span>
              </span>
              <span class="now" :class="nowPill(b).tone">{{ nowPill(b).text }}</span>
            </template>
          </SoftRow>
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
.rows {
  margin: 0;
  padding: 0;
  list-style: none;
}
.kh {
  font-family: var(--font-kh);
  font-weight: 500;
  color: var(--color-ink);
}
/* My decision and its time, then where the booking is now: the row's status, at its end. */
.mark {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  font-weight: 500;
  white-space: nowrap;
}
.mark :deep(svg.lucide) {
  width: 14px;
  height: 14px;
}
.mark.ok {
  color: var(--color-ok);
}
.mark.no {
  color: var(--color-crimson);
}
.decided-at {
  font-weight: 400;
}
.now {
  padding: 3px 10px;
  border-radius: 999px;
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
</style>
