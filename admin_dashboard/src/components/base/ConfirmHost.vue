<script setup lang="ts">
// The app's confirm dialog, SweetAlert-style (owner decision, 27 Oct 2026): a centred card
// with a large icon, the question, one line of consequence, and two buttons. Focus starts on
// the safe choice (Cancel), stays inside, and returns to the opener when it closes.
import { Power, Trash2, TriangleAlert } from 'lucide-vue-next'
import { nextTick, ref, useId, watch } from 'vue'

import { useConfirm } from '../../composables/useConfirm'

const { current, answer } = useConfirm()

const titleId = useId()
const textId = useId()
const card = ref<HTMLElement | null>(null)
const cancelButton = ref<HTMLButtonElement | null>(null)
let opener: HTMLElement | null = null

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    answer(false)
    return
  }
  if (event.key !== 'Tab' || !card.value) return
  const buttons = [...card.value.querySelectorAll<HTMLElement>('button')]
  const first = buttons[0]
  const last = buttons[buttons.length - 1]
  if (!first || !last) return
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  () => current.value !== null,
  async (open, wasOpen) => {
    if (open && !wasOpen) {
      opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
      document.addEventListener('keydown', onKey)
      await nextTick()
      cancelButton.value?.focus()
    } else if (!open && wasOpen) {
      document.removeEventListener('keydown', onKey)
      if (opener?.isConnected) opener.focus()
      opener = null
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm" appear>
      <div v-if="current" class="confirm-backdrop" @click.self="answer(false)">
        <div
          ref="card"
          class="confirm-card"
          role="alertdialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          :aria-describedby="current.text ? textId : undefined"
        >
          <span class="icon" aria-hidden="true">
            <Power v-if="current.icon === 'power'" />
            <Trash2 v-else-if="current.icon === 'trash'" />
            <TriangleAlert v-else />
          </span>
          <h2 :id="titleId">{{ current.title }}</h2>
          <p v-if="current.text" :id="textId">{{ current.text }}</p>
          <div class="buttons">
            <button ref="cancelButton" type="button" class="btn" @click="answer(false)">
              {{ current.cancelLabel ?? 'Cancel' }}
            </button>
            <button type="button" class="btn primary" @click="answer(true)">
              {{ current.confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(23, 4, 4, 0.45);
}
.confirm-card {
  display: grid;
  justify-items: center;
  width: 100%;
  max-width: 400px;
  padding: 32px 28px 24px;
  border-radius: 14px;
  background: var(--color-sheet);
  box-shadow:
    0 24px 60px rgba(23, 4, 4, 0.35),
    0 2px 8px rgba(23, 4, 4, 0.2);
  text-align: center;
}
.icon {
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  margin-bottom: 16px;
  border: 2px solid var(--color-danger-line);
  border-radius: 50%;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.icon :deep(svg.lucide) {
  width: 32px;
  height: 32px;
  stroke-width: 1.75;
}
h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
p {
  margin: 8px 0 0;
  max-width: 34ch;
  font-size: 14px;
  color: var(--color-intaglio);
}
.buttons {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}
.buttons .btn {
  min-width: 128px;
  height: 42px;
}

/* A short pop, like SweetAlert; the global reduced-motion rule turns it off. */
.confirm-enter-active {
  transition: opacity 180ms ease;
}
.confirm-enter-active .confirm-card {
  transition: transform 260ms var(--ease-out-quint);
}
.confirm-leave-active {
  transition: opacity 140ms ease;
}
.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}
.confirm-enter-from .confirm-card {
  transform: scale(0.94);
}
</style>
