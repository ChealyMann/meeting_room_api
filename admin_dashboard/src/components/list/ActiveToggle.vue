<script setup lang="ts">
// Turn off / turn on for an office, building or floor (DSH-G07, P05). Turning off asks in the
// confirm dialog and says how many active rooms stop being bookable; turning on does not ask.
import { CircleAlert, Power } from 'lucide-vue-next'
import { ref } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveRooms } from '../../api/places'
import { useConfirm } from '../../composables/useConfirm'
import BaseButton from '../base/BaseButton.vue'

const props = defineProps<{
  active: boolean
  name: string
  kind: 'office' | 'building' | 'floor'
  rooms: { location_id?: number; building_id?: number; floor_id?: number }
  /** The page's PATCH of is_active; throws ApiError when the API refuses. */
  turn: (active: boolean) => Promise<void>
}>()

const { confirm } = useConfirm()
const busy = ref(false)
const error = ref('')

function warning(count: number | null): string {
  if (count === null) return 'Its rooms stop being bookable. You can turn it on again.'
  if (count === 0) return 'No rooms are affected. You can turn it on again.'
  const rooms = count === 1 ? '1 room' : `${count} rooms`
  return `${rooms} in this ${props.kind} ${count === 1 ? 'stops' : 'stop'} being bookable. You can turn it on again.`
}

async function run(active: boolean) {
  busy.value = true
  error.value = ''
  try {
    await props.turn(active)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    busy.value = false
  }
}

async function turnOff() {
  busy.value = true
  let count: number | null = null
  try {
    count = await countActiveRooms(api, props.rooms)
  } catch {
    count = null // still ask, with the general warning
  } finally {
    busy.value = false
  }
  const ok = await confirm({
    title: `Turn off ${props.name}?`,
    text: warning(count),
    confirmLabel: 'Turn off',
    icon: 'power',
  })
  if (ok) await run(false)
}
</script>

<template>
  <div class="toggle">
    <div v-if="error" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <b>{{ error }}</b>
    </div>
    <BaseButton v-if="active" variant="danger" :busy="busy" @click="turnOff">
      <Power v-if="!busy" aria-hidden="true" />
      Turn off
    </BaseButton>
    <BaseButton v-else :busy="busy" @click="run(true)">
      <Power v-if="!busy" aria-hidden="true" />
      Turn on
    </BaseButton>
  </div>
</template>

<style scoped>
.toggle {
  position: relative;
}
/* Shown above the button, so a refusal is read right where it happened. The button sits at
   the start of the panel foot, so the message grows to the right. */
.summary {
  position: absolute;
  left: 0;
  bottom: calc(100% + 12px);
  width: max-content;
  max-width: min(360px, 80vw);
}
</style>
