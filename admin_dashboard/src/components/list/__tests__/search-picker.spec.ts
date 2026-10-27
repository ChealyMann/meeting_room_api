import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import SearchPicker, { type PickerItem } from '../SearchPicker.vue'

enableAutoUnmount(afterEach)

const WORDS = {
  all: 'All provinces',
  search: 'Search provinces',
  unknown: 'Unknown province',
  none: 'No province matches',
  clear: 'Show all provinces',
}
const PROVINCES: PickerItem[] = [
  { value: 'PP', label: 'Phnom Penh', keywords: 'ភ្នំពេញ' },
  { value: 'SIEM_REAP', label: 'Siem Reap', keywords: 'សៀមរាប' },
]
const GROUPED: PickerItem[] = [
  { value: 10, label: 'IT Department', group: 'Head Office' },
  { value: 11, label: 'Human Resources', group: 'Head Office' },
  { value: 12, label: 'Branch Operations', group: 'Siem Reap Branch' },
]

function mountPicker(items: PickerItem[], modelValue: string | number | null = null) {
  const wrapper = mount(SearchPicker, {
    props: {
      id: 'picker',
      items,
      words: WORDS,
      modelValue,
      'onUpdate:modelValue': (value: string | number | null) => wrapper.setProps({ modelValue: value }),
    },
    attachTo: document.body,
  })
  return wrapper
}
const options = (wrapper: ReturnType<typeof mountPicker>) => wrapper.findAll('[role="option"]').map((o) => o.text())

describe('SearchPicker', () => {
  it('works with text values, and searches the keywords too', async () => {
    const wrapper = mountPicker(PROVINCES)
    expect(wrapper.get('#picker').text()).toBe('All provinces')

    await wrapper.get('#picker').trigger('click')
    await wrapper.get('[role="combobox"]').setValue('សៀម')
    expect(options(wrapper)).toEqual(['Siem Reap'])
    await wrapper.get('[role="option"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([['SIEM_REAP']])
    expect(wrapper.get('#picker').text()).toBe('Siem Reap')
  })

  it('uses its own words for an unknown value and for no match', async () => {
    const wrapper = mountPicker(PROVINCES, 'XX')
    expect(wrapper.get('#picker').text()).toBe('Unknown province')

    await wrapper.get('#picker').trigger('click')
    await wrapper.get('[role="combobox"]').setValue('zzz')
    expect(wrapper.text()).toContain('No province matches “zzz”.')
    expect(wrapper.find('button[aria-label="Show all provinces"]').exists()).toBe(true)
  })

  it('shows a heading over each named group', async () => {
    const wrapper = mountPicker(GROUPED)
    await wrapper.get('#picker').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('.heading').map((h) => h.text())).toEqual(['Head Office', 'Siem Reap Branch'])
    expect(options(wrapper)).toEqual(['All provinces', 'IT Department', 'Human Resources', 'Branch Operations'])

    await wrapper.get('[role="combobox"]').setValue('branch')
    expect(wrapper.findAll('.heading').map((h) => h.text())).toEqual(['Siem Reap Branch'])
  })
})
