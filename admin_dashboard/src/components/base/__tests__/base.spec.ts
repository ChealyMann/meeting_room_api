import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'

import { useToast } from '../../../composables/useToast'
import AppToast from '../AppToast.vue'
import BaseButton from '../BaseButton.vue'
import BaseField from '../BaseField.vue'
import FormErrorSummary from '../FormErrorSummary.vue'

afterEach(() => {
  document.body.innerHTML = ''
  vi.useRealTimers()
})

describe('BaseButton', () => {
  it('is a plain secondary button by default', () => {
    const wrapper = mount(BaseButton, { slots: { default: 'Cancel' } })

    const button = wrapper.get('button')
    expect(button.attributes('type')).toBe('button')
    expect(button.classes()).toContain('btn')
    expect(button.attributes('disabled')).toBeUndefined()
  })

  it('is disabled while busy and keeps the slot text', () => {
    const wrapper = mount(BaseButton, {
      props: { variant: 'primary', busy: true, type: 'submit' },
      slots: { default: 'Saving' },
    })

    const button = wrapper.get('button')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('aria-busy')).toBe('true')
    expect(button.attributes('type')).toBe('submit')
    expect(button.classes()).toContain('primary')
    expect(button.text()).toContain('Saving')
    expect(wrapper.find('.spin').exists()).toBe(true)
  })
})

describe('BaseField', () => {
  it('shows the API error under the control, tied by id', () => {
    const wrapper = mount(BaseField, {
      props: { id: 'phone', label: 'Phone', error: 'Too long (max 20).' },
      slots: {
        default: (props: { describedBy?: string; invalid: boolean }) =>
          h('input', { id: 'phone', 'aria-describedby': props.describedBy, 'aria-invalid': props.invalid }),
      },
    })

    expect(wrapper.get('#phone-error').text()).toBe('Too long (max 20).')
    expect(wrapper.get('input').attributes('aria-describedby')).toBe('phone-error')
    expect(wrapper.get('input').attributes('aria-invalid')).toBe('true')
    expect(wrapper.classes()).toContain('has-error')
    expect(wrapper.get('label').attributes('for')).toBe('phone')
  })

  it('shows no error and the hint when there is no error', () => {
    const wrapper = mount(BaseField, {
      props: { id: 'phone', label: 'Phone', hint: 'optional' },
      slots: { default: () => h('input', { id: 'phone' }) },
    })

    expect(wrapper.find('#phone-error').exists()).toBe(false)
    expect(wrapper.classes()).not.toContain('has-error')
    expect(wrapper.get('label').text()).toContain('optional')
  })
})

describe('FormErrorSummary', () => {
  it('counts the fields and focuses one when its link is clicked', async () => {
    const input = document.createElement('input')
    input.id = 'phone'
    document.body.appendChild(input)
    const wrapper = mount(FormErrorSummary, {
      props: {
        errors: [
          { id: 'secondary_email', label: 'Second email' },
          { id: 'phone', label: 'Phone' },
        ],
      },
      attachTo: document.body,
    })

    expect(wrapper.get('[role="alert"]').text()).toContain('2 fields need attention:')
    const link = wrapper.findAll('a').find((a) => a.text() === 'Phone')
    await link!.trigger('click')

    expect(document.activeElement).toBe(input)
  })

  it('says "1 field" for one error and renders nothing for none', () => {
    const one = mount(FormErrorSummary, { props: { errors: [{ id: 'phone', label: 'Phone' }] } })
    expect(one.text()).toContain('1 field needs attention:')

    const none = mount(FormErrorSummary, { props: { errors: [] } })
    expect(none.find('[role="alert"]').exists()).toBe(false)
  })
})

describe('AppToast', () => {
  it('shows the newest toast and hides it after 4200 ms', async () => {
    vi.useFakeTimers()
    const wrapper = mount(AppToast)
    const { show } = useToast()

    show('Profile saved', 'admin@company.com')
    await nextTick()
    expect(wrapper.get('[role="status"]').text()).toContain('Profile saved')
    expect(wrapper.text()).toContain('admin@company.com')

    vi.advanceTimersByTime(4200)
    await nextTick()
    expect(wrapper.text()).not.toContain('Profile saved')
  })
})
