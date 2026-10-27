import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import type { LocationOut } from '../../../api/types'
import OfficePicker from '../OfficePicker.vue'

enableAutoUnmount(afterEach)

const office = (id: number, name_en: string, province: string, is_active = true) =>
  ({ id, name_en, name_kh: `ការិយាល័យ ${id}`, province: { code: province.toUpperCase(), name_en: province, name_kh: '' }, is_active }) as LocationOut
const OFFICES = [
  office(4, 'Battambang Branch', 'Battambang'),
  office(3, 'Head Office', 'Phnom Penh'),
  office(5, 'Siem Reap Branch', 'Siem Reap'),
  office(6, 'Old Branch', 'Kampot', false),
]

function mountPicker(modelValue: number | null = null) {
  const wrapper = mount(OfficePicker, {
    props: {
      id: 'filter-office',
      offices: OFFICES,
      modelValue,
      'onUpdate:modelValue': (value: number | null) => wrapper.setProps({ modelValue: value }),
    },
    attachTo: document.body,
  })
  return wrapper
}
const trigger = (wrapper: ReturnType<typeof mountPicker>) => wrapper.get('#filter-office')
const options = (wrapper: ReturnType<typeof mountPicker>) =>
  wrapper.findAll('[role="option"]').map((o) => o.text())
async function open(wrapper: ReturnType<typeof mountPicker>) {
  await trigger(wrapper).trigger('click')
  await flushPromises()
}

describe('OfficePicker', () => {
  it('shows "All offices" and lists main offices first, then the branches, without the ones that are off', async () => {
    const wrapper = mountPicker()
    expect(trigger(wrapper).text()).toBe('All offices')

    await open(wrapper)

    expect(trigger(wrapper).attributes('aria-expanded')).toBe('true')
    expect(document.activeElement?.getAttribute('role')).toBe('combobox')
    expect(options(wrapper)).toEqual(['All offices', 'Head Office', 'Battambang Branch', 'Siem Reap Branch'])
    expect(wrapper.find('[role="separator"]').exists()).toBe(true)
  })

  it('finds offices by English name, Khmer name or province, with the match in bold', async () => {
    const wrapper = mountPicker()
    await open(wrapper)

    await wrapper.get('[role="combobox"]').setValue('siem')
    expect(options(wrapper)).toEqual(['Siem Reap Branch'])
    expect(wrapper.get('[role="option"] mark').text()).toBe('Siem')

    await wrapper.get('[role="combobox"]').setValue('phnom')
    expect(options(wrapper)).toEqual(['Head Office'])

    await wrapper.get('[role="combobox"]').setValue('zzz')
    expect(wrapper.text()).toContain('No office matches “zzz”.')
  })

  it('chooses with a click, closes and gives focus back to the button', async () => {
    const wrapper = mountPicker()
    await open(wrapper)

    await wrapper.findAll('[role="option"]').find((o) => o.text() === 'Siem Reap Branch')!.trigger('click')
    await flushPromises()

    expect(wrapper.emitted('update:modelValue')).toEqual([[5]])
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
    expect(document.activeElement).toBe(trigger(wrapper).element)
    expect(trigger(wrapper).text()).toBe('Siem Reap Branch')
  })

  it('chooses with the arrow keys and Enter', async () => {
    const wrapper = mountPicker()
    await open(wrapper)
    const input = wrapper.get('[role="combobox"]')

    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'ArrowDown' })
    expect(input.attributes('aria-activedescendant')).toBe(wrapper.findAll('[role="option"]')[2]!.attributes('id'))
    await input.trigger('keydown', { key: 'Enter' })

    expect(wrapper.emitted('update:modelValue')).toEqual([[4]])
  })

  it('closes on Escape without changing anything, and keeps Escape from closing anything else', async () => {
    const wrapper = mountPicker(3)
    await open(wrapper)

    const escape = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })
    wrapper.get('[role="combobox"]').element.dispatchEvent(escape)
    await flushPromises()

    expect(escape.defaultPrevented).toBe(true)
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('closes when you click outside', async () => {
    const wrapper = mountPicker()
    await open(wrapper)

    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await flushPromises()

    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
  })

  it('clears the chosen office with ×', async () => {
    const wrapper = mountPicker(5)

    await wrapper.get('button[aria-label="Show all offices"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([[null]])
  })

  it('keeps a chosen office that is off, or gone, and says so', async () => {
    const off = mountPicker(6)
    expect(trigger(off).text()).toBe('Old Branch (off)')
    await open(off)
    expect(options(off)).toContain('Old Branch (off)')
    off.unmount()

    const gone = mountPicker(99)
    expect(trigger(gone).text()).toBe('Unknown office')
  })
})
