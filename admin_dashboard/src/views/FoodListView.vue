<script setup lang="ts">
// The day's food list (GET /pitika/catering, spec B-12): every food order of bookings in IT setup
// or confirmed whose first session is on that day. The Admin sees every province; nothing is
// changed here. The day lives in the address (?date=2026-11-04); none means today in Phnom Penh.
import { ChevronLeft, ChevronRight, CircleAlert } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import { getFoodList } from '../api/bookings'
import { ApiError } from '../api/errors'
import type { CateringOrderItem } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import EmptyState from '../components/list/EmptyState.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { usePhnomPenhToday } from '../composables/usePhnomPenhToday'
import { statusLabel } from '../utils/bookingLabels'
import { addDays, formatDay } from '../utils/time'

const route = useRoute()
const router = useRouter()

const DAY = /^\d{4}-\d{2}-\d{2}$/
// Kept current: a list left open past midnight (with no ?date) moves to the new day.
const today = usePhnomPenhToday()
const day = computed(() => {
  const value = route.query.date
  return typeof value === 'string' && DAY.test(value) ? value : today.value
})
function go(next: string) {
  void router.push({ query: next === today.value ? {} : { date: next } })
}

const items = ref<CateringOrderItem[] | null>(null)
const loading = ref(false)
const error = ref('')
let latest = 0

async function load() {
  const request = ++latest
  loading.value = true
  error.value = ''
  try {
    const answer = await getFoodList(api, day.value)
    if (request === latest) items.value = answer.items
  } catch (err) {
    if (request === latest) error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    if (request === latest) loading.value = false
  }
}
watch(day, load, { immediate: true })

const packages = (order: CateringOrderItem) => order.packages.map((p) => String(p.name)).join(', ')
const SKELETON_COLUMNS = ['64px', '2fr', '2fr', '64px', '2fr', '2fr', '2fr', '96px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Food list</h1>
      <span class="mono count">{{ formatDay(day) }}</span>
    </div>

    <div class="filters days">
      <BaseButton variant="quiet" @click="go(addDays(day, -1))">
        <ChevronLeft aria-hidden="true" />
        Previous day
      </BaseButton>
      <BaseButton variant="quiet" :disabled="day === today" @click="go(today)">Today</BaseButton>
      <BaseButton variant="quiet" @click="go(addDays(day, 1))">
        Next day
        <ChevronRight aria-hidden="true" />
      </BaseButton>
      <label class="pick">
        <span class="sr-only">Day</span>
        <input
          class="input mono"
          type="date"
          :value="day"
          @change="DAY.test(($event.target as HTMLInputElement).value) && go(($event.target as HTMLInputElement).value)"
        />
      </label>
    </div>

    <div class="sheet">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && !items" :columns="SKELETON_COLUMNS" />
      <EmptyState v-else-if="items && !items.length" title="No food orders on this day." text="Orders show here once Pitika approves the booking." />
      <div v-else-if="items" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Food orders on {{ formatDay(day) }}</caption>
          <thead>
            <tr>
              <th scope="col">Time</th>
              <th scope="col">Room</th>
              <th scope="col">Meeting</th>
              <th class="num" scope="col">Servings</th>
              <th scope="col">Packages</th>
              <th scope="col">Remarks</th>
              <th scope="col">Pitika notes</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in items" :key="order.booking_id">
              <td class="mono">{{ order.delivery_time.slice(0, 5) }}</td>
              <td>
                <span class="kh">{{ order.room.name_kh }}</span>
                <span class="en">{{ order.room.name_en }}</span>
                <span class="sub">{{ order.room.location.name_en }}</span>
              </td>
              <td>
                <RouterLink class="title link" :to="{ name: 'bookings', query: { id: String(order.booking_id) } }">
                  {{ order.meeting_title }}
                </RouterLink>
                <span class="sub mono">{{ order.reference_code }}</span>
              </td>
              <td class="num mono">{{ order.servings }}</td>
              <td>{{ packages(order) }}</td>
              <td class="notes" :class="{ none: !order.remarks }">{{ order.remarks || 'None' }}</td>
              <td class="notes" :class="{ none: !order.approver_notes }">{{ order.approver_notes || 'None' }}</td>
              <td class="status">{{ statusLabel(order.booking_status) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.days {
  align-items: center;
  gap: 4px;
}
.pick {
  margin-left: auto;
}
.pick .input {
  width: 160px;
}
td .kh,
td .en,
td .title,
td .sub {
  display: block;
}
.kh {
  font-family: var(--font-kh);
}
.title {
  font-weight: 500;
}
.link {
  color: inherit;
}
.link:hover {
  color: var(--color-crimson);
}
.sub {
  font-size: 12px;
  color: var(--color-ink-off);
}
.notes {
  max-width: 240px;
  overflow-wrap: anywhere;
  white-space: pre-line;
}
.notes.none {
  color: var(--color-ink-off);
}
.status {
  white-space: nowrap;
}
</style>
