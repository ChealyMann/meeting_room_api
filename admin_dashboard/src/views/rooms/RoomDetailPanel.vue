<script setup lang="ts">
// One room in the side panel (DSH-R02, R04, R05): details, photos and equipment as tabs,
// "Turn off / Turn on" with an inline confirm (G07), and the door code only on request.
import { CircleAlert, Eye, Power } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { getDoorCode, getRoom, updateRoom } from '../../api/rooms'
import type { RoomDetail } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import StateMarks from '../../components/list/StateMarks.vue'
import { useConfirm } from '../../composables/useConfirm'
import { serial } from '../../utils/serial'
import { formatPhnomPenh } from '../../utils/time'
import RoomEquipment from './RoomEquipment.vue'
import RoomPhotos from './RoomPhotos.vue'

export type RoomStep = 'details' | 'photos' | 'equipment'

/** `initial`: the room the page already has (just saved), so the panel opens at once. */
const props = defineProps<{ roomId: number; step?: RoomStep; initial?: RoomDetail }>()
const emit = defineEmits<{ edit: []; changed: [room: RoomDetail]; close: [] }>()

const room = ref<RoomDetail | null>(props.initial?.id === props.roomId ? props.initial : null)
const loadError = ref('')
const tab = ref<RoomStep>(props.step ?? 'details')
watch(
  () => props.step,
  (step) => (tab.value = step ?? 'details'),
)

// The door code: undefined = hidden; null = asked, none set; string = shown.
const doorCode = ref<string | null | undefined>(undefined)
const doorBusy = ref(false)

const switching = ref(false)
const actionError = ref('')

const messageOf = (err: unknown) => (err instanceof ApiError ? err.message : 'Something went wrong.')

async function load() {
  loadError.value = ''
  doorCode.value = undefined
  actionError.value = ''
  try {
    room.value = await getRoom(api, props.roomId)
  } catch (err) {
    loadError.value = messageOf(err)
  }
}
watch(() => props.roomId, load, { immediate: true })
onBeforeUnmount(() => (doorCode.value = undefined))

async function showDoorCode() {
  doorBusy.value = true
  actionError.value = ''
  try {
    doorCode.value = (await getDoorCode(api, props.roomId)).door_code ?? null
  } catch (err) {
    actionError.value = messageOf(err)
  } finally {
    doorBusy.value = false
  }
}

async function setActive(active: boolean) {
  if (!room.value) return
  switching.value = true
  actionError.value = ''
  try {
    room.value = await updateRoom(api, room.value.id, { is_active: active })
    emit('changed', room.value)
  } catch (err) {
    actionError.value = messageOf(err)
  } finally {
    switching.value = false
  }
}

const { confirm } = useConfirm()

async function askTurnOff() {
  if (!room.value) return
  const ok = await confirm({
    title: `Turn off ${room.value.name_en}?`,
    text: 'People can no longer book it. You can turn it on again.',
    confirmLabel: 'Turn off',
    icon: 'power',
  })
  if (ok) await setActive(false)
}

const place = computed(() =>
  room.value ? `${room.value.location.name_en} › ${room.value.building.name_en} › ${room.value.floor.floor_label}` : '',
)
const hours = computed(() =>
  room.value ? `${room.value.start_time.slice(0, 5)}–${room.value.end_time.slice(0, 5)}` : '',
)

const TABS: Array<{ id: RoomStep; label: () => string }> = [
  { id: 'details', label: () => 'Details' },
  { id: 'photos', label: () => `Photos ${room.value?.photos.length ?? 0}/20` },
  { id: 'equipment', label: () => `Equipment ${room.value?.equipment.length ?? 0}` },
]

/** Children (photos, equipment) report their new lists here. */
function update(changes: Partial<RoomDetail>) {
  if (!room.value) return
  room.value = { ...room.value, ...changes }
  emit('changed', room.value)
}

defineExpose({ update, tab })
</script>

<template>
  <!-- Opens once the room is here, so it slides in once with its content (no skeleton swap). -->
  <SidePanel
    :open="!!room || !!loadError"
    :title="room?.name_kh ?? 'Room'"
    :subtitle="room?.name_en"
    :serial="serial('RM', roomId)"
    @close="emit('close')"
  >
    <div v-if="loadError" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ loadError }}</b>
        <BaseButton variant="quiet" @click="load">Try again</BaseButton>
      </div>
    </div>

    <div v-else-if="!room" class="loading" aria-hidden="true">
      <div v-for="n in 6" :key="n" class="skeleton-bar" :style="{ width: `${40 + n * 8}%` }" />
    </div>

    <template v-else>
      <slot name="step" :tab="tab" />

      <div class="tabs" role="tablist" aria-label="Room">
        <button
          v-for="t in TABS"
          :id="`tab-${t.id}`"
          :key="t.id"
          type="button"
          role="tab"
          :aria-selected="tab === t.id"
          :aria-controls="`tabpanel-${t.id}`"
          @click="tab = t.id"
        >
          {{ t.label() }}
        </button>
      </div>

      <section v-show="tab === 'details'" id="tabpanel-details" role="tabpanel" aria-labelledby="tab-details">
        <dl class="details">
          <div><dt>State</dt><dd><StateMarks :active="room.is_active" :bookable="room.is_bookable" :private="room.is_private" /></dd></div>
          <div><dt>Place</dt><dd>{{ place }}</dd></div>
          <div>
            <dt>Room type</dt>
            <dd><span class="kh">{{ room.category.name_kh }}</span><span class="en">{{ room.category.name_en }}</span></dd>
          </div>
          <div><dt>Seats</dt><dd class="mono">{{ room.capacity }}</dd></div>
          <div><dt>Size</dt><dd :class="room.size_sqm ? 'mono' : 'none'">{{ room.size_sqm ? `${room.size_sqm} m²` : 'Not set' }}</dd></div>
          <div><dt>Hours</dt><dd class="hours">{{ hours }}</dd></div>
          <div><dt>Owner</dt><dd :class="{ none: !room.owner }">{{ room.owner?.name_en ?? 'No owner' }}</dd></div>
          <div><dt>Short description</dt><dd :class="{ none: !room.short_desc }">{{ room.short_desc || 'None' }}</dd></div>
          <div><dt>Description</dt><dd class="wrap" :class="{ none: !room.description }">{{ room.description || 'None' }}</dd></div>
          <div>
            <dt>Door code</dt>
            <dd class="door">
              <template v-if="doorCode === undefined">
                <span class="none">Hidden</span>
                <BaseButton class="small" :busy="doorBusy" @click="showDoorCode">
                  <Eye v-if="!doorBusy" aria-hidden="true" />
                  Show door code
                </BaseButton>
              </template>
              <template v-else>
                <span v-if="doorCode === null" class="none">No door code set</span>
                <span v-else class="mono door-code">{{ doorCode }}</span>
                <BaseButton variant="quiet" class="small" @click="doorCode = undefined">Hide</BaseButton>
              </template>
            </dd>
          </div>
          <div><dt>Created</dt><dd class="mono">{{ formatPhnomPenh(room.created_at) }}</dd></div>
          <div><dt>Updated</dt><dd class="mono">{{ formatPhnomPenh(room.updated_at) }}</dd></div>
        </dl>
      </section>

      <section v-show="tab === 'photos'" id="tabpanel-photos" role="tabpanel" aria-labelledby="tab-photos">
        <RoomPhotos
          :room-id="room.id"
          :photos="room.photos"
          @change="update({ photos: $event, cover_photo: $event[0] ? { url: $event[0].url, thumbnail_url: $event[0].thumbnail_url } : null })"
        />
      </section>

      <section v-show="tab === 'equipment'" id="tabpanel-equipment" role="tabpanel" aria-labelledby="tab-equipment">
        <RoomEquipment :room-id="room.id" :equipment="room.equipment" @change="update({ equipment: $event })" />
      </section>

      <div v-if="actionError" class="summary action-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ actionError }}</b>
      </div>

    </template>

    <template v-if="room" #foot>
      <BaseButton @click="emit('edit')">Edit</BaseButton>
      <BaseButton v-if="room.is_active" variant="danger" :busy="switching" @click="askTurnOff">
        <Power aria-hidden="true" />
        Turn off
      </BaseButton>
      <BaseButton v-else :busy="switching" @click="setActive(true)">
        <Power aria-hidden="true" />
        Turn on
      </BaseButton>
    </template>
  </SidePanel>
</template>

<style scoped>
.loading {
  display: grid;
  gap: 14px;
}
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--color-rule);
}
.tabs button {
  margin-bottom: -1px;
  padding: 8px 10px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--color-intaglio);
  font-size: 13px;
  cursor: pointer;
}
.tabs button[aria-selected='true'] {
  border-bottom-color: var(--color-crimson);
  color: var(--color-ink);
  font-weight: 500;
}
.details {
  margin: 0;
}
.details > div {
  display: grid;
  grid-template-columns: 128px minmax(0, 1fr);
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-rule);
}
.details dt {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.details dd {
  margin: 0;
  font-size: 13.5px;
}
.details .kh {
  display: block;
  font-weight: 500;
}
.details .en {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.wrap {
  overflow-wrap: anywhere;
  white-space: pre-line;
}
.none {
  color: var(--color-ink-off);
}
.door {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
}
.door-code {
  font-size: 14px;
  letter-spacing: 0.06em;
}
.small {
  height: 30px;
  padding: 0 10px;
  font-size: 12.5px;
}
.action-error {
  margin-top: 16px;
}
</style>
