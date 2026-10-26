import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { ApiError, networkError } from '../../api/errors'
import { useSessionStore } from '../../stores/session'
import NoAccessView from '../NoAccessView.vue'
import SignInView from '../SignInView.vue'

const Page = defineComponent({ render: () => h('p', 'page') })

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/sign-in', name: 'sign-in', component: Page },
      { path: '/no-access', name: 'no-access', component: Page },
      { path: '/', name: 'home', component: Page },
      { path: '/profile', name: 'profile', component: Page },
    ],
  })
}

async function mountSignIn(path = '/sign-in') {
  const router = makeRouter()
  await router.push(path)
  const session = useSessionStore()
  const wrapper = mount(SignInView, { global: { plugins: [router] } })
  return { wrapper, router, session }
}

async function submit(wrapper: Awaited<ReturnType<typeof mountSignIn>>['wrapper'], email: string, password: string) {
  await wrapper.get('#email').setValue(email)
  await wrapper.get('#password').setValue(password)
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('SignInView', () => {
  it('shows the API message on wrong credentials and keeps the email', async () => {
    const { wrapper, session } = await mountSignIn()
    vi.spyOn(session, 'signIn').mockRejectedValue(
      new ApiError(401, 'INVALID_CREDENTIALS', 'Wrong email or password.'),
    )

    await submit(wrapper, 'admin@company.com', 'bad')

    expect(wrapper.get('[role="alert"]').text()).toContain('Wrong email or password.')
    expect((wrapper.get('#email').element as HTMLInputElement).value).toBe('admin@company.com')
  })

  it('says how many minutes to wait after too many tries', async () => {
    const { wrapper, session } = await mountSignIn()
    vi.spyOn(session, 'signIn').mockRejectedValue(
      new ApiError(429, 'RATE_LIMITED', 'Too many failed sign-ins.', {}, 840),
    )

    await submit(wrapper, 'admin@company.com', 'bad')

    expect(wrapper.get('[role="alert"]').text()).toContain('Too many tries. Try again in 14 minutes.')
  })

  it('says "1 minute" when less than a minute is left', async () => {
    const { wrapper, session } = await mountSignIn()
    vi.spyOn(session, 'signIn').mockRejectedValue(
      new ApiError(429, 'RATE_LIMITED', 'Too many failed sign-ins.', {}, 45),
    )

    await submit(wrapper, 'admin@company.com', 'bad')

    expect(wrapper.get('[role="alert"]').text()).toContain('Too many tries. Try again in 1 minute.')
  })

  it('says when the server cannot be reached', async () => {
    const { wrapper, session } = await mountSignIn()
    vi.spyOn(session, 'signIn').mockRejectedValue(networkError(new TypeError('Failed to fetch')))

    await submit(wrapper, 'admin@company.com', 'pw')

    expect(wrapper.get('[role="alert"]').text()).toContain(
      "Can't reach the server. Check the API is running.",
    )
  })

  it('shows field errors from the API under the field', async () => {
    const { wrapper, session } = await mountSignIn()
    vi.spyOn(session, 'signIn').mockRejectedValue(
      new ApiError(422, 'VALIDATION_ERROR', 'Invalid request.', { email: 'Not a valid email.' }),
    )

    await submit(wrapper, 'admin', 'pw')

    expect(wrapper.get('#email-error').text()).toBe('Not a valid email.')
  })

  it('asks for both fields before calling the API', async () => {
    const { wrapper, session } = await mountSignIn()
    const signIn = vi.spyOn(session, 'signIn')

    await submit(wrapper, '  ', '')

    expect(signIn).not.toHaveBeenCalled()
    expect(wrapper.get('#email-error').text()).toBe('Enter your email.')
    expect(wrapper.get('#password-error').text()).toBe('Enter your password.')
  })

  it('sends the password untrimmed and is busy while waiting', async () => {
    const { wrapper, session } = await mountSignIn()
    let finish: () => void = () => {}
    const signIn = vi
      .spyOn(session, 'signIn')
      .mockImplementation(() => new Promise<void>((resolve) => (finish = resolve)))

    await wrapper.get('#email').setValue(' admin@company.com ')
    await wrapper.get('#password').setValue(' pw with spaces ')
    await wrapper.get('form').trigger('submit')

    expect(signIn).toHaveBeenCalledWith('admin@company.com', ' pw with spaces ')
    const button = wrapper.get('button[type="submit"]')
    expect(button.attributes('aria-busy')).toBe('true')
    expect(button.attributes('disabled')).toBeDefined()

    finish()
    await flushPromises()
    expect(wrapper.get('button[type="submit"]').attributes('aria-busy')).toBeUndefined()
  })

  it('goes to the redirect page after sign-in', async () => {
    const { wrapper, router, session } = await mountSignIn('/sign-in?redirect=/profile')
    vi.spyOn(session, 'signIn').mockResolvedValue()

    await submit(wrapper, 'admin@company.com', 'pw')

    expect(router.currentRoute.value.fullPath).toBe('/profile')
  })

  it('goes home without a redirect, and ignores redirects to other sites', async () => {
    const { wrapper, router, session } = await mountSignIn('/sign-in?redirect=//evil.example')
    vi.spyOn(session, 'signIn').mockResolvedValue()

    await submit(wrapper, 'admin@company.com', 'pw')

    expect(router.currentRoute.value.name).toBe('home')
  })

  it('shows and hides the password', async () => {
    const { wrapper } = await mountSignIn()
    const toggle = wrapper.get('button[aria-label="Show password"]')

    await toggle.trigger('click')

    expect(wrapper.get('#password').attributes('type')).toBe('text')
    expect(toggle.attributes('aria-pressed')).toBe('true')
  })
})

describe('SignInView forgot password', () => {
  it('says who resets a password, without calling the API', async () => {
    const { wrapper, session } = await mountSignIn()
    const signIn = vi.spyOn(session, 'signIn')
    const link = wrapper.get('button.forgot')
    expect(link.attributes('aria-expanded')).toBe('false')

    await link.trigger('click')

    expect(link.attributes('aria-expanded')).toBe('true')
    expect(wrapper.get('#forgot-note').text()).toContain('Ask an administrator to reset your password.')
    expect(signIn).not.toHaveBeenCalled()
  })
})

describe('NoAccessView', () => {
  it('says the user has no access and signs out', async () => {
    const router = makeRouter()
    await router.push('/no-access')
    const session = useSessionStore()
    const signOut = vi.spyOn(session, 'signOut').mockResolvedValue()
    const wrapper = mount(NoAccessView, { global: { plugins: [router] } })

    expect(wrapper.text()).toContain('You do not have access')

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(signOut).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.name).toBe('sign-in')
  })
})
