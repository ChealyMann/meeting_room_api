import { mount } from '@vue/test-utils'
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

  it('moves with the arrow keys', async () => {
    const wrapper = mountPicker('projector')

    await radio(wrapper, 'Projector').trigger('keydown', { key: 'ArrowRight' })

    expect(wrapper.emitted('update:modelValue')).toEqual([['presentation']])
  })
})
