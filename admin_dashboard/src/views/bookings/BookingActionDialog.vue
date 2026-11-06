<script setup lang="ts">
// The confirm for an Admin booking action (cancel, reject, approve). Owner decisions, 5 Nov
// 2026: a pop-up instead of a step inside the panel, so the choice cannot be missed, in the
// "Ledger" style (option B of five, with rounded corners and no rule on top): left aligned like
// the side panel, the icon tile beside the question, and the booking as a small table
// so the Admin sees exactly which meeting they act on.
import { CalendarX2, CircleCheck, CircleX } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, type Component } from 'vue'

import BaseButton from '../../components/base/BaseButton.vue'

export type BookingAction = 'cancel' | 'approve' | 'reject'

const props = defineProps<{
  action: BookingAction
  title: string
  confirmLabel: string
  fieldLabel: string
  max: number
  meeting: string
  reference: string
  /** "Fri 6 Nov 2026" */
  day: string
  /** "14:00–15:30", or with "+2 more" for a booking with more sessions */
  times: string
  actingFor?: string
  effect: string
  busy: boolean
  allowed: boolean
  error?: string
  fieldError?: string
  /** A required reason's shortest length (Pitika reject: 5); 0 when the box is optional. */
  minLength?: number
  /** No text box (IT: Mark ready). A default slot can add content above the box (IT: the staff). */
  noField?: boolean
  /** Another icon in the tile (IT: assign staff). The `summary` slot can replace the booking
   *  table, and the `foot-start` slot puts something before Back. */
  icon?: Component
}>()
const text = defineModel<string>({ required: true })
const emit = defineEmits<{ back: []; confirm: [] }>()

/** Too short to send yet (only when a minimum is set). */
const short = computed(() => !!props.minLength && [...text.value.trim()].length < props.minLength)

const titleId = useId()
const effectId = useId()
const fieldId = useId()
const card = ref<HTMLElement | null>(null)
const field = ref<HTMLTextAreaElement | null>(null)
let opener: HTMLElement | null = null

// The reference's prefix is crimson, like every serial: "NBC" in "NBC-26-91768".
const refCut = props.reference.indexOf('-')
const refPrefix = refCut < 0 ? props.reference : props.reference.slice(0, refCut)
const refRest = refCut < 0 ? '' : props.reference.slice(refCut)

function back() {
  if (!props.busy) emit('back')
}

// Capture phase, so Escape closes only this dialog: the side panel under it checks
// `defaultPrevented` before it closes itself.
function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    back()
    return
  }
  if (event.key !== 'Tab' || !card.value) return
  const stops = [...card.value.querySelectorAll<HTMLElement>('input, textarea, button:not([disabled])')]
  const first = stops[0]
  const last = stops[stops.length - 1]
  if (!first || !last) return
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

onMounted(async () => {
  opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  document.addEventListener('keydown', onKey, true)
  await nextTick()
  if (field.value) field.value.focus()
  else card.value?.querySelector<HTMLElement>('input, button.confirm')?.focus()
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey, true)
  if (opener?.isConnected) opener.focus()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="action" appear>
      <div class="action-backdrop" @click.self="back">
        <div
          ref="card"
          class="action-dialog"
          :class="action"
          role="alertdialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          :aria-describedby="effectId"
        >
          <div class="head">
            <span class="tile" aria-hidden="true">
              <component :is="icon" v-if="icon" />
              <CalendarX2 v-else-if="action === 'cancel'" />
              <CircleX v-else-if="action === 'reject'" />
              <CircleCheck v-else />
            </span>
            <div class="question">
              <h2 :id="titleId">{{ title }}</h2>
              <p v-if="actingFor" class="acting">{{ actingFor }}</p>
              <p :id="effectId" class="effect">{{ effect }}</p>
            </div>
          </div>

          <slot name="summary">
          <dl class="booking">
            <div>
              <dt>Meeting</dt>
              <dd class="meeting">{{ meeting }}</dd>
            </div>
            <div>
              <dt>Reference</dt>
              <dd class="mono"><span class="prefix">{{ refPrefix }}</span>{{ refRest }}</dd>
            </div>
            <div>
              <dt>When</dt>
              <dd>{{ day }} · <span class="mono times">{{ times }}</span></dd>
            </div>
          </dl>
          </slot>

          <slot />

          <p v-if="noField && error" class="step-error" role="alert">{{ error }}</p>
          <div v-if="!noField" class="field">
            <label :for="fieldId">{{ fieldLabel }}</label>
            <textarea
              :id="fieldId"
              ref="field"
              v-model="text"
              rows="3"
              :maxlength="max"
              :disabled="busy"
              :aria-invalid="!!fieldError || undefined"
            />
            <div class="field-foot">
              <span v-if="fieldError" class="field-error" role="alert">{{ fieldError }}</span>
              <span v-else-if="short" class="field-hint">At least {{ minLength }} characters.</span>
              <span class="count">{{ [...text].length }}/{{ max }}</span>
            </div>
            <p v-if="error" class="step-error" role="alert">{{ error }}</p>
          </div>

          <div class="foot">
            <slot name="foot-start" />
            <BaseButton class="back" :disabled="busy" @click="back">Back</BaseButton>
            <BaseButton variant="primary" class="confirm" :busy="busy" :disabled="!allowed || short" @click="emit('confirm')">
              {{ confirmLabel }}
            </BaseButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.action-backdrop {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  padding: 16px;
  overflow-y: auto;
  background: rgba(23, 4, 4, 0.45);
}
.action-dialog {
  --tone: var(--color-crimson);
  --tone-wash: var(--color-crimson-wash);
  position: relative;
  width: 100%;
  max-width: 480px;
  overflow: hidden;
  border-radius: 14px;
  background: var(--color-sheet);
  box-shadow:
    0 24px 60px rgba(23, 4, 4, 0.35),
    0 2px 8px rgba(23, 4, 4, 0.2);
}
/* Approving moves the booking on, so it takes the ledger green instead of the danger crimson. */
.action-dialog.approve {
  --tone: var(--color-ok);
  --tone-wash: color-mix(in srgb, var(--color-ok) 10%, var(--color-sheet));
}
.head {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  gap: 16px;
  padding: 28px 24px 20px;
}
.tile {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: var(--tone-wash);
  color: var(--tone);
}
.tile :deep(svg.lucide) {
  width: 28px;
  height: 28px;
  stroke-width: 1.75;
}
h2 {
  margin: 2px 0 0;
  font-size: 19px;
  font-weight: 600;
  line-height: 1.3;
}
.acting {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-crimson);
}
.effect {
  margin: 6px 0 0;
  font-size: 13.5px;
  color: var(--color-intaglio);
}
.booking {
  margin: 0 24px;
  border-top: 1px solid var(--color-rule);
}
.booking > div {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px solid var(--color-rule);
}
.booking dt {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.booking dd {
  margin: 0;
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
.booking .meeting {
  font-weight: 500;
}
.mono {
  font-family: var(--font-mono);
  font-size: 12.5px;
}
.prefix {
  color: var(--color-crimson);
}
.times {
  white-space: nowrap;
}
.field {
  display: grid;
  gap: 6px;
  padding: 18px 24px 0;
}
.field label {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--color-intaglio);
}
.field textarea {
  min-height: 84px;
  padding: 8px 10px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font: 13.5px/1.5 var(--font-sans);
  resize: vertical;
}
.field textarea:focus-visible {
  outline: none;
  border-color: var(--color-crimson);
  box-shadow: var(--shadow-halo);
}
.field textarea[aria-invalid='true'] {
  border-color: var(--color-crimson);
  background: var(--color-error-field);
}
.field-foot {
  display: flex;
  gap: 12px;
}
.field-error,
.field-hint {
  font-size: 12.5px;
  color: var(--color-crimson);
}
.count {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--color-intaglio);
}
.step-error {
  margin: 6px 0 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-size: 13px;
  font-weight: 500;
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
  padding: 14px 24px;
  border-top: 1px solid var(--color-rule);
  background: var(--color-paper);
}
.foot .btn {
  min-width: 112px;
  height: 40px;
}

@media (max-width: 480px) {
  .head {
    grid-template-columns: 44px minmax(0, 1fr);
    gap: 12px;
    padding: 24px 16px 16px;
  }
  .tile {
    width: 44px;
    height: 44px;
    border-radius: 10px;
  }
  .tile :deep(svg.lucide) {
    width: 22px;
    height: 22px;
  }
  .booking {
    margin: 0 16px;
  }
  .booking > div {
    grid-template-columns: 84px minmax(0, 1fr);
  }
  .field {
    padding: 16px 16px 0;
  }
  .foot {
    padding: 12px 16px;
  }
  .foot .btn {
    flex: 1;
    min-width: 0;
  }
}

/* A short pop, like the Confirm Dialog; the global reduced-motion rule turns it off. */
.action-enter-active {
  transition: opacity 180ms ease;
}
.action-enter-active .action-dialog {
  transition: transform 260ms var(--ease-out-quint);
}
.action-enter-from {
  opacity: 0;
}
.action-enter-from .action-dialog {
  transform: scale(0.94);
}
</style>
