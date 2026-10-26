<script setup lang="ts">
// Create, edit and detail open here, over the list (DSH-G03, DESIGN.md "Side Panel").
// The list stays visible beside it; Escape and the scrim close it.
import { X } from 'lucide-vue-next'
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = defineProps<{ open: boolean; title: string; subtitle?: string; serial?: string }>()
const emit = defineEmits<{ close: [] }>()

const titleId = useId()
const panel = ref<HTMLElement | null>(null)
let opener: HTMLElement | null = null

const FIELDS = 'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])'

/** The first field that needs attention, else the first field, else the close button. */
function focusFirst() {
  const root = panel.value
  if (!root) return
  const target =
    root.querySelector<HTMLElement>('.panel-body [aria-invalid="true"]') ??
    root.querySelector<HTMLElement>(`.panel-body :is(${FIELDS})`) ??
    root.querySelector<HTMLElement>('button[aria-label="Close"]')
  target?.focus()
}

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
      document.addEventListener('keydown', onKey)
      await nextTick()
      focusFirst()
    } else {
      document.removeEventListener('keydown', onKey)
      opener?.focus()
      opener = null
    }
  },
  { immediate: true },
)

// The app removes panels with v-if instead of setting open=false: give focus back then too.
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  if (props.open && opener?.isConnected) opener.focus()
})

defineExpose({ focusFirst })
</script>

<template>
  <Teleport to="body">
    <Transition name="scrim" appear>
      <div v-if="open" class="scrim" aria-hidden="true" @click="emit('close')" />
    </Transition>
    <Transition name="panel" appear>
      <aside
        v-if="open"
        ref="panel"
        class="panel"
        role="dialog"
        aria-modal="false"
        :aria-labelledby="titleId"
      >
        <header class="panel-head">
          <div class="titles">
            <h2 :id="titleId">{{ title }}</h2>
            <span v-if="subtitle || serial" class="subtitle">
              <template v-if="subtitle">{{ subtitle }}</template>
              <template v-if="subtitle && serial"> · </template>
              <span v-if="serial" class="serial">
                <span class="prefix">{{ serial.split('·')[0] }}</span>·{{ serial.split('·')[1] }}
              </span>
            </span>
          </div>
          <button type="button" class="icon-btn" aria-label="Close" @click="emit('close')">
            <X aria-hidden="true" />
          </button>
        </header>
        <div class="panel-body">
          <slot />
        </div>
        <footer v-if="$slots.foot" class="panel-foot">
          <slot name="foot" />
        </footer>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.scrim {
  position: fixed;
  inset: 0;
  z-index: 35;
  background: var(--color-scrim);
}
.panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 36;
  display: flex;
  flex-direction: column;
  width: 440px;
  max-width: 100%;
  border-left: 1px solid var(--color-rule);
  background: var(--color-sheet);
  box-shadow: var(--shadow-panel);
}
.panel-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 16px 12px 16px 20px;
  border-bottom: 1px solid var(--color-rule);
}
.titles {
  min-width: 0;
}
/* The serial ends the second line: "Head Office · OF·0003". */
.subtitle .serial {
  font-size: 11.5px;
}
h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.35;
}
.subtitle {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.panel-head .icon-btn {
  margin-left: auto;
}
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 24px;
}
.panel-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--color-rule);
  background: var(--color-paper);
}

.panel-enter-active,
.panel-leave-active {
  transition: transform 280ms var(--ease-out-quint);
}
.panel-enter-from,
.panel-leave-to {
  transform: translateX(100%);
}
.scrim-enter-active,
.scrim-leave-active {
  transition: opacity 200ms ease;
}
.scrim-enter-from,
.scrim-leave-to {
  opacity: 0;
}

@media (max-width: 760px) {
  .panel {
    width: 100%;
  }
}
</style>
