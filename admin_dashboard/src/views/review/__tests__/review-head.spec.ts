import { enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import ReviewHead from '../ReviewHead.vue'

enableAutoUnmount(afterEach)

const SUMMARY = { waiting: 3, approved_today: 5, rejected_today: 1 }
const tabs = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[role="tab"]')

describe('ReviewHead', () => {
  it('shows today in a ring, one line, and the tabs with their numbers', () => {
    const wrapper = mount(ReviewHead, { props: { summary: SUMMARY, tab: 'approved' } })

    expect(wrapper.get('h1').text()).toBe('To review')
    expect(wrapper.get('.today-ring').text()).toBe('6/9')
    expect(wrapper.get('.today-ring').attributes('aria-label')).toBe('6 of 9 decided today')
    expect(wrapper.get('.sub').text()).toBe('Today you decided 6 · 3 still waiting')
    expect(tabs(wrapper).map((t) => t.text())).toEqual(['Waiting3', 'Approved5', 'Rejected1'])
    expect(tabs(wrapper).map((t) => t.attributes('aria-selected'))).toEqual(['false', 'true', 'false'])
  })

  it('says which tab was picked', async () => {
    const wrapper = mount(ReviewHead, { props: { summary: SUMMARY, tab: 'waiting' } })

    await tabs(wrapper)[1]!.trigger('click')
    await tabs(wrapper)[2]!.trigger('keydown', { key: 'ArrowRight' })

    expect(wrapper.emitted('select')).toEqual([['approved'], ['waiting']])
  })

  it('moves the focus with the arrow keys, so every tab can be reached', async () => {
    const wrapper = mount(ReviewHead, { props: { summary: SUMMARY, tab: 'waiting' }, attachTo: document.body })
    ;(tabs(wrapper)[0]!.element as HTMLElement).focus()

    await tabs(wrapper)[0]!.trigger('keydown', { key: 'ArrowRight' })
    await wrapper.setProps({ tab: 'approved' })
    expect(document.activeElement).toBe(tabs(wrapper)[1]!.element)

    await tabs(wrapper)[1]!.trigger('keydown', { key: 'ArrowRight' })
    await wrapper.setProps({ tab: 'rejected' })
    expect(document.activeElement).toBe(tabs(wrapper)[2]!.element)
    expect(wrapper.emitted('select')).toEqual([['approved'], ['rejected']])
  })

  it('shows the tabs without numbers and no ring text before the summary loads', () => {
    const wrapper = mount(ReviewHead, { props: { summary: null, tab: 'waiting' } })

    expect(tabs(wrapper).map((t) => t.text())).toEqual(['Waiting', 'Approved', 'Rejected'])
    expect(wrapper.get('.today-ring').text()).toBe('')
    expect(wrapper.find('.sub').exists()).toBe(false)
  })
})
