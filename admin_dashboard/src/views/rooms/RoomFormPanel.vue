<script setup lang="ts">
// Create or edit a room in the side panel (DSH-R03, R04, G03–G06, G08, G09).
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { listBuildings, listFloors, listOffices, listRoomOwners, listRoomTypes } from '../../api/references'
import { createRoom, updateRoom } from '../../api/rooms'
import type { BuildingOut, CategoryOut, FloorOut, LocationOut, RoomDetail, UserListItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import OfficePicker from '../../components/list/OfficePicker.vue'
import SearchPicker from '../../components/list/SearchPicker.vue'
import { FIELD_WORDS } from '../../utils/pickerWords'
import BaseField from '../../components/base/BaseField.vue'
import BaseSwitch from '../../components/base/BaseSwitch.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import PasswordInput from '../../components/base/PasswordInput.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import { emptyRoomForm, roomChanges, roomCreateBody, roomFormOf, roomProblems, type RoomForm } from '../../utils/roomForm'
import { selectOptions } from '../../utils/selectOptions'
import { serial } from '../../utils/serial'

const props = defineProps<{ room: RoomDetail | null }>()
const emit = defineEmits<{ saved: [room: RoomDetail]; close: [] }>()

const LABELS: Record<string, string> = {
  name_kh: 'Khmer name',
  name_en: 'English name',
  location_id: 'Office',
  building_id: 'Building',
  floor_id: 'Floor',
  category_id: 'Room type',
  capacity: 'Seats',
  size_sqm: 'Size',
  start_time: 'Opening',
  end_time: 'Closing',
  short_desc: 'Short description',
  description: 'Description',
  door_code: 'Door code',
  room_owner_id: 'Owner',
  is_private: 'Private',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the room is unchanged on the server (same updated_at).
interface RoomDraft {
  updatedAt: string | null
  form: RoomForm
}
const draftKey = computed(() => (props.room ? `room:${props.room.id}` : 'room:new'))
const base = () => (props.room ? roomFormOf(props.room) : emptyRoomForm())
function restore(): RoomForm {
  const draft = drafts.get<RoomDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.room?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<RoomForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const offices = ref<LocationOut[]>([])
const buildings = ref<BuildingOut[]>([])
const floors = ref<FloorOut[]>([])
const roomTypes = ref<CategoryOut[]>([])
const owners = ref<UserListItem[]>([])

onMounted(async () => {
  const [o, t, people] = await Promise.all([listOffices(api), listRoomTypes(api), listRoomOwners(api)])
  offices.value = o
  roomTypes.value = t
  owners.value = people
  await Promise.all([loadBuildings(form.value.location_id), loadFloors(form.value.building_id)])
})

const officeOptions = computed(() =>
  selectOptions(offices.value, form.value.location_id, (o) => o.name_en, 'Unknown office'),
)
const buildingOptions = computed(() =>
  selectOptions(buildings.value, form.value.building_id, (b) => b.name_en, 'Unknown building'),
)
const floorOptions = computed(() =>
  selectOptions(floors.value, form.value.floor_id, (f) => f.floor_label, 'Unknown floor'),
)
const typeOptions = computed(() =>
  selectOptions(roomTypes.value, form.value.category_id, (t) => t.name_en, 'Unknown room type'),
)


// Only the answer for the parent chosen last counts: answers can come back out of order.
async function loadBuildings(id: number | null) {
  const items = id ? await listBuildings(api, id) : []
  if (form.value.location_id === id) buildings.value = items
}
async function loadFloors(id: number | null) {
  const items = id ? await listFloors(api, id) : []
  if (form.value.building_id === id) floors.value = items
}

// Choosing a parent clears its children, so a floor from another office is never sent.
async function chooseOffice(id: number | null) {
  form.value.location_id = id
  form.value.building_id = null
  form.value.floor_id = null
  buildings.value = []
  floors.value = []
  await loadBuildings(form.value.location_id)
}
async function chooseBuilding(id: number | null) {
  form.value.building_id = id
  form.value.floor_id = null
  floors.value = []
  await loadFloors(form.value.building_id)
}

// Active room owners, plus the room's current owner even when no longer one (G08).
const ownerOptions = computed(() => {
  const options = owners.value.map((o) => ({ value: o.id, label: o.name_en }))
  const chosen = form.value.room_owner_id
  if (chosen !== null && !options.some((o) => o.value === chosen)) {
    const current = props.room?.owner
    options.unshift({
      value: chosen,
      label: current?.id === chosen ? `${current.name_en} (off)` : 'Unknown owner',
    })
  }
  return options
})

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.room ? roomChanges(form.value, props.room) : null))
const dirty = computed(() =>
  props.room
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(emptyRoomForm()),
)

// Unsaved typing survives a forced sign-in (DSH-A06).
watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.room?.updated_at ?? null, form: form.value })
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
  const problems = roomProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.room && !dirty.value) return
  saving.value = true
  try {
    const room = props.room
      ? await updateRoom(api, props.room.id, changes.value ?? {})
      : await createRoom(api, roomCreateBody(form.value))
    drafts.clear(draftKey.value)
    toast.show(
      `${room.name_en} saved`,
      `${serial('RM', room.id)} · ${room.location.name_en} › ${room.building.name_en} › ${room.floor.floor_label}`,
    )
    emit('saved', room)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="room ? room.name_kh : 'New room'"
    :subtitle="room?.name_en"
    :serial="serial('RM', room?.id ?? null)"
    @close="close"
  >
    <form id="room-form" class="form" novalidate @submit.prevent="save">
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

      <section class="group" aria-labelledby="g-place">
        <h3 id="g-place">Place</h3>
        <BaseField id="location_id" label="Office" :error="errors.location_id">
          <template #default="{ describedBy, invalid }">
            <OfficePicker
              id="location_id"
              mode="field"
              :offices="offices"
              :model-value="form.location_id"
              :invalid="invalid"
              :described-by="describedBy"
              @update:model-value="chooseOffice"
            />
          </template>
        </BaseField>
        <div class="row2">
          <BaseField id="building_id" label="Building" :error="errors.building_id">
            <template #default="{ describedBy, invalid }">
              <SearchPicker
                id="building_id"
                mode="field"
                :items="buildingOptions"
                :words="FIELD_WORDS.building"
                :model-value="form.building_id"
                :disabled="!form.location_id"
                :invalid="invalid"
                :described-by="describedBy"
                @update:model-value="chooseBuilding($event as number | null)"
              />
            </template>
          </BaseField>
          <BaseField id="floor_id" label="Floor" :error="errors.floor_id">
            <template #default="{ describedBy, invalid }">
              <SearchPicker
                id="floor_id"
                mode="field"
                :items="floorOptions"
                :words="FIELD_WORDS.floor"
                :model-value="form.floor_id"
                :disabled="!form.building_id"
                :invalid="invalid"
                :described-by="describedBy"
                @update:model-value="form.floor_id = $event as number | null"
              />
            </template>
          </BaseField>
        </div>
      </section>

      <section class="group" aria-labelledby="g-room">
        <h3 id="g-room">Room</h3>
        <BaseField id="category_id" label="Room type" :error="errors.category_id">
          <template #default="{ describedBy, invalid }">
            <SearchPicker
              id="category_id"
              mode="field"
              :items="typeOptions"
              :words="FIELD_WORDS.roomType"
              :model-value="form.category_id"
              :invalid="invalid"
              :described-by="describedBy"
              @update:model-value="form.category_id = $event as number | null"
            />
          </template>
        </BaseField>
        <div class="row2">
          <BaseField id="capacity" label="Seats" hint="1 to 10000" :error="errors.capacity">
            <template #default="{ describedBy, invalid }">
              <input id="capacity" v-model="form.capacity" class="input mono" inputmode="numeric" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
            </template>
          </BaseField>
          <BaseField id="size_sqm" label="Size" hint="optional" :error="errors.size_sqm">
            <template #default="{ describedBy, invalid }">
              <div class="with-unit">
                <input id="size_sqm" v-model="form.size_sqm" class="input mono" inputmode="numeric" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
                <span aria-hidden="true">m²</span>
              </div>
            </template>
          </BaseField>
        </div>
        <div class="row2">
          <BaseField id="start_time" label="Opening" :error="errors.start_time">
            <template #default="{ describedBy, invalid }">
              <input id="start_time" v-model="form.start_time" class="input mono" type="time" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
            </template>
          </BaseField>
          <BaseField id="end_time" label="Closing" :error="errors.end_time">
            <template #default="{ describedBy, invalid }">
              <input id="end_time" v-model="form.end_time" class="input mono" type="time" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
            </template>
          </BaseField>
        </div>
      </section>

      <section class="group" aria-labelledby="g-about">
        <h3 id="g-about">About</h3>
        <BaseField id="short_desc" label="Short description" :hint="`${count(form.short_desc)}/200`" :error="errors.short_desc">
          <template #default="{ describedBy, invalid }">
            <input id="short_desc" v-model="form.short_desc" class="input" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
        <BaseField id="description" label="Description" :hint="`${count(form.description)}/1000`" :error="errors.description">
          <template #default="{ describedBy, invalid }">
            <textarea id="description" v-model="form.description" class="input" rows="3" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
      </section>

      <section class="group" aria-labelledby="g-access">
        <h3 id="g-access">Access</h3>
        <BaseField id="door_code" label="Door code" :hint="room ? 'Leave empty to keep the current code' : 'optional'" :error="errors.door_code">
          <template #default="{ describedBy, invalid }">
            <PasswordInput id="door_code" v-model="form.door_code" autocomplete="new-password" :described-by="describedBy" :invalid="invalid" />
          </template>
        </BaseField>
        <BaseField id="room_owner_id" label="Owner" :error="errors.room_owner_id">
          <template #default="{ describedBy, invalid }">
            <SearchPicker
              id="room_owner_id"
              mode="field"
              :items="ownerOptions"
              :words="FIELD_WORDS.owner"
              :model-value="form.room_owner_id"
              nullable
              :invalid="invalid"
              :described-by="describedBy"
              @update:model-value="form.room_owner_id = $event as number | null"
            />
          </template>
        </BaseField>
        <div class="switch-row">
          <div>
            <label for="is_private">Private</label>
            <p>Only a label: shows the room as private.</p>
          </div>
          <BaseSwitch id="is_private" v-model="form.is_private" />
        </div>
      </section>
    </form>

    <template #foot>
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="room-form" :busy="saving" :disabled="!!room && !dirty">
        {{ saving ? (room ? 'Saving' : 'Creating') : room ? 'Save changes' : 'Create room' }}
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
  gap: 12px;
}
.with-unit {
  position: relative;
}
.with-unit .input {
  padding-right: 40px;
}
.with-unit span {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  font-size: 12px;
  color: var(--color-intaglio);
}
textarea.input {
  min-height: 72px;
}
.switch-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.switch-row label {
  font-size: 12.5px;
  font-weight: 500;
}
.switch-row p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
@media (max-width: 760px) {
  .row2 {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
