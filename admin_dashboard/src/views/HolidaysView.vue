<script setup lang="ts">
// Public holidays: the dates that give a booking a holiday warning, sorted by date and filtered
// by year. The open holiday lives in the address (?id=4, ?id=new), so a reload keeps the panel open.
import { CircleAlert, Ellipsis, LoaderCircle, Plus } from 'lucide-vue-next'
import { computed } from 'vue'

import { api } from '../api'
import { getHoliday, listHolidayPage, type HolidayFilters } from '../api/holidays'
import type { PublicHolidayOut } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import EmptyState from '../components/list/EmptyState.vue'
import PagingFoot from '../components/list/PagingFoot.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { usePanelParam } from '../composables/usePanelParam'
import { usePanelRecord } from '../composables/usePanelRecord'
import { useResourceList } from '../composables/useResourceList'
import { holidayDateLabel } from '../utils/holidayForm'
import { serial } from '../utils/serial'
import HolidayFormPanel from './catalog/HolidayFormPanel.vue'

// Holidays have no on/off status, so the list's status param is not sent.
const { list, result, loading, error, savedId, load, refresh } = useResourceList<PublicHolidayOut>(
  { year: 'int' },
  (params) => {
    const { year, page, size } = params as HolidayFilters
    return listHolidayPage(api, { year, page, size })
  },
)
const panel = usePanelParam()

const THIS_YEAR = new Date().getFullYear()
const YEARS = [THIS_YEAR - 1, THIS_YEAR, THIS_YEAR + 1]
const year = computed(() => (list.filters.value.year as number | undefined) ?? null)

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'holiday' : 'holidays'}`)

// A holiday on the page opens at once; one from an old link is looked up (the API has no GET by id).
const { record: editHoliday, error: openError, openingId, load: loadEdit } = usePanelRecord(panel.id, (id) => {
  const loaded = result.value?.items.find((h) => h.id === id)
  return loaded ? Promise.resolve(loaded) : getHoliday(api, id)
})

/** The holiday that is next from today, marked in the list. */
const today = new Date().toISOString().slice(0, 10)
const nextId = computed(() => result.value?.items.find((h) => h.holiday_date >= today)?.id ?? null)
const isPast = (h: PublicHolidayOut) => h.holiday_date < today

async function onSaved(holiday: PublicHolidayOut) {
  panel.close()
  await refresh(holiday.id)
}
async function onDeleted() {
  panel.close()
  await refresh()
}

const SKELETON_COLUMNS = ['72px', '160px', '2fr', '2fr', '2fr', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Public holidays</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="panel.open('new')">
        <Plus aria-hidden="true" />
        New holiday
      </BaseButton>
    </div>

    <div class="filters" role="search">
      <div class="segmented" role="group" aria-label="Year">
        <button type="button" :aria-pressed="year === null" @click="list.set({ year: null })">All years</button>
        <button
          v-for="y in YEARS"
          :key="y"
          type="button"
          class="mono"
          :aria-pressed="year === y"
          @click="list.set({ year: y })"
        >
          {{ y }}
        </button>
      </div>
    </div>

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ serial('PH', panel.id.value) }}: {{ openError }}</b>
        <BaseButton variant="quiet" @click="loadEdit">Try again</BaseButton>
        <BaseButton variant="quiet" @click="panel.close">Close</BaseButton>
      </div>
    </div>

    <div class="sheet">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && !result" :columns="SKELETON_COLUMNS" />
      <template v-else-if="result && !result.items.length">
        <EmptyState v-if="year" filtered title="No holidays in this year" :text="`Nothing is set for ${year}.`">
          <BaseButton @click="list.reset()">All years</BaseButton>
          <BaseButton variant="primary" @click="panel.open('new')">New holiday</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No public holidays yet" text="Add the first date. Bookings on it get a warning.">
          <BaseButton variant="primary" @click="panel.open('new')">New holiday</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Public holidays</caption>
          <thead>
            <tr>
              <th class="col-serial" scope="col">Serial</th>
              <th scope="col">Date</th>
              <th scope="col">Khmer name</th>
              <th scope="col">English name</th>
              <th scope="col">Remarks</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="holiday in result.items"
              :key="holiday.id"
              :class="{ 'is-off': isPast(holiday), 'just-saved': holiday.id === savedId }"
              :aria-busy="holiday.id === openingId || undefined"
              tabindex="0"
              @click="panel.open(holiday.id)"
              @keydown.enter="panel.open(holiday.id)"
            >
              <td class="col-serial"><span class="serial"><span class="prefix">PH</span>·{{ String(holiday.id).padStart(4, '0') }}</span></td>
              <td class="date mono">
                {{ holidayDateLabel(holiday.holiday_date) }}
                <span v-if="holiday.id === nextId" class="next">Next</span>
              </td>
              <td class="kh name">{{ holiday.name_km }}</td>
              <td>{{ holiday.name_en ?? '—' }}</td>
              <td class="remarks">{{ holiday.remarks ?? '' }}</td>
              <td class="row-actions">
                <button
                  type="button"
                  class="icon-btn"
                  :aria-label="`Open ${holiday.name_en || holiday.name_km}`"
                  @click.stop="panel.open(holiday.id)"
                >
                  <LoaderCircle v-if="holiday.id === openingId" class="spin" aria-hidden="true" />
                  <Ellipsis v-else aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <HolidayFormPanel
      v-if="panel.isNew.value"
      :holiday="null"
      @saved="onSaved"
      @deleted="onDeleted"
      @close="panel.close"
    />
    <HolidayFormPanel
      v-else-if="editHoliday"
      :key="`holiday-${editHoliday.id}`"
      :holiday="editHoliday"
      @saved="onSaved"
      @deleted="onDeleted"
      @close="panel.close"
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
.date {
  white-space: nowrap;
}
.next {
  margin-left: 8px;
  font-family: var(--font-sans);
  font-size: 11.5px;
  font-weight: 500;
  color: var(--color-crimson);
}
.name {
  font-weight: 500;
}
.remarks {
  max-width: 32ch;
  overflow: hidden;
  color: var(--color-intaglio);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.segmented {
  display: inline-flex;
  height: 36px;
  padding: 3px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-sheet);
}
.segmented button {
  padding: 0 12px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-intaglio);
  font-size: 13px;
  cursor: pointer;
  transition:
    background-color 140ms ease,
    color 140ms ease;
}
.segmented button[aria-pressed='true'] {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-weight: 500;
}
</style>
