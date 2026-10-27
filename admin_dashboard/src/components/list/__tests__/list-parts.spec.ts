import { enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import EmptyState from '../EmptyState.vue'
import { choosePicker } from '../../../test-utils/picker'
import PagingFoot from '../PagingFoot.vue'
import StateMarks from '../StateMarks.vue'
import StatusFilter from '../StatusFilter.vue'
import TableSkeleton from '../TableSkeleton.vue'

const pagerLabels = (wrapper: ReturnType<typeof mount>) =>
  wrapper.findAll('nav[aria-label="Pages"] > *').map((el) => el.text() || el.attributes('aria-label'))

enableAutoUnmount(afterEach)

describe('PagingFoot', () => {
  it('shows the range and moves between pages', async () => {
    const wrapper = mount(PagingFoot, { props: { page: 3, size: 20, total: 57 }, attachTo: document.body })

    expect(wrapper.get('.range').text()).toBe('41–57 of 57')
    expect(wrapper.get('button[aria-label="Next page"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('button[aria-label="Previous page"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('button[aria-current="page"]').text()).toBe('3')

    await wrapper.findAll('nav button').find((b) => b.text() === '2')!.trigger('click')
    expect(wrapper.emitted('update:page')?.[0]).toEqual([2])

    await choosePicker('rows-per-page', '50')
    expect(wrapper.emitted('update:size')?.[0]).toEqual([50])
  })

  it('shows 0 of 0 with both arrows off for an empty list', () => {
    const wrapper = mount(PagingFoot, { props: { page: 1, size: 20, total: 0 } })

    expect(wrapper.get('.range').text()).toBe('0 of 0')
    expect(wrapper.get('button[aria-label="Previous page"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('button[aria-label="Next page"]').attributes('disabled')).toBeDefined()
  })

  it('shows the first, the last and the pages around the current one', () => {
    const wrapper = mount(PagingFoot, { props: { page: 25, size: 20, total: 1000 } })

    expect(pagerLabels(wrapper)).toEqual([
      'Previous page', '1', '…', '24', '25', '26', '…', '50', 'Next page',
    ])
  })
})

describe('StatusFilter', () => {
  it('chooses a status and marks only that one as pressed', async () => {
    const wrapper = mount(StatusFilter, { props: { modelValue: 'active' } })

    await wrapper.findAll('button').find((b) => b.text() === 'All')!.trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['all'])
    await wrapper.setProps({ modelValue: 'all' })
    const pressed = wrapper.findAll('button[aria-pressed="true"]')
    expect(pressed.map((b) => b.text())).toEqual(['All'])
    expect(wrapper.get('[role="group"]').attributes('aria-label')).toBe('Status')
  })
})

describe('StateMarks', () => {
  it('shows only Inactive for a room that is off', () => {
    const text = mount(StateMarks, { props: { active: false, bookable: false } }).text()

    expect(text).toContain('Inactive')
    expect(text).not.toContain('Not bookable')
  })

  it('shows every mark that applies, each with a word', () => {
    const text = mount(StateMarks, { props: { active: true, bookable: false, private: true } }).text()

    expect(text).toContain('Active')
    expect(text).toContain('Not bookable')
    expect(text).toContain('Private')
  })

  it('marks Active with a circle check and Inactive with a dashed circle, never a dot', () => {
    const on = mount(StateMarks, { props: { active: true } })
    const off = mount(StateMarks, { props: { active: false } })

    expect(on.find('.state svg.lucide-circle-check').exists()).toBe(true)
    expect(off.find('.state svg.lucide-circle-dashed').exists()).toBe(true)
    expect(on.find('.state svg').attributes('aria-hidden')).toBe('true')
  })

  it('shows only the state for a record with no bookable mark (offices, buildings, floors)', () => {
    const text = mount(StateMarks, { props: { active: true } }).text()

    expect(text).toBe('Active')
  })
})

describe('EmptyState and TableSkeleton', () => {
  it('shows the heading, the text, the actions and a hidden watermark', () => {
    const wrapper = mount(EmptyState, {
      props: { title: 'No rooms yet', text: 'Add the first meeting room.' },
      slots: { default: '<button>New room</button>' },
    })

    expect(wrapper.text()).toContain('No rooms yet')
    expect(wrapper.text()).toContain('Add the first meeting room.')
    expect(wrapper.find('button').text()).toBe('New room')
    expect(wrapper.get('svg.watermark').attributes('aria-hidden')).toBe('true')
  })

  it('draws hidden rows that match the columns', () => {
    const wrapper = mount(TableSkeleton, { props: { columns: ['72px', '1fr', '96px'], rows: 3 } })

    expect(wrapper.attributes('aria-hidden')).toBe('true')
    expect(wrapper.findAll('.skeleton-row')).toHaveLength(3)
    expect(wrapper.findAll('.skeleton-row')[0]!.findAll('.skeleton-bar')).toHaveLength(3)
  })
})
