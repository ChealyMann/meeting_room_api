import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'

import { ApiError } from '../../api/errors'
import SecretReveal from '../SecretReveal.vue'

enableAutoUnmount(afterEach)

let writeText: ReturnType<typeof vi.fn<(text: string) => Promise<void>>>

beforeEach(() => {
  writeText = vi.fn<(text: string) => Promise<void>>(async () => {})
  vi.stubGlobal('navigator', { clipboard: { writeText } })
})
afterEach(() => vi.unstubAllGlobals())

function mountReveal(reveal: () => Promise<string | null>, extra?: string) {
  return mount(SecretReveal, {
    props: { label: 'door code', reveal, emptyText: 'No door code set' },
    slots: extra ? { extra: () => h('span', { class: 'extra' }, extra) } : {},
  })
}
const button = (wrapper: ReturnType<typeof mountReveal>, label: string) => wrapper.find(`button[aria-label="${label}"]`)

describe('SecretReveal', () => {
  it('shows masked dots and asks for nothing until the eye is pressed', async () => {
    const reveal = vi.fn<() => Promise<string | null>>(async () => '4821#')
    const wrapper = mountReveal(reveal)

    expect(wrapper.get('[aria-label="Door code hidden"]').text()).toBe('•••••')
    expect(button(wrapper, 'Show door code').exists()).toBe(true)
    expect(reveal).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('4821#')
  })

  it('shows the code with Copy and Hide after the eye is pressed', async () => {
    const reveal = vi.fn<() => Promise<string | null>>(async () => '4821#')
    const wrapper = mountReveal(reveal, 'Valid until 12 Nov')

    await button(wrapper, 'Show door code').trigger('click')
    await flushPromises()

    expect(reveal).toHaveBeenCalledTimes(1)
    expect(wrapper.get('.secret-code').text()).toBe('4821#')
    expect(wrapper.get('.extra').text()).toBe('Valid until 12 Nov')
    expect(button(wrapper, 'Copy door code').text()).toBe('')
    expect(button(wrapper, 'Hide door code').exists()).toBe(true)
  })

  it('stays one row: the same buttons and no wrapping when shown', async () => {
    const wrapper = mountReveal(async () => '4821#', 'Expired')
    const roundButtons = () => wrapper.findAll('button.round').length
    expect(roundButtons()).toBe(1)

    await button(wrapper, 'Show door code').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('button').every((b) => b.classes('round'))).toBe(true)
    expect(roundButtons()).toBe(2)
    expect(wrapper.find('.shown .extra').exists()).toBe(true)
  })

  it('copies the code and says so', async () => {
    const wrapper = mountReveal(async () => '4821#')
    await button(wrapper, 'Show door code').trigger('click')
    await flushPromises()

    await button(wrapper, 'Copy door code').trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith('4821#')
    expect(wrapper.get('[role="status"]').text()).toBe('Copied')
  })

  it('hides the code again and tells the parent', async () => {
    const wrapper = mountReveal(async () => '4821#')
    await button(wrapper, 'Show door code').trigger('click')
    await flushPromises()

    await button(wrapper, 'Hide door code').trigger('click')

    expect(wrapper.text()).not.toContain('4821#')
    expect(wrapper.find('[aria-label="Door code hidden"]').exists()).toBe(true)
    expect(wrapper.emitted('hide')).toHaveLength(1)
  })

  it('says when there is no code', async () => {
    const wrapper = mountReveal(async () => null)

    await button(wrapper, 'Show door code').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('No door code set')
    expect(button(wrapper, 'Copy door code').exists()).toBe(false)
    expect(button(wrapper, 'Hide door code').exists()).toBe(true)
  })

  it("shows the API's refusal and lets the eye try again", async () => {
    const wrapper = mountReveal(async () => Promise.reject(new ApiError(404, 'NOT_FOUND', 'No door pass yet.')))

    await button(wrapper, 'Show door code').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('No door pass yet.')
    expect(wrapper.find('[aria-label="Door code hidden"]').exists()).toBe(false)
    expect(button(wrapper, 'Show door code').exists()).toBe(true)
  })
})
