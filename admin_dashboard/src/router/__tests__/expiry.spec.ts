import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { RouterView } from 'vue-router'

const ME = {
  id: 1,
  staff_id: 'EMP-00002',
  title: null,
  name_en: 'Sok Dara',
  name_kh: 'សុខ ដារា',
  email: 'dara@company.com',
  secondary_email: null,
  phone: null,
  avatar_url: null,
  signature_url: null,
  email_notifications: true,
  division: null,
  department: null,
  position: { id: 9, name_en: 'IT Lead', name_kh: 'ប្រធានព័ត៌មានវិទ្យា' },
  province: null,
  roles: [{ code: 'ADMIN', name_en: 'Admin', name_kh: 'អ្នកគ្រប់គ្រង' }],
  owned_room_ids: [],
  is_active: true,
  must_change_password: false,
  last_login_at: null,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const unauthorized = () => json(401, { error: { code: 'UNAUTHORIZED', message: 'Please sign in.' } })

afterEach(() => {
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

describe('session lost mid-edit (DSH-A05, DSH-A06)', () => {
  it('goes to sign-in, then back to the same page with the typed values', async () => {
    // A fresh router module: its one-time restore and expire hook belong to this test's Pinia.
    vi.resetModules()
    const { default: router } = await import('../index')
    const { REFRESH_KEY } = await import('../../stores/session')
    const pinia = createPinia()
    setActivePinia(pinia)

    let refused = false
    let issued = 0
    const tokens = () => ({ access_token: `A${++issued}`, refresh_token: `R${issued}`, token_type: 'bearer' })
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async (input, init) => {
        const key = `${init?.method ?? 'GET'} ${new URL(String(input)).pathname}`
        if (key === 'POST /api/v1/auth/refresh') return refused ? unauthorized() : json(200, tokens())
        if (key === 'POST /api/v1/auth/login') {
          refused = false
          return json(200, tokens())
        }
        if (refused) return unauthorized()
        if (key === 'GET /api/v1/me') return json(200, ME)
        throw new Error(`unexpected call ${key}`)
      }),
    )
    sessionStorage.setItem(REFRESH_KEY, 'R0')

    const Root = defineComponent({ render: () => h(RouterView) })
    const wrapper = mount(Root, { global: { plugins: [pinia, router] }, attachTo: document.body })
    await router.push('/profile')
    await vi.waitFor(() => expect(wrapper.find('#phone').exists()).toBe(true))

    await wrapper.get('#phone').setValue('099 111 222')
    refused = true
    await wrapper.get('form').trigger('submit')

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('sign-in'))
    expect(router.currentRoute.value.query).toEqual({ redirect: '/profile' })

    await vi.waitFor(() => expect(wrapper.find('#email').exists()).toBe(true))
    await wrapper.get('#email').setValue('dara@company.com')
    await wrapper.get('#password').setValue('pw')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/profile'))
    await vi.waitFor(() =>
      expect((wrapper.get('#phone').element as HTMLInputElement).value).toBe('099 111 222'),
    )
    wrapper.unmount()
  })
})
