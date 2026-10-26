import { ref } from 'vue'

export type ConfirmIcon = 'warning' | 'power' | 'trash'

export interface ConfirmOptions {
  title: string
  text?: string
  confirmLabel: string
  cancelLabel?: string
  icon?: ConfirmIcon
}

interface OpenConfirm extends ConfirmOptions {
  resolve(answer: boolean): void
}

// One dialog for the whole app (owner decision: a SweetAlert-style pop-up for every confirm).
// ConfirmHost, mounted once in App.vue, draws it.
const current = ref<OpenConfirm | null>(null)

function answer(value: boolean): void {
  const open = current.value
  current.value = null
  open?.resolve(value)
}

/** Ask a yes/no question. Resolves true for the confirm button, false for anything else. */
function confirm(options: ConfirmOptions): Promise<boolean> {
  answer(false) // a new question replaces an unanswered one
  return new Promise((resolve) => {
    current.value = { ...options, resolve }
  })
}

export function useConfirm() {
  return { current, confirm, answer }
}
