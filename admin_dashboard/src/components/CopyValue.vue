<script setup lang="ts">
// A value you click to copy (owner, 19 Nov 2026: "just click to copy", no Copy button): the
// booker's phone and email in To review. A copy icon shows on hover, a green tick for a moment
// after the click, and a toast says what was copied. The click stays here, so a row under it
// does not open.
import { Check, Copy } from 'lucide-vue-next'
import { onBeforeUnmount, ref } from 'vue'

import { useToast } from '../composables/useToast'

const props = defineProps<{
  value: string
  /** What it is, for the toast and the hover title: "Phone", "Email". */
  what: string
}>()

const toast = useToast()
const copied = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

/** The old way, for where the clipboard is off: the app opened by its LAN address over http. */
function copyByHand(text: string): boolean {
  const box = document.createElement('textarea')
  box.value = text
  box.setAttribute('readonly', '')
  box.style.cssText = 'position:fixed;top:0;left:0;opacity:0'
  document.body.appendChild(box)
  box.select()
  try {
    return document.execCommand('copy')
  } catch {
    return false
  } finally {
    box.remove()
  }
}

async function copy() {
  let done = false
  try {
    await navigator.clipboard.writeText(props.value)
    done = true
  } catch {
    done = copyByHand(props.value)
  }
  if (!done) {
    toast.show(`Could not copy the ${props.what.toLowerCase()}`, 'Select it and copy it by hand.')
    return
  }
  toast.show(`${props.what} copied`, props.value)
  copied.value = true
  clearTimeout(timer)
  timer = setTimeout(() => (copied.value = false), 1400)
}
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <button
    type="button"
    class="copy-value"
    :class="{ copied }"
    :title="`Click to copy the ${what.toLowerCase()}`"
    :aria-label="`Copy the ${what.toLowerCase()}: ${value}`"
    @click.stop="copy"
    @keydown.enter.stop
  ><span class="v">{{ value }}</span><Check v-if="copied" class="ok" aria-hidden="true" /><Copy v-else class="cp" aria-hidden="true" /></button>
</template>

<style scoped>
.copy-value {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  margin: -2px -6px;
  padding: 2px 6px;
  border: 0;
  border-radius: 7px;
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: copy;
  transition: background-color 140ms ease;
}
.v {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.copy-value svg {
  flex: none;
  width: 13px;
  height: 13px;
}
.cp {
  color: var(--color-ink-off);
  opacity: 0;
  transition: opacity 140ms ease;
}
.ok {
  color: var(--color-ok);
}
@media (hover: hover) and (pointer: fine) {
  .copy-value:hover {
    background: var(--color-field-disabled);
  }
  .copy-value:hover .cp {
    opacity: 1;
  }
}
.copy-value:focus-visible {
  outline: 2px solid var(--color-crimson);
  outline-offset: 1px;
}
.copy-value:focus-visible .cp {
  opacity: 1;
}
@media (prefers-reduced-motion: reduce) {
  .copy-value,
  .cp {
    transition-duration: 1ms;
  }
}
</style>
