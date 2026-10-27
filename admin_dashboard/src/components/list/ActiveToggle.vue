<script setup lang="ts">
// Turn off / turn on for a place, a catalog record or an organisation record (DSH-G07, P05, C01,
// C02, O01–O03). Turning off asks in the confirm dialog and says what happens to the active rooms
// or users it touches (the page passes the count); turning on does not ask.
import { CircleAlert, Power } from 'lucide-vue-next'
import { ref } from 'vue'

import { ApiError } from '../../api/errors'
import { useConfirm } from '../../composables/useConfirm'
import BaseButton from '../base/BaseButton.vue'

const props = defineProps<{
  active: boolean
  name: string
  kind: 'office' | 'building' | 'floor' | 'room type' | 'equipment' | 'department' | 'division' | 'position'
  /** How many active rooms or users it touches (the warning's number). */
  count: () => Promise<number>
  /** The page's PATCH of is_active; throws ApiError when the API refuses. */
  turn: (active: boolean) => Promise<void>
  /** Why it cannot turn now (e.g. unsaved changes): shown instead of turning. */
  blocked?: string
}>()

const { confirm } = useConfirm()
const busy = ref(false)
const error = ref('')

const AGAIN = 'You can turn it on again.'

// A place's rooms stop being bookable; rooms keep a room type or an item, and users keep their
// department, division or position — it only cannot be chosen again (the API changes nobody).
function warning(count: number | null): string {
  const one = count === 1
  const rooms = one ? '1 room' : `${count} rooms`
  const users = one ? '1 user' : `${count} users`
  if (props.kind === 'department') {
    // Its divisions stay on and still take new users (the API checks only the division).
    const divisions = 'Its divisions stay on, but no new division can be added to it.'
    if (count === null) return `Its users and divisions stay as they are, but no new division can be added to it. ${AGAIN}`
    if (count === 0) return `No users work in it. ${divisions} ${AGAIN}`
    return `${users} ${one ? 'works' : 'work'} in this department and ${one ? 'stays' : 'stay'} in it. ${divisions} ${AGAIN}`
  }
  if (props.kind === 'division') {
    if (count === null) return `Its users stay in it, but no new user can join it. ${AGAIN}`
    if (count === 0) return `No users work in it. ${AGAIN}`
    return `${users} ${one ? 'works' : 'work'} in this division and ${one ? 'stays' : 'stay'} in it. No new user can join it. ${AGAIN}`
  }
  if (props.kind === 'position') {
    if (count === null) return `Users with it keep it, but no new user can get it. ${AGAIN}`
    if (count === 0) return `No users have it. ${AGAIN}`
    return `${users} ${one ? 'has' : 'have'} this position and ${one ? 'keeps' : 'keep'} it. No new user can get it. ${AGAIN}`
  }
  if (props.kind === 'room type') {
    if (count === null) return `Rooms that use it keep it, but it cannot be chosen for other rooms. ${AGAIN}`
    if (count === 0) return `No rooms use it. ${AGAIN}`
    return `${rooms} ${one ? 'uses' : 'use'} this room type and ${one ? 'keeps' : 'keep'} it. It cannot be chosen for other rooms. ${AGAIN}`
  }
  if (props.kind === 'equipment') {
    if (count === null) return `Rooms that have it keep it, but it cannot be added to other rooms. ${AGAIN}`
    if (count === 0) return `No rooms have it. ${AGAIN}`
    return `${rooms} ${one ? 'has' : 'have'} this item and ${one ? 'keeps' : 'keep'} it. It cannot be added to other rooms. ${AGAIN}`
  }
  if (count === null) return `Its rooms stop being bookable. ${AGAIN}`
  if (count === 0) return `No rooms are affected. ${AGAIN}`
  return `${rooms} in this ${props.kind} ${one ? 'stops' : 'stop'} being bookable. ${AGAIN}`
}

async function run(active: boolean) {
  if (refuse()) return
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

function refuse(): boolean {
  error.value = props.blocked ?? ''
  return !!props.blocked
}

async function turnOff() {
  if (refuse()) return
  busy.value = true
  let count: number | null = null
  try {
    count = await props.count()
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
