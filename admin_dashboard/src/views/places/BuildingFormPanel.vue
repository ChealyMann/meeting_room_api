<script setup lang="ts">
// Create, edit or move a building in the side panel (DSH-P03, P05, G03–G06, G08).
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveRooms, createBuilding, updateBuilding } from '../../api/places'
import { listOffices } from '../../api/references'
import type { BuildingDetail, LocationOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import OfficePicker from '../../components/list/OfficePicker.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import {
  buildingChanges,
  buildingCreateBody,
  buildingFormOf,
  buildingProblems,
  emptyBuildingForm,
  type BuildingForm,
} from '../../utils/placeForms'
import { serial } from '../../utils/serial'

const props = defineProps<{ building: BuildingDetail | null; defaultOfficeId?: number | null }>()
const emit = defineEmits<{ saved: [building: BuildingDetail]; close: [] }>()

const LABELS: Record<string, string> = {
  location_id: 'Office',
  name_kh: 'Khmer name',
  name_en: 'English name',
  short_name: 'Short name',
  sort_order: 'Order',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the building is unchanged on the server (same updated_at).
interface BuildingDraft {
  updatedAt: string | null
  form: BuildingForm
}
const draftKey = computed(() => (props.building ? `building:${props.building.id}` : 'building:new'))
const base = () => (props.building ? buildingFormOf(props.building) : emptyBuildingForm(props.defaultOfficeId ?? null))
function restore(): BuildingForm {
  const draft = drafts.get<BuildingDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.building?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<BuildingForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const offices = ref<LocationOut[]>([])
onMounted(async () => {
  offices.value = await listOffices(api)
})

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.building ? buildingChanges(form.value, props.building) : null))
const dirty = computed(() =>
  props.building
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(base()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.building?.updated_at ?? null, form: form.value })
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

function done(building: BuildingDetail, title: string) {
  drafts.clear(draftKey.value)
  toast.show(title, `${serial('BL', building.id)} · ${building.location.name_en}`)
  emit('saved', building)
}

async function save() {
  clear()
  const problems = buildingProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.building && !dirty.value) return
  saving.value = true
  try {
    const building = props.building
      ? await updateBuilding(api, props.building.id, changes.value ?? {})
      : await createBuilding(api, buildingCreateBody(form.value))
    done(building, `${building.name_en} saved`)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const building = await updateBuilding(api, props.building!.id, { is_active: active })
  done(building, `${building.name_en} turned ${active ? 'on' : 'off'}`)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="building ? building.name_kh : 'New building'"
    :subtitle="building?.name_en"
    :serial="serial('BL', building?.id ?? null)"
    @close="close"
  >
    <form id="building-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <section class="group" aria-labelledby="g-where">
        <h3 id="g-where">Where</h3>
        <BaseField
          id="location_id"
          label="Office"
          :hint="building ? 'Change to move the building' : undefined"
          :error="errors.location_id"
        >
          <template #default="{ describedBy, invalid }">
            <OfficePicker
              id="location_id"
              mode="field"
              :offices="offices"
              :model-value="form.location_id"
              :invalid="invalid"
              :described-by="describedBy"
              @update:model-value="form.location_id = $event"
            />
          </template>
        </BaseField>
      </section>

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
        <div class="row2">
          <BaseField id="short_name" label="Short name" :hint="`${count(form.short_name)}/20`" :error="errors.short_name">
            <template #default="{ describedBy, invalid }">
              <input id="short_name" v-model="form.short_name" class="input mono" placeholder="optional, e.g. A" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
            </template>
          </BaseField>
          <BaseField id="sort_order" label="Order" hint="Lower comes first" :error="errors.sort_order">
            <template #default="{ describedBy, invalid }">
              <input id="sort_order" v-model="form.sort_order" class="input mono" inputmode="numeric" placeholder="0" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
            </template>
          </BaseField>
        </div>
      </section>
    </form>

    <template #foot>
      <ActiveToggle
        v-if="building"
        class="toggle"
        :active="building.is_active"
        :name="building.name_en"
        kind="building"
        :count="() => countActiveRooms(api, { building_id: building!.id })"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="building-form" :busy="saving" :disabled="!!building && !dirty">
        {{ saving ? (building ? 'Saving' : 'Creating') : building ? 'Save changes' : 'Create building' }}
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
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: start;
  gap: 12px;
}
/* Turn off sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
@media (max-width: 760px) {
  .row2 {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
