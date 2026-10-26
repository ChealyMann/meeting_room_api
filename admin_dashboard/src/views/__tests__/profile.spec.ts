import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import { useSessionStore } from '../../stores/session'
import ProfileView from '../ProfileView.vue'

const ME = {
  id: 1,
  staff_id: 'EMP-00002',
  title: null,
  name_en: 'Sok Dara',
  name_kh: 'សុខ ដារា',
  email: 'dara@company.com',
  secondary_email: 'dara.home@example.com',
  phone: null,
  avatar_url: null,
  signature_url: null,
  email_notifications: true,
  division: { id: 25, name_en: 'Application Management', name_kh: 'គ្រប់គ្រងកម្មវិធី' },
  department: { id: 4, name_en: 'IT Department', name_kh: 'នាយកដ្ឋានព័ត៌មានវិទ្យា' },
  position: { id: 9, name_en: 'IT Lead', name_kh: 'ប្រធានព័ត៌មានវិទ្យា' },
  province: null,
  roles: [{ code: 'ADMIN', name_en: 'Admin', name_kh: 'អ្នកគ្រប់គ្រង' }],
  owned_room_ids: [],
  is_active: true,
  must_change_password: false,
  last_login_at: '2026-10-23T06:51:03Z',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-23T06:51:03Z',
}

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

type Route = (init: RequestInit) => Response

function stubApi(routes: Record<string, Route>) {
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const key = `${init?.method ?? 'GET'} ${new URL(String(input)).pathname}`
    const route = routes[key]
    if (!route) throw new Error(`unexpected call ${key}`)
    return route(init ?? {})
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const patchBodies = (fetchMock: ReturnType<typeof stubApi>) =>
  fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH').map(([, init]) => init?.body)

async function mountProfile() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/profile', name: 'profile', component: ProfileView },
      { path: '/change-password', name: 'change-password', component: defineComponent({ render: () => h('p') }) },
    ],
  })
  await router.push('/profile')
  const session = useSessionStore()
  session.accessToken = 'A1'
  const wrapper = mount(ProfileView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, session }
}

async function save(wrapper: Awaited<ReturnType<typeof mountProfile>>['wrapper']) {
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  setActivePinia(createPinia())
  useToast().toasts.value = []
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ProfileView', () => {
  it('shows skeleton lines while loading, then the details', async () => {
    let answer: (r: Response) => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(() => new Promise<Response>((resolve) => (answer = resolve))),
    )
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/profile', name: 'profile', component: ProfileView },
        { path: '/change-password', name: 'change-password', component: defineComponent({ render: () => h('p') }) },
      ],
    })
    await router.push('/profile')
    useSessionStore().accessToken = 'A1'
    const wrapper = mount(ProfileView, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('[data-skeleton]').exists()).toBe(true)

    answer(json(200, ME))
    await flushPromises()

    expect(wrapper.find('[data-skeleton]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Sok Dara')
    expect(wrapper.text()).toContain('សុខ ដារា')
    expect(wrapper.text()).toContain('EMP-00002')
    expect(wrapper.text()).toContain('IT Lead')
    expect(wrapper.text()).toContain('Application Management')
    expect(wrapper.text()).toContain('23 Oct 2026, 13:51')
  })

  it('sends only the changed phone', async () => {
    const fetchMock = stubApi({
      'GET /api/v1/me': () => json(200, ME),
      'PATCH /api/v1/me': () => json(200, { ...ME, phone: '012 345 678' }),
    })
    const { wrapper } = await mountProfile()

    await wrapper.get('#phone').setValue('012 345 678')
    await save(wrapper)

    expect(patchBodies(fetchMock)).toEqual(['{"phone":"012 345 678"}'])
  })

  it('sends null when the second email is cleared', async () => {
    const fetchMock = stubApi({
      'GET /api/v1/me': () => json(200, ME),
      'PATCH /api/v1/me': () => json(200, { ...ME, secondary_email: null }),
    })
    const { wrapper } = await mountProfile()

    await wrapper.get('#secondary_email').setValue('   ')
    await save(wrapper)

    expect(patchBodies(fetchMock)).toEqual(['{"secondary_email":null}'])
  })

  it('shows API field errors under the field and in the summary', async () => {
    stubApi({
      'GET /api/v1/me': () => json(200, ME),
      'PATCH /api/v1/me': () =>
        json(422, {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Invalid request.',
            fields: { secondary_email: 'Second email must be different.' },
          },
        }),
    })
    const { wrapper } = await mountProfile()

    await wrapper.get('#secondary_email').setValue('dara@company.com')
    await save(wrapper)

    expect(wrapper.get('#secondary_email-error').text()).toBe('Second email must be different.')
    const summary = wrapper.get('[role="alert"]')
    expect(summary.text()).toContain('1 field needs attention:')
    expect(summary.text()).toContain('Second email')
  })

  it('shows "Profile saved", clears the draft and updates the signed-in user', async () => {
    stubApi({
      'GET /api/v1/me': () => json(200, ME),
      'PATCH /api/v1/me': () => json(200, { ...ME, phone: '099 000 111' }),
    })
    const { wrapper, session } = await mountProfile()
    const drafts = useDraftsStore()

    await wrapper.get('#phone').setValue('099 000 111')
    expect(drafts.get('profile:1')).toBeDefined()
    await save(wrapper)

    expect(useToast().toasts.value.map((t) => t.title)).toContain('Profile saved')
    expect(drafts.get('profile:1')).toBeUndefined()
    expect(session.user?.phone).toBe('099 000 111')
  })

  it('does not send anything when nothing changed', async () => {
    const fetchMock = stubApi({ 'GET /api/v1/me': () => json(200, ME) })
    const { wrapper } = await mountProfile()

    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    await save(wrapper)

    expect(patchBodies(fetchMock)).toEqual([])
  })

  it('brings back a draft kept from before a forced sign-in', async () => {
    stubApi({ 'GET /api/v1/me': () => json(200, ME) })
    useDraftsStore().set('profile:1', {
      secondary_email: 'dara.home@example.com',
      phone: '012 999 888',
      avatar_url: '',
      email_notifications: false,
    })

    const { wrapper } = await mountProfile()

    expect((wrapper.get('#phone').element as HTMLInputElement).value).toBe('012 999 888')
    expect(wrapper.get('#email_notifications').attributes('aria-checked')).toBe('false')
  })
})

describe('ProfileView drafts and names', () => {
  it("never shows one user's unsaved draft to another user", async () => {
    let me: Record<string, unknown> = ME
    stubApi({ 'GET /api/v1/me': () => json(200, me) })
    const first = await mountProfile()
    await first.wrapper.get('#phone').setValue('099 111 222')
    first.wrapper.unmount()

    me = { ...ME, id: 2, staff_id: 'EMP-00003', email: 'other@company.com', phone: '011 000 000' }
    const second = await mountProfile()

    expect((second.wrapper.get('#phone').element as HTMLInputElement).value).toBe('011 000 000')
  })

  it('shows Khmer names under English ones', async () => {
    stubApi({ 'GET /api/v1/me': () => json(200, ME) })

    const { wrapper } = await mountProfile()

    for (const khmer of ['ប្រធានព័ត៌មានវិទ្យា', 'គ្រប់គ្រងកម្មវិធី', 'នាយកដ្ឋានព័ត៌មានវិទ្យា', 'អ្នកគ្រប់គ្រង']) {
      expect(wrapper.text()).toContain(khmer)
    }
  })
})
