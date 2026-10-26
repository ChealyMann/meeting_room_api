// Test helpers for the app's confirm dialog (ConfirmHost), which App.vue mounts once.
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'

import ConfirmHost from '../components/base/ConfirmHost.vue'
import { useConfirm } from '../composables/useConfirm'

let host: VueWrapper | null = null

/** Mount the dialog host (replacing one from an earlier test). */
export function mountConfirmHost(): void {
  host?.unmount()
  useConfirm().answer(false)
  host = mount(ConfirmHost, { attachTo: document.body })
}

export const confirmDialog = () => document.body.querySelector<HTMLElement>('[role="alertdialog"]')

/** Click a button in the open dialog by its text. */
export async function answerConfirm(label: string): Promise<void> {
  const button = [...(confirmDialog()?.querySelectorAll('button') ?? [])].find(
    (b) => b.textContent?.trim() === label,
  )
  if (!button) throw new Error(`no "${label}" button in the confirm dialog`)
  button.click()
  await flushPromises()
}
