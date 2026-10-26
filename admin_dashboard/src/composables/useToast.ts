import { ref } from 'vue'

export interface Toast {
  id: number
  title: string
  detail?: string
}

const HIDE_AFTER_MS = 4200

// One list for the whole app: any view can show a toast; AppToast draws it.
const toasts = ref<Toast[]>([])
let nextId = 1

function show(title: string, detail?: string): void {
  const toast: Toast = { id: nextId++, title, detail }
  toasts.value.push(toast)
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== toast.id)
  }, HIDE_AFTER_MS)
}

export function useToast() {
  return { toasts, show }
}
