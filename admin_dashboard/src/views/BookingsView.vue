<script setup lang="ts">
// Bookings (DSH-B01, B-32): every booking. A filtered, paged list; the open booking lives in the
// address (?id=12), so a reload keeps its panel open. The Admin's only changes are the actions
// in the booking panel (cancel, and approve or reject as backup reviewer, B-33/B-34).
import { CircleAlert, Ellipsis, LoaderCircle, Monitor, Utensils } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import { api } from '../api'
import { getBooking, listBookingPage, listPitikaBookingPage, type BookingFilters as BookingFilterParams } from '../api/bookings'
import type { BookingDetail, BookingListItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import EmptyState from '../components/list/EmptyState.vue'
import PagingFoot from '../components/list/PagingFoot.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { usePanelParam } from '../composables/usePanelParam'
import { usePanelRecord } from '../composables/usePanelRecord'
import { useResourceList } from '../composables/useResourceList'
import { useSessionStore } from '../stores/session'
import { MEETING_TYPE_LABELS, statusLabel } from '../utils/bookingLabels'
import { formatDay } from '../utils/time'
import BookingFilters from './bookings/BookingFilters.vue'
import BookingPanel from './bookings/BookingPanel.vue'
import { BOOKING_FILTERS } from './bookings/bookingFilters'

// A Pitika (not also Admin) sees the bookings of their province, read only.
const pitikaOnly = useSessionStore().pitikaOnly
const { list, result, loading, error, errorFields, filtered, load, refresh } = useResourceList<BookingListItem>(
  BOOKING_FILTERS,
  (params) => (pitikaOnly ? listPitikaBookingPage : listBookingPage)(api, params as BookingFilterParams),
  { activeFilter: false },
)
const panel = usePanelParam()
// The booking is loaded before its panel opens (see usePanelRecord), so a reload on ?id=… works too.
const { record: openBooking, error: openError, openingId, load: loadOpen } = usePanelRecord(panel.id, (id) =>
  getBooking(api, id),
)

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'booking' : 'bookings'}`)
const words = ref<string[]>([])
const fieldMessages = computed(() => Object.values(errorFields.value))

const hhmm = (time: string) => time.slice(0, 5)

/** After an Admin action: the panel shows the new booking, the list reloads and tints its row. */
async function onChanged(booking: BookingDetail) {
  openBooking.value = booking
  await refresh(booking.id)
}

const SKELETON_COLUMNS = ['120px', '2fr', '2fr', '1fr', '1.5fr', '1fr', '56px', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Bookings</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
    </div>

    <BookingFilters :province-filter="!pitikaOnly" @summary="words = $event" />

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>Booking {{ panel.id.value }}: {{ openError }}</b>
        <BaseButton variant="quiet" @click="loadOpen">Try again</BaseButton>
        <BaseButton variant="quiet" @click="panel.close">Close</BaseButton>
      </div>
    </div>

    <div class="sheet">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <span v-for="message in fieldMessages" :key="message" class="field-message">{{ message }}</span>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
          <BaseButton v-if="filtered" variant="quiet" @click="list.reset()">Clear filters</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && !result" :columns="SKELETON_COLUMNS" />
      <template v-else-if="result && !result.items.length">
        <EmptyState v-if="filtered" filtered title="No bookings match" :text="`Nothing matches ${words.join(', ')}.`">
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No bookings yet" text="Bookings show here once people send them." />
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Bookings</caption>
          <thead>
            <tr>
              <th scope="col">Reference</th>
              <th scope="col">Meeting</th>
              <th scope="col">Room</th>
              <th scope="col">Booker</th>
              <th scope="col">First session</th>
              <th scope="col">Status</th>
              <th scope="col"><span class="sr-only">Services</span></th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="booking in result.items"
              :key="booking.id"
              :aria-busy="booking.id === openingId || undefined"
              tabindex="0"
              @click="panel.open(booking.id)"
              @keydown.enter="panel.open(booking.id)"
            >
              <td class="mono ref">{{ booking.reference_code }}</td>
              <td>
                <span class="title">{{ booking.meeting_title }}</span>
                <span class="sub">{{ MEETING_TYPE_LABELS[booking.meeting_type] ?? booking.meeting_type }}</span>
              </td>
              <td>
                <span class="kh">{{ booking.room.name_kh }}</span>
                <span class="en">{{ booking.room.name_en }}</span>
                <span class="sub">{{ booking.room.location.name_en }}</span>
              </td>
              <td>{{ booking.requester.name_en }}</td>
              <td class="when">
                <span>{{ formatDay(booking.first_session.date) }}</span>
                <span class="sub mono">
                  {{ hhmm(booking.first_session.start_time) }}–{{ hhmm(booking.first_session.end_time) }}
                  <template v-if="booking.session_count > 1"> +{{ booking.session_count - 1 }} more</template>
                </span>
              </td>
              <td class="status">{{ statusLabel(booking.display_status) }}</td>
              <td class="services">
                <Utensils v-if="booking.has_catering" aria-label="Food ordered" role="img" />
                <Monitor v-if="booking.has_it" aria-label="IT help asked" role="img" />
              </td>
              <td class="row-actions">
                <button
                  type="button"
                  class="icon-btn"
                  :aria-label="`Open ${booking.reference_code}`"
                  @click.stop="panel.open(booking.id)"
                >
                  <LoaderCircle v-if="booking.id === openingId" class="spin" aria-hidden="true" />
                  <Ellipsis v-else aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <BookingPanel
      v-if="openBooking"
      :key="`booking-${openBooking.id}`"
      :booking="openBooking"
      :admin-actions="!pitikaOnly"
      @close="panel.close"
      @changed="onChanged"
    />

    <PagingFoot
      v-if="result && total > 0"
      :page="list.page.value"
      :size="list.size.value"
      :total="total"
      @update:page="list.page.value = $event"
      @update:size="list.size.value = $event"
    />
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.ref {
  white-space: nowrap;
}
td .title,
td .kh,
td .en,
td .sub,
.when span {
  display: block;
}
.title {
  font-weight: 500;
}
.kh {
  font-family: var(--font-kh);
}
.sub {
  font-size: 12px;
  color: var(--color-ink-off);
}
.when,
.status {
  white-space: nowrap;
}
.services {
  white-space: nowrap;
  color: var(--color-ink-off);
}
.services svg {
  width: 16px;
  height: 16px;
  margin-right: 4px;
}
.field-message {
  display: block;
  font-size: 12.5px;
}
</style>
