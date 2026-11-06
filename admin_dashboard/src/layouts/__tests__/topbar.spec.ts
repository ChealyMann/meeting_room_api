import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useSessionStore } from '../../stores/session'
import AppTopbar from '../AppTopbar.vue'

const Page = defineComponent({ render: () => h('p') })

async function titleAt(roles: string[], name: string, metaTitle: string) {
  useSessionStore().user = { roles: roles.map((code) => ({ code })) } as never
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/x', name, component: Page, meta: { title: metaTitle } }] })
  await router.push('/x')
  const wrapper = mount(AppTopbar, { props: { menuOpen: false }, global: { plugins: [router] } })
  return wrapper.text()
}

beforeEach(() => setActivePinia(createPinia()))

describe('AppTopbar title', () => {
  it('says My rooms on the owner page of a Pitika who owns a room', async () => {
    expect(await titleAt(['PITIKA', 'ROOM_OWNER'], 'owner-review', 'To review')).toContain('My rooms')
  })

  it('keeps the page title otherwise', async () => {
    expect(await titleAt(['ROOM_OWNER'], 'owner-review', 'To review')).toContain('To review')
    expect(await titleAt(['ADMIN'], 'profile', 'My profile')).toContain('My profile')
  })
})

describe('AppTopbar clock', () => {
  afterEach(() => vi.useRealTimers())

  it("shows today's date and the time in Phnom Penh, and turns the day at midnight there", async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-06T16:59:00Z')) // 23:59 on Fri 6 Nov in Phnom Penh
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/x', component: Page }] })
    await router.push('/x')
    const wrapper = mount(AppTopbar, { props: { menuOpen: false }, global: { plugins: [router] } })
    expect(wrapper.find('.clock').text()).toBe('Phnom Penh Fri 6 Nov 2026 23:59')

    await vi.advanceTimersByTimeAsync(60_000)
    expect(wrapper.find('.clock').text()).toBe('Phnom Penh Sat 7 Nov 2026 00:00')
    wrapper.unmount()
  })
})
