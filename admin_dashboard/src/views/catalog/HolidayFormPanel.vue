<script setup lang="ts">
// Add, change or delete a public holiday in the side panel: its date, Khmer and English names,
// and remarks. A booking on the date is still allowed; it only gets a warning.
import { CircleAlert, Trash2 } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { createHoliday, deleteHoliday, updateHoliday } from '../../api/holidays'
import type { PublicHolidayOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import DatePicker from '../../components/base/DatePicker.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import { useConfirm } from '../../composables/useConfirm'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import {
  emptyHolidayForm,
  holidayChanges,
  holidayCreateBody,
  holidayDateLabel,
  holidayFormOf,
  holidayProblems,
  type HolidayForm,
} from '../../utils/holidayForm'
import { serial } from '../../utils/serial'

const props = defineProps<{ holiday: PublicHolidayOut | null }>()
const emit = defineEmits<{ saved: [holiday: PublicHolidayOut]; deleted: []; close: [] }>()

const LABELS: Record<string, string> = {
  holiday_date: 'Date',
  name_km: 'Khmer name',
  name_en: 'English name',
  remarks: 'Remarks',
}

const toast = useToast()
const { confirm } = useConfirm()
const { errors, formMessage, apply, clear } = useFieldErrors()

const form = ref<HolidayForm>(props.holiday ? holidayFormOf(props.holiday) : emptyHolidayForm())
const saving = ref(false)
const deleting = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const changes = computed(() => (props.holiday ? holidayChanges(form.value, props.holiday) : null))
const dirty = computed(() =>
  props.holiday
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(emptyHolidayForm()),
)
const summary = computed(() =>
  Object.keys(errors.value)
    .filter((key) => key in LABELS)
    .map((key) => ({ id: key, label: LABELS[key] ?? key })),
)
const count = (text: string) => [...text].length
const title = computed(() => (props.holiday ? props.holiday.name_en || props.holiday.name_km : 'New holiday'))

async function focusProblem() {
  await nextTick()
  panel.value?.focusFirst()
}

async function save() {
  clear()
  const problems = holidayProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.holiday && !dirty.value) return
  saving.value = true
  try {
    const holiday = props.holiday
      ? await updateHoliday(api, props.holiday.id, changes.value ?? {})
      : await createHoliday(api, holidayCreateBody(form.value))
    toast.show(`${holiday.name_en || holiday.name_km} saved`, holidayDateLabel(holiday.holiday_date))
    emit('saved', holiday)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function askDelete() {
  const holiday = props.holiday!
  const ok = await confirm({
    title: `Delete ${holiday.name_en || holiday.name_km}?`,
    text: `${holidayDateLabel(holiday.holiday_date)} stops showing a holiday warning. Bookings already made do not change.`,
    confirmLabel: 'Delete holiday',
    icon: 'trash',
  })
  if (!ok) return
  deleting.value = true
  try {
    await deleteHoliday(api, holiday.id)
    toast.show(`${holiday.name_en || holiday.name_km} deleted`, holidayDateLabel(holiday.holiday_date))
    emit('deleted')
  } catch (err) {
    apply(err)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="title"
    :serial="serial('PH', holiday?.id ?? null)"
    @close="emit('close')"
  >
    <form id="holiday-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <section class="group" aria-labelledby="g-day">
        <h3 id="g-day">Day</h3>
        <BaseField id="holiday_date" label="Date" hint="One holiday per date" :error="errors.holiday_date">
          <template #default="{ describedBy, invalid }">
            <DatePicker
              id="holiday_date"
              class="date"
              label="Date"
              :model-value="form.holiday_date || null"
              :described-by="describedBy"
              :invalid="invalid"
              @update:model-value="form.holiday_date = $event ?? ''"
            />
          </template>
        </BaseField>
      </section>

      <section class="group" aria-labelledby="g-names">
        <h3 id="g-names">Names</h3>
        <BaseField id="name_km" label="Khmer name" :hint="`${count(form.name_km)}/255`" :error="errors.name_km">
          <template #default="{ describedBy, invalid }">
            <input
              id="name_km"
              v-model="form.name_km"
              class="input kh"
              lang="km"
              placeholder="ទិវាឯករាជ្យជាតិ"
              :aria-describedby="describedBy"
              :aria-invalid="invalid || undefined"
            />
          </template>
        </BaseField>
        <BaseField id="name_en" label="English name" :hint="`Optional · ${count(form.name_en)}/255`" :error="errors.name_en">
          <template #default="{ describedBy, invalid }">
            <input
              id="name_en"
              v-model="form.name_en"
              class="input"
              placeholder="Independence Day"
              :aria-describedby="describedBy"
              :aria-invalid="invalid || undefined"
            />
          </template>
        </BaseField>
      </section>

      <section class="group" aria-labelledby="g-notes">
        <h3 id="g-notes">Remarks</h3>
        <BaseField id="remarks" label="Remarks" :hint="`Optional · ${count(form.remarks)}/1000`" :error="errors.remarks">
          <template #default="{ describedBy, invalid }">
            <textarea
              id="remarks"
              v-model="form.remarks"
              class="input"
              rows="3"
              :aria-describedby="describedBy"
              :aria-invalid="invalid || undefined"
            />
          </template>
        </BaseField>
      </section>
    </form>

    <template #foot>
      <BaseButton v-if="holiday" variant="quiet" class="delete" :busy="deleting" @click="askDelete">
        <Trash2 aria-hidden="true" />
        Delete
      </BaseButton>
      <BaseButton variant="quiet" @click="emit('close')">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="holiday-form" :busy="saving" :disabled="!!holiday && !dirty">
        {{ saving ? (holiday ? 'Saving' : 'Adding') : holiday ? 'Save changes' : 'Add holiday' }}
      </BaseButton>
    </template>
  </SidePanel>
</template>

<style scoped>
.form {
  display: grid;
  gap: 20px;
}
.group {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding-top: 16px;
  border-top: 1px solid var(--color-rule);
}
.group:first-of-type {
  padding-top: 0;
  border-top: 0;
}
h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}
.date {
  max-width: 200px;
}
textarea.input {
  height: auto;
  min-height: 76px;
  padding-block: 8px;
  resize: vertical;
}
/* Delete sits apart, at the start of the foot. */
.delete {
  margin-right: auto;
  color: var(--color-crimson);
}
</style>
