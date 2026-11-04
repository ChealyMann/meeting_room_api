<script setup lang="ts">
// A secret shown only on request (DSH-R05, DSH-B03): masked dots and a round eye button; the
// code is fetched only when the eye is pressed, then shows in mono with round Copy and Hide
// buttons. One row, one height in every state (owner decision, 4 Nov 2026: "masked dots", no
// size change).
import { Check, Copy, Eye, EyeOff, LoaderCircle } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import { ApiError } from '../api/errors'

const props = defineProps<{
  /** What it is, lower case: "door code", "door pass". */
  label: string
  /** Fetch the secret; null = none is set. */
  reveal: () => Promise<string | null>
  /** Said when `reveal` gives null. */
  emptyText?: string
}>()
const emit = defineEmits<{ hide: [] }>()
defineSlots<{ extra?: () => unknown }>()

// undefined = hidden; null = asked, none set; string = shown.
const code = ref<string | null | undefined>(undefined)
const busy = ref(false)
const error = ref('')
const copied = ref(false)

const Label = computed(() => props.label.charAt(0).toUpperCase() + props.label.slice(1))

async function show() {
  busy.value = true
  error.value = ''
  try {
    code.value = await props.reveal()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    busy.value = false
  }
}

function hide() {
  code.value = undefined
  copied.value = false
  emit('hide')
}

async function copy() {
  if (!code.value) return
  try {
    await navigator.clipboard.writeText(code.value)
    copied.value = true
  } catch {
    error.value = 'Could not copy. Select the code instead.'
  }
}
</script>

<template>
  <div class="secret">
    <template v-if="code === undefined">
      <span v-if="error" class="error" role="alert">{{ error }}</span>
      <span v-else class="dots" :aria-label="`${Label} hidden`">•••••</span>
      <button type="button" class="round" :aria-label="`Show ${label}`" :disabled="busy" @click="show">
        <LoaderCircle v-if="busy" class="spin" aria-hidden="true" />
        <Eye v-else aria-hidden="true" />
      </button>
    </template>
    <template v-else>
      <span v-if="code === null" class="none">{{ emptyText ?? 'None set' }}</span>
      <span v-else class="shown">
        <span class="secret-code">{{ code }}</span>
        <slot name="extra" />
      </span>
      <span class="actions">
        <button v-if="code" type="button" class="round" :aria-label="`Copy ${label}`" :title="copied ? 'Copied' : 'Copy'" @click="copy">
          <Check v-if="copied" aria-hidden="true" />
          <Copy v-else aria-hidden="true" />
        </button>
        <button type="button" class="round on" :aria-label="`Hide ${label}`" @click="hide">
          <EyeOff aria-hidden="true" />
        </button>
      </span>
    </template>
    <span class="sr-only" role="status">{{ copied ? 'Copied' : '' }}</span>
  </div>
</template>

<style scoped>
.secret {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: 36px;
}
.dots {
  font-family: var(--font-mono);
  font-size: 18px;
  letter-spacing: 0.3em;
  color: var(--color-off-ring);
}
.shown {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
/* Sized so a door pass (NBC- and 5 digits) and its "Expired" tag fit beside the two buttons in
   the panel's value column: the code is never cut. */
.secret-code {
  flex: none;
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--color-ink);
  white-space: nowrap;
}
.none {
  font-size: 13.5px;
  color: var(--color-ink-off);
}
.actions {
  display: flex;
  flex: none;
  gap: 6px;
}
.round {
  height: 36px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 999px;
  background: var(--color-sheet);
  color: var(--color-intaglio);
  cursor: pointer;
}
.round {
  display: grid;
  flex: none;
  place-items: center;
  width: 36px;
  padding: 0;
}
.round:hover {
  border-color: var(--color-intaglio);
  color: var(--color-ink);
}
.round.on {
  border-color: var(--color-crimson);
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.round:focus-visible {
  outline: none;
  box-shadow: var(--shadow-halo);
}
.round:disabled {
  cursor: wait;
}
.round svg {
  width: 17px;
  height: 17px;
}
.error {
  min-width: 0;
  overflow: hidden;
  font-size: 12.5px;
  color: var(--color-crimson);
  white-space: nowrap;
  text-overflow: ellipsis;
}
.spin {
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .spin {
    animation: none;
  }
}
</style>
