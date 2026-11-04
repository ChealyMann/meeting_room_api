<script setup lang="ts">
// A room's bookings, one week at a time (GET /rooms/{id}/schedule). Read only. Times are
// already Phnom Penh time. A private session the viewer may not see comes masked: no booking,
// no booker, only "Reserved (Private Session)".
import { ChevronLeft, ChevronRight, CircleAlert, Lock } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import { api } from '../../api'
import { getRoomSchedule } from '../../api/bookings'
import { ApiError } from '../../api/errors'
import type { ScheduleItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import { statusLabel } from '../../utils/bookingLabels'
import { addDays, formatDay, phnomPenhDate } from '../../utils/time'

const props = defineProps<{ roomId: number }>()

const thisWeek = phnomPenhDate(new Date())
const from = ref(thisWeek)
const to = computed(() => addDays(from.value, 6))

const items = ref<ScheduleItem[] | null>(null)
const error = ref('')
const loading = ref(false)
let latest = 0

async function load() {
  const request = ++latest
  loading.value = true
  error.value = ''
  try {
    const answer = await getRoomSchedule(api, props.roomId, from.value, to.value)
    if (request === latest) items.value = answer.items
  } catch (err) {
    if (request === latest) error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    if (request === latest) loading.value = false
  }
}
watch(from, load, { immediate: true })

/** The sessions by day, in the API's order (date, then start). */
const days = computed(() => {
  const groups: Array<{ date: string; items: ScheduleItem[] }> = []
  for (const item of items.value ?? []) {
    const last = groups[groups.length - 1]
    if (last?.date === item.date) last.items.push(item)
    else groups.push({ date: item.date, items: [item] })
  }
  return groups
})

const hhmm = (time: string) => time.slice(0, 5)
</script>

<template>
  <div class="schedule">
    <div class="week">
      <span class="range">{{ formatDay(from) }} – {{ formatDay(to) }}</span>
      <div class="moves">
        <BaseButton variant="quiet" class="small" @click="from = addDays(from, -7)">
          <ChevronLeft aria-hidden="true" />
          Previous week
        </BaseButton>
        <BaseButton variant="quiet" class="small" :disabled="from === thisWeek" @click="from = thisWeek">This week</BaseButton>
        <BaseButton variant="quiet" class="small" @click="from = addDays(from, 7)">
          Next week
          <ChevronRight aria-hidden="true" />
        </BaseButton>
      </div>
    </div>

    <div v-if="error" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ error }}</b>
        <BaseButton variant="quiet" @click="load">Try again</BaseButton>
      </div>
    </div>
    <p v-else-if="items && !items.length" class="empty">No bookings this week.</p>
    <div v-else-if="items" :aria-busy="loading || undefined">
      <section v-for="group in days" :key="group.date" class="day">
        <h4>{{ formatDay(group.date) }}</h4>
        <ul>
          <li v-for="(item, i) in group.items" :key="`${item.start_time}-${i}`" :class="{ masked: item.is_masked }">
            <span class="mono time">{{ hhmm(item.start_time) }}–{{ hhmm(item.end_time) }}</span>
            <span class="what">
              <span class="title">
                <Lock v-if="item.is_masked" class="lock" aria-hidden="true" />
                <RouterLink v-if="item.booking_id" class="link" :to="{ name: 'bookings', query: { id: String(item.booking_id) } }">
                  {{ item.title }}
                </RouterLink>
                <template v-else>{{ item.title }}</template>
              </span>
              <span v-if="!item.is_masked" class="meta">
                <span class="mono">{{ item.reference_code }}</span>
                <span v-if="item.requester_name">{{ item.requester_name }}</span>
              </span>
            </span>
            <span class="status">{{ statusLabel(item.status) }}</span>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.schedule {
  display: grid;
  gap: 16px;
}
.week {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.range {
  font-size: 13px;
  font-weight: 500;
}
.moves {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.empty {
  margin: 0;
  font-size: 13px;
  color: var(--color-ink-off);
}
.day + .day {
  margin-top: 16px;
}
h4 {
  margin: 0 0 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-ink-off);
}
ul {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--color-rule);
}
li {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: baseline;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-rule);
  font-size: 13px;
}
.time {
  font-size: 12.5px;
}
.what {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  overflow-wrap: anywhere;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  font-size: 12px;
  color: var(--color-ink-off);
}
.link {
  color: inherit;
}
.link:hover {
  color: var(--color-crimson);
}
.masked .title {
  font-weight: 400;
  color: var(--color-ink-off);
}
.lock {
  width: 14px;
  height: 14px;
}
.status {
  font-size: 12px;
  white-space: nowrap;
}
</style>
