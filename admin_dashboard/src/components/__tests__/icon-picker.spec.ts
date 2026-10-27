import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import IconPicker from '../IconPicker.vue'

const mountPicker = (modelValue: string | null) => mount(IconPicker, { props: { id: 'icon', modelValue } })
const radio = (wrapper: ReturnType<typeof mountPicker>, label: string) => wrapper.get(`[role="radio"][aria-label="${label}"]`)

describe('IconPicker', () => {
  it('previews the chosen icon and marks it in the grid', () => {
    const wrapper = mountPicker('projector')

    expect(wrapper.get('.preview').text()).toContain('projector')
    expect(radio(wrapper, 'Projector').attributes('aria-checked')).toBe('true')
    expect(radio(wrapper, 'TV').attributes('aria-checked')).toBe('false')
  })

  it('chooses an icon, or no icon', async () => {
    const wrapper = mountPicker('projector')

    await radio(wrapper, 'TV').trigger('click')
    await wrapper.findAll('button').find((b) => b.text() === 'No icon')!.trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([['tv'], [null]])
  })

  it('says when no icon matches the search, and keeps the choice', async () => {
    const wrapper = mountPicker('projector')

    await wrapper.get('input[type="search"]').setValue('zzz')

    expect(wrapper.text()).toContain('No icons match.')
    expect(wrapper.get('.preview').text()).toContain('projector')
  })

  it('finds icons by label', async () => {
    const wrapper = mountPicker(null)

    await wrapper.get('input[type="search"]').setValue('micro')

    expect(wrapper.findAll('[role="radio"]').map((r) => r.attributes('aria-label'))).toEqual(['Microphone'])
  })

  it('keeps an icon it does not know and says so', () => {
    const wrapper = mountPicker('old-icon')

    expect(wrapper.get('.preview').text()).toContain('Unknown icon')
    expect(wrapper.get('.preview').text()).toContain('old-icon')
  })

  it('moves focus and choice together after a search is cleared', async () => {
    const wrapper = mount(IconPicker, {
      props: { id: 'icon', modelValue: 'projector', 'onUpdate:modelValue': (v: string | null) => wrapper.setProps({ modelValue: v }) },
      attachTo: document.body,
    })
    const search = wrapper.get('input[type="search"]')
    await search.setValue('mic')
    await search.setValue('')

    await radio(wrapper, 'Projector').trigger('keydown', { key: 'ArrowRight' })
    await flushPromises()

    expect(wrapper.props('modelValue')).toBe('presentation')
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Presentation board')
    wrapper.unmount()
  })

  it('does not send the form on Enter in the search', async () => {
    const wrapper = mountPicker('projector')
    const enter = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true, bubbles: true })

    wrapper.get('input[type="search"]').element.dispatchEvent(enter)

    expect(enter.defaultPrevented).toBe(true)
  })

  it('clears the search on Escape instead of closing the panel, and lets Escape through when empty', async () => {
    const wrapper = mountPicker('projector')
    const search = wrapper.get('input[type="search"]')
    await search.setValue('mic')

    const first = new KeyboardEvent('keydown', { key: 'Escape', cancelable: true, bubbles: true })
    search.element.dispatchEvent(first)
    await flushPromises()
    expect(first.defaultPrevented).toBe(true)
    expect((search.element as HTMLInputElement).value).toBe('')

    const second = new KeyboardEvent('keydown', { key: 'Escape', cancelable: true, bubbles: true })
    search.element.dispatchEvent(second)
    expect(second.defaultPrevented).toBe(false)
  })

  it('moves with the arrow keys', async () => {
    const wrapper = mountPicker('projector')

    await radio(wrapper, 'Projector').trigger('keydown', { key: 'ArrowRight' })

    expect(wrapper.emitted('update:modelValue')).toEqual([['presentation']])
  })
})
