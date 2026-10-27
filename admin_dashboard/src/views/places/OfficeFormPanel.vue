<script setup lang="ts">
// Create or edit an office in the side panel (DSH-P01, P02, P05, G03–G06).
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveRooms, createOffice, updateOffice } from '../../api/places'
import { listProvinces } from '../../api/references'
import type { LocationOut, ProvinceRef } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import SearchPicker from '../../components/list/SearchPicker.vue'
import { FIELD_WORDS } from '../../utils/pickerWords'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import {
  emptyOfficeForm,
  officeChanges,
  officeCreateBody,
  officeFormOf,
  officeProblems,
  type OfficeForm,
} from '../../utils/placeForms'
import { serial } from '../../utils/serial'

const props = defineProps<{ office: LocationOut | null }>()
const emit = defineEmits<{ saved: [office: LocationOut]; close: [] }>()

const LABELS: Record<string, string> = {
  name_kh: 'Khmer name',
  name_en: 'English name',
  province: 'Province',
  address: 'Address',
  map_query: 'Map text',
  description: 'Description',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the office is unchanged on the server (same updated_at).
interface OfficeDraft {
  updatedAt: string | null
  form: OfficeForm
}
const draftKey = computed(() => (props.office ? `office:${props.office.id}` : 'office:new'))
const base = () => (props.office ? officeFormOf(props.office) : emptyOfficeForm())
function restore(): OfficeForm {
  const draft = drafts.get<OfficeDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.office?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<OfficeForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const provinces = ref<ProvinceRef[]>([])
onMounted(async () => {
  provinces.value = await listProvinces(api)
})
// A province the list does not have shows as "Unknown province" (the picker's own words).
const provinceOptions = computed(() => provinces.value.map((p) => ({ value: p.code, label: p.name_en, keywords: p.name_kh })))

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.office ? officeChanges(form.value, props.office) : null))
const dirty = computed(() =>
  props.office
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(emptyOfficeForm()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.office?.updated_at ?? null, form: form.value })
      : drafts.clear(draftKey.value),
  { deep: true },
)

const summary = computed(() =>
  Object.keys(errors.value)
    .filter((key) => key in LABELS)
    .map((key) => ({ id: key, label: LABELS[key] ?? key })),
)
const count = (text: string) => [...text].length

async function focusProblem() {
  await nextTick()
  panel.value?.focusFirst()
}

async function save() {
  clear()
  const problems = officeProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.office && !dirty.value) return
  saving.value = true
  try {
    const office = props.office
      ? await updateOffice(api, props.office.id, changes.value ?? {})
      : await createOffice(api, officeCreateBody(form.value))
    drafts.clear(draftKey.value)
    toast.show(`${office.name_en} saved`, serial('OF', office.id))
    emit('saved', office)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const office = await updateOffice(api, props.office!.id, { is_active: active })
  drafts.clear(draftKey.value)
  toast.show(`${office.name_en} is now ${active ? 'active' : 'inactive'}`, serial('OF', office.id))
  emit('saved', office)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="office ? office.name_kh : 'New office'"
    :subtitle="office?.name_en"
    :serial="serial('OF', office?.id ?? null)"
    @close="close"
  >
    <form id="office-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <section class="group" aria-labelledby="g-names">
        <h3 id="g-names">Names</h3>
        <BaseField id="name_kh" label="Khmer name" :hint="`${count(form.name_kh)}/100`" :error="errors.name_kh">
          <template #default="{ describedBy, invalid }">
            <input id="name_kh" v-model="form.name_kh" class="input kh" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
        <BaseField id="name_en" label="English name" :hint="`${count(form.name_en)}/100`" :error="errors.name_en">
          <template #default="{ describedBy, invalid }">
            <input id="name_en" v-model="form.name_en" class="input" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
      </section>

      <section class="group" aria-labelledby="g-where">
        <h3 id="g-where">Where</h3>
        <BaseField id="province" label="Province" :error="errors.province">
          <template #default="{ describedBy, invalid }">
            <SearchPicker
              id="province"
              mode="field"
              :items="provinceOptions"
              :words="FIELD_WORDS.province"
              :model-value="form.province || null"
              :invalid="invalid"
              :described-by="describedBy"
              @update:model-value="form.province = ($event as string | null) ?? ''"
            />
          </template>
        </BaseField>
        <BaseField id="address" label="Address" :hint="`${count(form.address)}/200`" :error="errors.address">
          <template #default="{ describedBy, invalid }">
            <input id="address" v-model="form.address" class="input" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
        <BaseField id="map_query" label="Map text" :hint="`${count(form.map_query)}/500`" :error="errors.map_query">
          <template #default="{ describedBy, invalid }">
            <input id="map_query" v-model="form.map_query" class="input" :aria-describedby="`map-help ${describedBy ?? ''}`.trim()" :aria-invalid="invalid || undefined" />
            <p id="map-help" class="help">What to search on a map, e.g. National Bank of Cambodia, Phnom Penh</p>
          </template>
        </BaseField>
      </section>

      <section class="group" aria-labelledby="g-about">
        <h3 id="g-about">About</h3>
        <BaseField id="description" label="Description" :hint="`${count(form.description)}/1000`" :error="errors.description">
          <template #default="{ describedBy, invalid }">
            <textarea id="description" v-model="form.description" class="input" rows="3" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
      </section>
    </form>

    <template #foot>
      <ActiveToggle
        v-if="office"
        class="toggle"
        :active="office.is_active"
        :name="office.name_en"
        kind="office"
        :count="() => countActiveRooms(api, { location_id: office!.id })"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="office-form" :busy="saving" :disabled="!!office && !dirty">
        {{ saving ? (office ? 'Saving' : 'Creating') : office ? 'Save changes' : 'Create office' }}
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
textarea.input {
  min-height: 72px;
}
.help {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
/* The Active switch sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
</style>
