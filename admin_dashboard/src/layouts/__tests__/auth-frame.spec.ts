import { enableAutoUnmount, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import AuthFrame from '../AuthFrame.vue'

enableAutoUnmount(afterEach)

beforeEach(() => setActivePinia(createPinia()))

const mountFrame = () =>
  mount(AuthFrame, {
    props: { title: 'Sign in', subtitle: 'Continue to the meeting rooms dashboard' },
    slots: { default: '<form id="sign-in-form"></form>' },
  })

describe('AuthFrame', () => {
  it('puts the logo, the title, the form and the footer in one card', () => {
    const card = mountFrame().get('.card')

    expect(card.get('img.logo').attributes('src')).toBe('/nbc-logo.png')
    expect(card.get('h1').text()).toBe('Sign in')
    expect(card.text()).toContain('Continue to the meeting rooms dashboard')
    expect(card.find('#sign-in-form').exists()).toBe(true)
    expect(card.text()).toContain('Authorised NBC personnel only')
  })

  it('shows the logo on its own, with no filled seal behind it', () => {
    expect(mountFrame().find('.seal').exists()).toBe(false)
  })

  it('draws the temple behind the card, hidden from assistive tech', () => {
    const wrapper = mountFrame()

    expect(wrapper.get('.backdrop canvas.halftone').attributes('aria-hidden')).toBe('true')
    expect(wrapper.get('.backdrop').element.nextElementSibling?.classList.contains('card')).toBe(true)
  })
})
