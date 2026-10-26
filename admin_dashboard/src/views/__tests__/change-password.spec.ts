import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { ApiError } from '../../api/errors'
import type { UserDetail } from '../../api/types'
import { useToast } from '../../composables/useToast'
import { useSessionStore } from '../../stores/session'
import ChangePasswordView from '../ChangePasswordView.vue'

const Page = defineComponent({ render: () => h('p', 'page') })

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/change-password', name: 'change-password', component: Page },
      { path: '/sign-in', name: 'sign-in', component: Page },
      { path: '/', name: 'home', component: Page },
      { path: '/profile', name: 'profile', component: Page },
    ],
  })
  await router.push('/change-password')
  const session = useSessionStore()
  session.accessToken = 'A1'
  session.user = {
    id: 1,
    email: 'admin@company.com',
    roles: [],
    must_change_password: true,
  } as unknown as UserDetail
  const wrapper = mount(ChangePasswordView, { global: { plugins: [router] } })
  return { wrapper, router, session }
}

type Wrapper = Awaited<ReturnType<typeof mountView>>['wrapper']

async function fill(wrapper: Wrapper, current: string, next: string, confirm = next) {
  await wrapper.get('#current_password').setValue(current)
  await wrapper.get('#new_password').setValue(next)
  await wrapper.get('#confirm_password').setValue(confirm)
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  setActivePinia(createPinia())
  useToast().toasts.value = []
})

describe('ChangePasswordView', () => {
  it('shows a wrong current password under "Current password"', async () => {
    const { wrapper, session } = await mountView()
    vi.spyOn(session, 'changePassword').mockRejectedValue(
      new ApiError(400, 'WRONG_PASSWORD', 'Current password is wrong.'),
    )

    await fill(wrapper, 'not it', 'a new password')

    expect(wrapper.get('#current_password-error').text()).toBe('Current password is wrong.')
  })

  it('shows an API rule under "New password"', async () => {
    const { wrapper, session } = await mountView()
    vi.spyOn(session, 'changePassword').mockRejectedValue(
      new ApiError(422, 'VALIDATION_ERROR', 'Invalid request.', {
        new_password: 'Password must be 8 to 128 characters.',
      }),
    )

    await fill(wrapper, 'old password', 'a new password')

    expect(wrapper.get('#new_password-error').text()).toBe('Password must be 8 to 128 characters.')
  })

  it('checks the rules before calling the API', async () => {
    const { wrapper, session } = await mountView()
    const change = vi.spyOn(session, 'changePassword')

    await fill(wrapper, 'old password', 'ADMIN@company.com')

    expect(change).not.toHaveBeenCalled()
    expect(wrapper.get('#new_password-error').text()).toBe('Password cannot be your email.')
  })

  it('says when the two new passwords do not match, without calling the API', async () => {
    const { wrapper, session } = await mountView()
    const change = vi.spyOn(session, 'changePassword')

    await fill(wrapper, 'old password', 'a new password', 'a new passwork')

    expect(change).not.toHaveBeenCalled()
    expect(wrapper.get('#confirm_password-error').text()).toBe('The passwords do not match.')
  })

  it('changes the password, shows a toast and goes home', async () => {
    const { wrapper, router, session } = await mountView()
    const change = vi.spyOn(session, 'changePassword').mockResolvedValue()

    await fill(wrapper, 'old password', ' a new password ')

    expect(change).toHaveBeenCalledWith('old password', ' a new password ')
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Password changed')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('lets a user who must change their password sign out instead', async () => {
    const { wrapper, router, session } = await mountView()
    const signOut = vi.spyOn(session, 'signOut').mockResolvedValue()

    await wrapper.get('button.sign-out').trigger('click')
    await flushPromises()

    expect(signOut).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.name).toBe('sign-in')
  })
})
