<script setup lang="ts">
// Create, edit or move a floor in the side panel (DSH-P04, P05, G03–G06, G08).
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { createFloor, updateFloor } from '../../api/places'
import { listBuildings, listOffices } from '../../api/references'
import type { BuildingOut, FloorDetail, LocationOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import {
  emptyFloorForm,
  floorChanges,
  floorCreateBody,
  floorFormOf,
  floorProblems,
  type FloorForm,
} from '../../utils/placeForms'
import { selectOptions } from '../../utils/selectOptions'
import { serial } from '../../utils/serial'

const props = defineProps<{
  floor: FloorDetail | null
  defaultOfficeId?: number | null
  defaultBuildingId?: number | null
}>()
const emit = defineEmits<{ saved: [floor: FloorDetail]; close: [] }>()

const LABELS: Record<string, string> = {
  location_id: 'Office',
  building_id: 'Building',
  floor_label: 'Floor name',
  sort_order: 'Order',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the floor is unchanged on the server (same updated_at).
interface FloorDraft {
  updatedAt: string | null
  form: FloorForm
}
const draftKey = computed(() => (props.floor ? `floor:${props.floor.id}` : 'floor:new'))
const base = () =>
  props.floor
    ? floorFormOf(props.floor)
    : emptyFloorForm(props.defaultOfficeId ?? null, props.defaultOfficeId ? (props.defaultBuildingId ?? null) : null)
function restore(): FloorForm {
  const draft = drafts.get<FloorDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.floor?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<FloorForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const offices = ref<LocationOut[]>([])
const buildings = ref<BuildingOut[]>([])
onMounted(async () => {
  offices.value = await listOffices(api)
  await loadBuildings(form.value.location_id)
})

// Only the answer for the office chosen last counts: answers can come back out of order.
async function loadBuildings(id: number | null) {
  const items = id ? await listBuildings(api, id) : []
  if (form.value.location_id === id) buildings.value = items
}

const officeOptions = computed(() =>
  selectOptions(offices.value, form.value.location_id, (o) => o.name_en, 'Unknown office'),
)
const buildingOptions = computed(() =>
  selectOptions(buildings.value, form.value.building_id, (b) => b.name_en, 'Unknown building'),
)
const idOf = (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  return value ? Number(value) : null
}
// Choosing an office clears the building, so a building from another office is never sent.
async function chooseOffice(event: Event) {
  form.value.location_id = idOf(event)
  form.value.building_id = null
  buildings.value = []
  await loadBuildings(form.value.location_id)
}

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.floor ? floorChanges(form.value, props.floor) : null))
const dirty = computed(() =>
  props.floor
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(base()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.floor?.updated_at ?? null, form: form.value })
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

function done(floor: FloorDetail, title: string) {
  drafts.clear(draftKey.value)
  toast.show(title, `${serial('FL', floor.id)} · ${floor.location.name_en} › ${floor.building.name_en}`)
  emit('saved', floor)
}

async function save() {
  clear()
  const problems = floorProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.floor && !dirty.value) return
  saving.value = true
  try {
    const floor = props.floor
      ? await updateFloor(api, props.floor.id, changes.value ?? {})
      : await createFloor(api, floorCreateBody(form.value))
    done(floor, `${floor.floor_label} saved`)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const floor = await updateFloor(api, props.floor!.id, { is_active: active })
  done(floor, `${floor.floor_label} turned ${active ? 'on' : 'off'}`)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="floor ? floor.floor_label : 'New floor'"
    :subtitle="floor ? `${floor.building.name_en} · ${floor.location.name_en}` : undefined"
    :serial="serial('FL', floor?.id ?? null)"
    @close="close"
  >
    <form id="floor-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <section class="group" aria-labelledby="g-where">
        <h3 id="g-where">Where</h3>
        <BaseField id="location_id" label="Office" :error="errors.location_id">
          <template #default="{ describedBy, invalid }">
            <select id="location_id" class="input" :value="form.location_id ?? ''" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" @change="chooseOffice">
              <option value="">Choose an office</option>
              <option v-for="o in officeOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
          </template>
        </BaseField>
        <BaseField
          id="building_id"
          label="Building"
          :hint="floor ? 'Change to move the floor' : undefined"
          :error="errors.building_id"
        >
          <template #default="{ describedBy, invalid }">
            <select id="building_id" class="input" :value="form.building_id ?? ''" :disabled="!form.location_id" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" @change="form.building_id = idOf($event)">
              <option value="">Choose a building</option>
              <option v-for="b in buildingOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
            </select>
          </template>
        </BaseField>
      </section>

      <section class="group" aria-labelledby="g-floor">
        <h3 id="g-floor">Floor</h3>
        <div class="row2">
          <BaseField id="floor_label" label="Floor name" :hint="`${count(form.floor_label)}/100`" :error="errors.floor_label">
            <template #default="{ describedBy, invalid }">
              <input id="floor_label" v-model="form.floor_label" class="input" placeholder="e.g. 3rd floor" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
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
        v-if="floor"
        class="toggle"
        :active="floor.is_active"
        :name="floor.floor_label"
        kind="floor"
        :rooms="{ floor_id: floor.id }"
        :turn="turn"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="floor-form" :busy="saving" :disabled="!!floor && !dirty">
        {{ saving ? (floor ? 'Saving' : 'Creating') : floor ? 'Save changes' : 'Create floor' }}
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
  grid-template-columns: 2fr 1fr;
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
