import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'

import type { UserDetail } from '../../api/types'
import { useSessionStore } from '../../stores/session'
import AppShell from '../AppShell.vue'

const Page = defineComponent({ render: () => h('p', 'page') })
const Root = defineComponent({ render: () => h(RouterView) })

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/sign-in', name: 'sign-in', component: Page },
      {
        path: '/',
        component: AppShell,
        children: [
          { path: '', name: 'home', component: Page, meta: { title: 'Rooms' } },
          { path: 'profile', name: 'profile', component: Page, meta: { title: 'My profile' } },
          { path: 'offices', name: 'offices', component: Page, meta: { title: 'Offices' } },
        ],
      },
    ],
  })
}

async function mountShell(path = '/', avatarUrl: string | null = null) {
  const router = makeRouter()
  await router.push(path)
  const session = useSessionStore()
  session.accessToken = 'A1'
  session.user = {
    id: 1,
    name_en: 'Sok Dara',
    email: 'dara@company.com',
    roles: [{ code: 'ADMIN', name_en: 'Admin', name_kh: '' }],
    must_change_password: false,
    avatar_url: avatarUrl,
    updated_at: 't1',
  } as unknown as UserDetail
  const wrapper = mount(Root, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router, session }
}

beforeEach(() => {
  setActivePinia(createPinia())
  document.body.innerHTML = ''
})

describe('AppShell', () => {
  it('marks Rooms as the current page on home', async () => {
    const { wrapper } = await mountShell('/')

    const rooms = wrapper.get('a[aria-current="page"]')
    expect(rooms.text()).toContain('Rooms')
  })

  it('renders not-yet-built pages as disabled links', async () => {
    const { wrapper } = await mountShell('/')

    const roomTypes = wrapper.findAll('nav a').find((a) => a.text().includes('Room types'))
    expect(roomTypes?.attributes('aria-disabled')).toBe('true')
    expect(roomTypes?.attributes('title')).toBe('Coming soon')
    expect(roomTypes?.attributes('href')).toBeUndefined()
  })

  it('links Offices and marks it on its page', async () => {
    const { wrapper } = await mountShell('/offices')

    const current = wrapper.get('a[aria-current="page"]')
    expect(current.text()).toContain('Offices')
    expect(current.attributes('href')).toBe('/offices')
  })

  it('shows the signed-in user and the page title', async () => {
    const { wrapper } = await mountShell('/profile')

    expect(wrapper.text()).toContain('Sok Dara')
    expect(wrapper.text()).toContain('dara@company.com')
    expect(wrapper.text()).toContain('SD')
    expect(wrapper.get('header').text()).toContain('My profile')
    expect(wrapper.get('header').text()).toMatch(/Phnom Penh \d\d:\d\d/)
  })

  it('signs out and goes to sign-in', async () => {
    const { wrapper, router, session } = await mountShell('/')
    const signOut = vi.spyOn(session, 'signOut').mockResolvedValue()

    await wrapper.get('button[aria-label="Sign out"]').trigger('click')
    await flushPromises()

    expect(signOut).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.name).toBe('sign-in')
  })
})

describe('AppShell photo', () => {
  it('shows the user photo in the rail instead of initials', async () => {
    URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => 'blob:photo')
    URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>()
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async () => new Response('jpg')),
    )

    const { wrapper } = await mountShell('/', '/api/v1/users/1/avatar')

    expect(wrapper.get('.who img').attributes('src')).toBe('blob:photo')
    expect(wrapper.find('.who .initials').text()).toBe('')
    vi.unstubAllGlobals()
  })
})

describe('AppShell toggles', () => {
  it('folds the sidebar to icons and opens it again', async () => {
    localStorage.clear()
    const { wrapper } = await mountShell('/')

    await wrapper.get('button[aria-label="Collapse sidebar"]').trigger('click')

    expect(wrapper.get('aside.rail').classes()).toContain('compact')
    expect(wrapper.get('.shell').classes()).toContain('compact')
    expect(localStorage.getItem('nbc.admin.rail')).toBe('collapsed')

    await wrapper.get('button[aria-label="Expand sidebar"]').trigger('click')

    expect(wrapper.get('aside.rail').classes()).not.toContain('compact')
  })

  it('switches between day and night', async () => {
    localStorage.clear()
    const { wrapper } = await mountShell('/')
    expect(document.documentElement.dataset.theme).toBe('light')

    await wrapper.get('button[aria-label="Switch to night mode"]').trigger('click')

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(wrapper.find('button[aria-label="Switch to day mode"]').exists()).toBe(true)
  })
})
