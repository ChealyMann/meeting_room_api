import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import { useConfirm } from '../../../composables/useConfirm'
import ConfirmHost from '../ConfirmHost.vue'

enableAutoUnmount(afterEach)
afterEach(() => {
  document.body.innerHTML = ''
})

const dialog = () => document.body.querySelector('[role="alertdialog"]') as HTMLElement | null
const buttonIn = (text: string) =>
  [...(dialog()?.querySelectorAll('button') ?? [])].find((b) => b.textContent?.trim() === text) as HTMLButtonElement

async function open(extra: Record<string, unknown> = {}) {
  mount(ConfirmHost, { attachTo: document.body })
  const answer = useConfirm().confirm({
    title: 'Turn off Mekong Room?',
    text: 'People can no longer book it. You can turn it on again.',
    confirmLabel: 'Turn off',
    ...extra,
  })
  await nextTick()
  await nextTick()
  return answer
}

describe('confirm dialog', () => {
  it('shows the question as an alert dialog', async () => {
    void open()
    await flushPromises()

    expect(dialog()?.getAttribute('aria-modal')).toBe('true')
    expect(dialog()?.textContent).toContain('Turn off Mekong Room?')
    expect(dialog()?.textContent).toContain('People can no longer book it.')
    expect(buttonIn('Cancel')).toBeTruthy()
  })

  it('answers yes with the confirm button and closes', async () => {
    const answer = open()
    await flushPromises()

    buttonIn('Turn off').click()

    await expect(answer).resolves.toBe(true)
    await flushPromises()
    expect(dialog()).toBeNull()
  })

  it('answers no with Cancel, Escape or a click outside', async () => {
    let answer = open()
    await flushPromises()
    buttonIn('Cancel').click()
    await expect(answer).resolves.toBe(false)

    answer = useConfirm().confirm({ title: 'Delete photo 2?', confirmLabel: 'Delete photo' })
    await flushPromises()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await expect(answer).resolves.toBe(false)

    answer = useConfirm().confirm({ title: 'Delete photo 2?', confirmLabel: 'Delete photo' })
    await flushPromises()
    ;(document.body.querySelector('.confirm-backdrop') as HTMLElement).click()
    await expect(answer).resolves.toBe(false)
  })

  it('starts on Cancel, keeps focus inside, and gives it back afterwards', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()
    const answer = open()
    await flushPromises()

    expect(document.activeElement).toBe(buttonIn('Cancel'))
    buttonIn('Turn off').focus()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }))
    expect(document.activeElement).toBe(buttonIn('Cancel'))

    buttonIn('Cancel').click()
    await answer
    await flushPromises()
    expect(document.activeElement).toBe(opener)
  })
})
