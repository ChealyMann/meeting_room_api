import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import TimePicker from '../TimePicker.vue'

enableAutoUnmount(afterEach)

/** The picker with a v-model, as a form uses it. */
function mountPicker(start = '08:00') {
  const value = ref(start)
  const Host = defineComponent({
    setup: () => () =>
      h(TimePicker, { id: 'start_time', label: 'Opening', modelValue: value.value, 'onUpdate:modelValue': (v: string) => (value.value = v) }),
  })
  const wrapper = mount(Host, { attachTo: document.body })
  return { wrapper, value }
}

const trigger = () => document.getElementById('start_time') as HTMLButtonElement
const column = (name: string) => document.querySelector<HTMLElement>(`[role="listbox"][aria-label="${name}"]`)!
const options = (name: string) => [...column(name).querySelectorAll<HTMLElement>('[role="option"]')]
const option = (name: string, text: string) => options(name).find((o) => o.textContent?.trim() === text)!
const selected = (name: string) => options(name).find((o) => o.getAttribute('aria-selected') === 'true')?.textContent?.trim()
async function key(el: HTMLElement, k: string) {
  el.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true }))
  await flushPromises()
}

describe('TimePicker', () => {
  it('shows the time on a button, not a browser time box', () => {
    mountPicker('08:00')

    expect(trigger().tagName).toBe('BUTTON')
    expect(trigger().textContent).toContain('08:00')
    expect(document.querySelector('input[type="time"]')).toBeNull()
  })

  it('opens hour and minute columns with the current time picked', async () => {
    mountPicker('08:00')
    trigger().click()
    await flushPromises()

    expect(options('Hour').map((o) => o.textContent?.trim())).toEqual(Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0')))
    expect(options('Minute').map((o) => o.textContent?.trim())).toEqual(Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, '0')))
    expect(selected('Hour')).toBe('08')
    expect(selected('Minute')).toBe('00')
    expect(trigger().getAttribute('aria-expanded')).toBe('true')
  })

  it('sets the hour, then the minute, and closes', async () => {
    const { value } = mountPicker('08:00')
    trigger().click()
    await flushPromises()

    option('Hour', '09').click()
    await flushPromises()
    expect(value.value).toBe('09:00')
    expect(column('Minute')).toBeTruthy()

    option('Minute', '30').click()
    await flushPromises()
    expect(value.value).toBe('09:30')
    expect(document.querySelector('[role="listbox"]')).toBeNull()
  })

  it('works from the keyboard: arrows, Enter to pick, and Escape', async () => {
    const { value } = mountPicker('08:00')
    trigger().click()
    await flushPromises()

    expect(document.activeElement).toBe(column('Hour'))
    await key(column('Hour'), 'ArrowDown')
    await key(column('Hour'), 'Enter')
    expect(value.value).toBe('09:00')
    expect(document.activeElement).toBe(column('Minute'))

    await key(column('Minute'), 'ArrowDown')
    await key(column('Minute'), 'ArrowDown')
    await key(column('Minute'), 'Enter')
    expect(value.value).toBe('09:10')
    expect(document.querySelector('[role="listbox"]')).toBeNull()
    expect(document.activeElement).toBe(trigger())

    trigger().click()
    await flushPromises()
    await key(column('Hour'), 'ArrowUp')
    await key(column('Hour'), 'Escape')
    expect(value.value).toBe('09:10')
    expect(document.querySelector('[role="listbox"]')).toBeNull()
  })

  it('keeps a minute that is not on the 5-minute steps', async () => {
    mountPicker('08:07')
    trigger().click()
    await flushPromises()

    expect(selected('Minute')).toBe('07')
    expect(options('Minute').map((o) => o.textContent?.trim())).toContain('05')
  })
})
