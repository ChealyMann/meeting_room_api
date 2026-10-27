<script setup lang="ts">
// The Active switch for a place, a catalog record, an organisation record or a user (DSH-G07,
// P05, C01, C02, O01–O03, U03). Making it inactive asks in the confirm dialog and says what happens
// to the active rooms or users it touches (the page passes the count); making it active does not
// ask. The switch moves only when the page's record changes, never before the API answers
// (owner decision, 27 Oct 2026: a switch labelled Active/Inactive, not a Turn off button).
import { CircleAlert } from 'lucide-vue-next'
import { ref, useId } from 'vue'

import { ApiError } from '../../api/errors'
import { useConfirm } from '../../composables/useConfirm'

const props = defineProps<{
  active: boolean
  name: string
  kind: 'room' | 'office' | 'building' | 'floor' | 'room type' | 'equipment' | 'department' | 'division' | 'position' | 'user'
  /** How many active rooms or users it touches (the warning's number); a room has none to count. */
  count?: () => Promise<number>
  /** The page's PATCH of is_active; throws ApiError when the API refuses. */
  turn: (active: boolean) => Promise<void>
  /** Why it cannot turn now (e.g. unsaved changes): shown instead of turning. */
  blocked?: string
  /** Why it can never turn here (e.g. your own user): the switch looks off-limits, names the reason on hover, and a click says it. */
  locked?: string
}>()

const lockId = useId()

const { confirm } = useConfirm()
const busy = ref(false)
const error = ref('')

const AGAIN = 'You can make it active again.'

// A place's rooms stop being bookable; rooms keep a room type or an item, and users keep their
// department, division or position — it only cannot be chosen again (the API changes nobody).
function warning(count: number | null): string {
  const one = count === 1
  const rooms = one ? '1 room' : `${count} rooms`
  const users = one ? '1 user' : `${count} users`
  if (props.kind === 'room') return `People can no longer book it. ${AGAIN}`
  if (props.kind === 'user') {
    // The count is the rooms they own: turning them off clears the owner (R9).
    if (!count) return 'They cannot sign in until you make them active again.'
    return `They cannot sign in, and ${rooms} ${one ? 'loses its' : 'lose their'} owner. You can make them active again.`
  }
  if (props.kind === 'department') {
    // Its divisions stay active and still take new users (the API checks only the division).
    const divisions = 'Its divisions stay active, but no new division can be added to it.'
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
  error.value = props.locked ?? props.blocked ?? ''
  return !!error.value
}

function flip() {
  if (busy.value) return
  if (props.active) void turnOff()
  else void run(true)
}

async function turnOff() {
  if (refuse()) return
  busy.value = true
  let count: number | null = null
  try {
    count = props.count ? await props.count() : null
  } catch {
    count = null // still ask, with the general warning
  } finally {
    busy.value = false
  }
  const ok = await confirm({
    title: `Make ${props.name} inactive?`,
    text: warning(count),
    confirmLabel: 'Make inactive',
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
    <!-- A locked switch stays focusable (aria-disabled), so its reason can be read and clicked for. -->
    <button
      type="button"
      role="switch"
      class="switch"
      aria-label="Active"
      :aria-checked="active"
      :aria-busy="busy || undefined"
      :aria-disabled="locked ? 'true' : undefined"
      :aria-describedby="locked ? lockId : undefined"
      :title="locked"
      :class="{ locked: !!locked, busy }"
      @click="flip"
    />
    <span class="state" :class="{ off: !active }" aria-hidden="true">{{ active ? 'Active' : 'Inactive' }}</span>
    <span v-if="locked" :id="lockId" class="sr-only">{{ locked }}</span>
  </div>
</template>

<style scoped>
.toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
}
.switch.locked,
.switch.busy {
  opacity: 0.5;
  cursor: not-allowed;
}
.state {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-ink);
  white-space: nowrap;
}
.state.off {
  color: var(--color-intaglio);
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
