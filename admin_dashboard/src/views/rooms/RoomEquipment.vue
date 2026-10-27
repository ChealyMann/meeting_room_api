<script setup lang="ts">
// A room's equipment (DSH-R07, API R15): tick from the active equipment list. Inactive items
// the room already has stay ticked and marked "(off)"; once unticked and saved they cannot
// come back.
import { CircleAlert } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { listEquipment } from '../../api/references'
import { setRoomEquipment } from '../../api/rooms'
import type { EquipmentOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import { useToast } from '../../composables/useToast'
import { iconFor } from '../../utils/equipmentIcons'

const props = defineProps<{ roomId: number; equipment: EquipmentOut[] }>()
const emit = defineEmits<{ change: [list: EquipmentOut[]] }>()

const toast = useToast()
const all = ref<EquipmentOut[]>([])
const current = ref<EquipmentOut[]>([...props.equipment])
const checked = ref(new Set(props.equipment.map((e) => e.id)))
const saving = ref(false)
const error = ref('')

watch(
  () => props.equipment,
  (list) => {
    current.value = [...list]
    checked.value = new Set(list.map((e) => e.id))
  },
)

onMounted(async () => {
  all.value = await listEquipment(api)
})

/** Active equipment, plus inactive items the room still has. */
const offered = computed(() => {
  const owned = new Set(current.value.map((e) => e.id))
  const byId = new Map([...all.value, ...current.value].map((e) => [e.id, e]))
  return [...byId.values()]
    .filter((e) => e.is_active || owned.has(e.id))
    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
})

const dirty = computed(() => {
  const before = current.value.map((e) => e.id).sort((a, b) => a - b)
  const after = [...checked.value].sort((a, b) => a - b)
  return before.join(',') !== after.join(',')
})

function toggle(id: number, on: boolean) {
  const next = new Set(checked.value)
  if (on) next.add(id)
  else next.delete(id)
  checked.value = next
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const result = await setRoomEquipment(api, props.roomId, [...checked.value].sort((a, b) => a - b))
    current.value = result.items
    checked.value = new Set(result.items.map((e) => e.id))
    toast.show('Equipment saved')
    emit('change', result.items)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="equipment">
    <div v-if="error" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <b>{{ error }}</b>
    </div>
    <p v-if="!offered.length" class="none">No equipment yet. Add it under Catalog › Equipment.</p>
    <fieldset v-else>
      <legend class="sr-only">Equipment in this room</legend>
      <label v-for="e in offered" :key="e.id" class="check" :class="{ off: !e.is_active }">
        <input type="checkbox" :checked="checked.has(e.id)" @change="toggle(e.id, ($event.target as HTMLInputElement).checked)" />
        <!-- The item's icon, as in the equipment list; an empty slot keeps the names in line. -->
        <span class="icon"><component :is="iconFor(e.icon)" v-if="iconFor(e.icon)" aria-hidden="true" /></span>{{ e.is_active ? e.name : `${e.name} (off)` }}</label>
    </fieldset>
    <div class="foot">
      <BaseButton variant="primary" :busy="saving" :disabled="!dirty" @click="save">
        {{ saving ? 'Saving' : 'Save equipment' }}
      </BaseButton>
    </div>
  </div>
</template>

<style scoped>
.equipment {
  display: grid;
  gap: 12px;
}
fieldset {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
  margin: 0;
  padding: 0;
  border: 0;
}
.check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
}
.check input {
  accent-color: var(--color-crimson-fill);
}
.icon {
  display: inline-flex;
  flex: none;
  width: 18px;
  color: var(--color-intaglio);
}
.icon svg.lucide {
  width: 18px;
  height: 18px;
}
.check.off {
  color: var(--color-ink-off);
}
.none {
  color: var(--color-ink-off);
}
.foot {
  display: flex;
  justify-content: flex-end;
}
</style>
