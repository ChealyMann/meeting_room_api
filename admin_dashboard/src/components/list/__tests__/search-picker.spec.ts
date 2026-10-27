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
      searchable: true,
      modelValue,
      'onUpdate:modelValue': (value: string | number | null) => wrapper.setProps({ modelValue: value }),
    },
    attachTo: document.body,
  })
  return wrapper
}
const options = (wrapper: ReturnType<typeof mountPicker>) => wrapper.findAll('[role="option"]').map((o) => o.text())

const FIELD_WORDS = { all: 'Choose an office', search: 'Search offices', unknown: 'Unknown office', none: 'No office matches' }
const MANY: PickerItem[] = Array.from({ length: 9 }, (_, i) => ({ value: i + 1, label: `Office ${i + 1}` }))

function mountField(props: Record<string, unknown>) {
  const wrapper = mount(SearchPicker, {
    props: {
      id: 'location_id',
      mode: 'field' as const,
      words: FIELD_WORDS,
      'onUpdate:modelValue': (value: string | number | null) => wrapper.setProps({ modelValue: value }),
      ...props,
    },
    attachTo: document.body,
  })
  return wrapper
}

describe('SearchPicker as a form field', () => {
  it('says what to choose, offers no "all" row and no ×, and passes on the field state', async () => {
    const wrapper = mountField({ items: MANY, modelValue: null, invalid: true, describedBy: 'location_id-error' })
    const trigger = wrapper.get('#location_id')

    expect(trigger.text()).toBe('Choose an office')
    expect(trigger.classes()).toContain('empty')
    expect(trigger.attributes('aria-invalid')).toBe('true')
    expect(trigger.attributes('aria-describedby')).toBe('location_id-error')

    await trigger.trigger('click')
    expect(options(wrapper)[0]).toBe('Office 1')
    await wrapper.findAll('[role="option"]')[1]!.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([[2]])
    expect(wrapper.find('button.clear').exists()).toBe(false)
  })

  it('offers the empty choice when the field is optional', async () => {
    const wrapper = mountField({ items: MANY, modelValue: 3, nullable: true, words: { ...FIELD_WORDS, all: 'No owner' } })

    await wrapper.get('#location_id').trigger('click')
    expect(options(wrapper)[0]).toBe('No owner')
    await wrapper.findAll('[role="option"]')[0]!.trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([[null]])
  })

  it('does not open while disabled', async () => {
    const wrapper = mountField({ items: MANY, modelValue: null, disabled: true })

    await wrapper.get('#location_id').trigger('click')

    expect(wrapper.get('#location_id').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
  })

  it('leaves out the search box for a short list, and still works with the keyboard', async () => {
    const wrapper = mountField({ items: MANY.slice(0, 3), modelValue: null })

    await wrapper.get('#location_id').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="combobox"]').exists()).toBe(false)
    const list = wrapper.get('[role="listbox"]')
    expect(document.activeElement).toBe(list.element)

    await list.trigger('keydown', { key: 'ArrowDown' })
    await list.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('update:modelValue')).toEqual([[2]])
  })

  it('opens upward when there is no room below', async () => {
    const wrapper = mountField({ items: MANY, modelValue: null })
    const trigger = wrapper.get('#location_id').element
    trigger.getBoundingClientRect = () => ({ top: 700, bottom: 740, left: 40, right: 340, width: 300, height: 40, x: 40, y: 700, toJSON: () => ({}) })

    await wrapper.get('#location_id').trigger('click')
    await flushPromises()

    expect(wrapper.get('.pop').classes()).toContain('up')
  })
})

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
