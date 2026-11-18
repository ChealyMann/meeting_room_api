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

/** How many items are ticked or unticked since the last save. */
const changes = computed(() => {
  const before = new Set(current.value.map((e) => e.id))
  return [...checked.value].filter((id) => !before.has(id)).length + [...before].filter((id) => !checked.value.has(id)).length
})
function undo() {
  checked.value = new Set(current.value.map((e) => e.id))
}
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
    <div v-if="offered.length" class="head" aria-hidden="true">In this room <span class="mono">{{ checked.size }} of {{ offered.length }}</span></div>
    <fieldset v-if="offered.length">
      <legend class="sr-only">Equipment in this room</legend>
      <!-- Look A (owner pick, 18 Nov 2026): soft tiles, the icon in a square, a round tick. The
           checkbox stays inside for the keyboard and screen readers. -->
      <label v-for="e in offered" :key="e.id" class="check" :class="{ on: checked.has(e.id), off: !e.is_active }">
        <input
          type="checkbox"
          class="sr-only"
          :checked="checked.has(e.id)"
          @change="toggle(e.id, ($event.target as HTMLInputElement).checked)"
        />
        <span class="icon"><component :is="iconFor(e.icon)" v-if="iconFor(e.icon)" aria-hidden="true" /></span>
        <span class="name" :title="e.is_active ? e.name : `${e.name} (off)`">{{ e.is_active ? e.name : `${e.name} (off)` }}</span>
        <span class="tick" aria-hidden="true" />
      </label>
    </fieldset>
    <!-- Says what changed; Undo and Save only when something did. -->
    <div class="foot" :class="{ clean: !dirty }">
      <span class="state">
        <template v-if="dirty"><b>{{ changes }} {{ changes === 1 ? 'change' : 'changes' }}</b> not saved</template>
        <template v-else>No changes</template>
      </span>
      <span class="acts">
        <BaseButton variant="quiet" :disabled="!dirty || saving" @click="undo">Undo</BaseButton>
        <BaseButton variant="primary" :busy="saving" :disabled="!dirty" @click="save">{{ saving ? 'Saving' : 'Save' }}</BaseButton>
      </span>
    </div>
  </div>
</template>

<style scoped>
.equipment {
  display: grid;
  gap: 14px;
}
fieldset {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  border: 0;
}
.head {
  display: flex;
  justify-content: space-between;
  margin-bottom: -4px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-ink-off);
}
.head .mono {
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
}
.check {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 7px 34px 7px 8px;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
  background: var(--color-sheet);
  font-size: 13px;
  line-height: 1.25;
  cursor: pointer;
  transition:
    border-color 140ms ease,
    background-color 140ms ease,
    transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.check:active {
  transform: scale(0.98);
}
@media (hover: hover) and (pointer: fine) {
  .check:hover {
    border-color: var(--color-rule-strong);
  }
}
.check:has(input:focus-visible) {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
.icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: var(--color-field-disabled);
  color: var(--color-intaglio);
  transition:
    background-color 140ms ease,
    color 140ms ease;
}
.icon svg.lucide {
  width: 18px;
  height: 18px;
}
/* One line only (owner, 18 Nov 2026): a long name ends in "…", the whole name on hover. */
.name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* The round tick: an empty ring, filled crimson with a white check when ticked. */
.tick {
  position: absolute;
  top: 50%;
  right: 10px;
  width: 18px;
  height: 18px;
  margin-top: -9px;
  border: 1.5px solid var(--color-rule-strong);
  border-radius: 50%;
  transition:
    background-color 140ms ease,
    border-color 140ms ease;
}
.tick::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 5.5px;
  width: 4px;
  height: 8px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  opacity: 0;
  transform: rotate(45deg) scale(0.6);
  transition:
    opacity 120ms ease,
    transform 180ms cubic-bezier(0.23, 1, 0.32, 1);
}
.check.on {
  border-color: var(--color-danger-line);
  background: var(--color-crimson-wash);
}
.check.on .icon {
  background: var(--color-sheet);
  color: var(--color-crimson);
}
.check.on .tick {
  border-color: var(--color-crimson-fill);
  background: var(--color-crimson-fill);
}
.check.on .tick::after {
  opacity: 1;
  transform: rotate(45deg) scale(1);
}
.check.off .name {
  color: var(--color-ink-off);
}
.none {
  color: var(--color-ink-off);
}
.foot {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
}
.state {
  flex: 1;
  font-size: 13px;
  color: var(--color-ink-off);
}
.state b {
  color: var(--color-ink);
  font-weight: 600;
}
.acts {
  display: flex;
  gap: 6px;
  transition:
    opacity 160ms ease,
    transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
/* Nothing changed: the buttons step away instead of showing faded. */
.foot.clean .acts {
  opacity: 0;
  transform: translateY(4px);
  pointer-events: none;
}
@media (max-width: 420px) {
  fieldset {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (prefers-reduced-motion: reduce) {
  .check,
  .icon,
  .tick,
  .tick::after,
  .acts {
    transition-duration: 1ms;
  }
}
</style>
