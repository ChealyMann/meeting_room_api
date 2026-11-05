import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { clearDate, dateLabel, pickDate } from '../../../test-utils/datePicker'
import DatePicker from '../DatePicker.vue'

enableAutoUnmount(afterEach)

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-05T02:00:00Z')) // Thu 5 Nov 2026, 09:00 in Phnom Penh
})
afterEach(() => vi.useRealTimers())

/** A DatePicker bound to a ref, so a test can read what it sets. */
function mountPicker(start: string | null, props: Record<string, unknown> = {}) {
  const value = ref<string | null>(start)
  const Host = defineComponent({
    setup: () => () =>
      h(DatePicker, {
        id: 'day',
        label: 'Day',
        modelValue: value.value,
        'onUpdate:modelValue': (next: string | null) => (value.value = next),
        ...props,
      }),
  })
  const wrapper = mount(Host, { attachTo: document.body })
  return { wrapper, value }
}

const pop = () => document.querySelector<HTMLElement>('.date-picker .pop')
const title = () => pop()?.querySelector('.title')?.textContent?.trim()
const dayButton = (n: number) =>
  [...(pop()?.querySelectorAll<HTMLButtonElement>('.day:not(.other)') ?? [])].find((b) => b.textContent?.trim() === String(n))!
async function open() {
  document.querySelector<HTMLButtonElement>('#day')!.click()
  await flushPromises()
}
async function key(name: string) {
  document.activeElement!.dispatchEvent(new KeyboardEvent('keydown', { key: name, bubbles: true, cancelable: true }))
  await flushPromises()
}

describe('DatePicker', () => {
  it('shows the day in words, or the placeholder when empty', () => {
    mountPicker('2026-11-09')
    expect(dateLabel('day')).toBe('Mon 9 Nov 2026')
  })

  it('shows its placeholder when empty', () => {
    mountPicker(null, { placeholder: 'Any day' })
    expect(dateLabel('day')).toBe('Any day')
  })

  it('opens on the month of its day, Monday first, with today ringed and the day filled', async () => {
    mountPicker('2026-12-24')
    await open()

    expect(title()).toBe('December 2026')
    expect([...pop()!.querySelectorAll('th')].map((th) => th.textContent)).toEqual(['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'])
    expect(pop()!.querySelectorAll('.day')).toHaveLength(42)
    expect(dayButton(24).classList.contains('chosen')).toBe(true)
    expect(document.activeElement).toBe(dayButton(24))
  })

  it('opens on today when empty, and marks today', async () => {
    mountPicker(null)
    await open()

    expect(title()).toBe('November 2026')
    expect(dayButton(5).classList.contains('today')).toBe(true)
    expect(dayButton(5).getAttribute('aria-current')).toBe('date')
  })

  it('picks a day and closes', async () => {
    const { value } = mountPicker('2026-11-05')
    await pickDate('day', '2027-02-14')

    expect(value.value).toBe('2027-02-14')
    expect(pop()).toBeNull()
    expect(dateLabel('day')).toBe('Sun 14 Feb 2027')
  })

  it('moves by day, week and month with the keyboard, and picks with Enter', async () => {
    const { value } = mountPicker('2026-01-31')
    await open()

    await key('ArrowRight') // Sun 1 Feb
    await key('ArrowDown') // Sun 8 Feb
    await key('PageUp') // Thu 8 Jan
    await key('Home') // Mon 5 Jan
    expect(title()).toBe('January 2026')
    await key('Enter')

    expect(value.value).toBe('2026-01-05')
  })

  it('keeps the day inside a shorter month', async () => {
    const { value } = mountPicker('2027-01-31')
    await open()

    await key('PageDown')
    await key('Enter')

    expect(value.value).toBe('2027-02-28')
  })

  it('turns off days outside min and max', async () => {
    const { value } = mountPicker(null, { min: '2026-11-03', max: '2026-11-20' })
    await open()

    expect(dayButton(2).disabled).toBe(true)
    expect(dayButton(3).disabled).toBe(false)
    expect(dayButton(21).disabled).toBe(true)
    dayButton(2).click()
    await flushPromises()
    expect(value.value).toBeNull()

    await key('End') // Sun 8 Nov
    await key('ArrowDown') // 15
    await key('ArrowDown') // 22, past max: stops at 20
    await key('Enter')
    expect(value.value).toBe('2026-11-20')
  })

  it('picks today with Today, and empties with Clear when clearable', async () => {
    const { value } = mountPicker('2026-10-01', { clearable: true })
    await open()
    ;[...pop()!.querySelectorAll<HTMLButtonElement>('.foot button')].find((b) => b.textContent === 'Today')!.click()
    await flushPromises()
    expect(value.value).toBe('2026-11-05')

    await clearDate('day')
    expect(value.value).toBeNull()
  })

  it('has no Clear unless clearable', async () => {
    mountPicker('2026-11-05')
    await open()

    expect([...pop()!.querySelectorAll('.foot button')].map((b) => b.textContent)).toEqual(['Today'])
  })

  it('closes on Escape and marks the key as used, so a side panel stays open', async () => {
    mountPicker('2026-11-05')
    await open()
    const escape = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })
    document.activeElement!.dispatchEvent(escape)
    await flushPromises()

    expect(pop()).toBeNull()
    expect(escape.defaultPrevented).toBe(true)
    expect(document.activeElement).toBe(document.querySelector('#day'))
  })

  it('moves a month with the arrow buttons', async () => {
    mountPicker('2026-11-05')
    await open()

    pop()!.querySelector<HTMLButtonElement>('button[aria-label="Next month"]')!.click()
    await flushPromises()
    expect(title()).toBe('December 2026')
    pop()!.querySelector<HTMLButtonElement>('button[aria-label="Previous month"]')!.click()
    pop()!.querySelector<HTMLButtonElement>('button[aria-label="Previous month"]')!.click()
    await flushPromises()
    expect(title()).toBe('October 2026')
  })
})
