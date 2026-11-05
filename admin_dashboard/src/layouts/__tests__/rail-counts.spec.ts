import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { REVIEW_SUMMARY_EVENT, reportWaiting } from '../../composables/useWaitingCounts'
import { useSessionStore } from '../../stores/session'
import AppRail from '../AppRail.vue'
import { NAV_GROUPS } from '../nav'

enableAutoUnmount(afterEach)

const Page = defineComponent({ render: () => h('p') })
const calls: string[] = []
let waiting: Record<string, number>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  calls.length = 0
  waiting = { pitika: 3, owner: 0 }
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      calls.push(url.pathname)
      const who = url.pathname.match(/^\/api\/v1\/(pitika|owner)\/bookings\/summary$/)?.[1]
      if (who) return json({ waiting: waiting[who], approved_today: 0, rejected_today: 0 })
      return json({ error: { code: 'NOT_FOUND', message: 'Not found.', fields: {} } }, 404)
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

async function mountRail(roles: string[]) {
  const session = useSessionStore()
  session.accessToken = 'A1'
  session.user = { id: 7, name_en: 'Keo Vanna', email: 'k@x.kh', roles: roles.map((code) => ({ code })), avatar_url: null } as never
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [...new Set(['profile', ...NAV_GROUPS.flatMap((g) => g.items.map((i) => i.route ?? 'profile'))])].map((name) => ({
      path: `/${name}`,
      name,
      component: Page,
    })),
  })
  await router.push('/bookings')
  const wrapper = mount(AppRail, { props: { open: false, compact: false }, global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return wrapper
}
const count = (wrapper: Awaited<ReturnType<typeof mountRail>>, route: string) =>
  wrapper.find(`a[href="/${route}"] .wait`).exists() ? wrapper.get(`a[href="/${route}"] .wait`).text() : null

describe('waiting counts in the menu', () => {
  it('shows how many bookings wait for a Pitika', async () => {
    const wrapper = await mountRail(['PITIKA'])
    expect(count(wrapper, 'review')).toBe('3')
    expect(wrapper.get('a[href="/review"] .wait').attributes('aria-label')).toBe('3 waiting')
    expect(calls).toEqual(['/api/v1/pitika/bookings/summary'])
  })

  it('shows nothing at 0', async () => {
    const wrapper = await mountRail(['ROOM_OWNER'])
    expect(count(wrapper, 'owner-review')).toBeNull()
  })

  it('shows both for a Pitika who also owns a room', async () => {
    waiting = { pitika: 3, owner: 2 }
    const wrapper = await mountRail(['PITIKA', 'ROOM_OWNER'])
    expect([count(wrapper, 'review'), count(wrapper, 'owner-review')]).toEqual(['3', '2'])
  })

  it('takes the newest number from the page, so the menu and the ring agree', async () => {
    const wrapper = await mountRail(['PITIKA'])
    reportWaiting('review', 2)
    await flushPromises()
    expect(count(wrapper, 'review')).toBe('2')
    expect(calls).toEqual(['/api/v1/pitika/bookings/summary'])
    expect(REVIEW_SUMMARY_EVENT).toBe('review:summary')
  })

  it('keeps the page number when the first load answers later', async () => {
    let release!: () => void
    const late = new Promise<void>((done) => (release = done))
    const real = globalThis.fetch
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
      await late
      return real(input, init)
    }))
    const wrapper = await mountRail(['PITIKA'])
    reportWaiting('review', 1)
    await flushPromises()
    release()
    await flushPromises()
    expect(count(wrapper, 'review')).toBe('1')
  })

  it('asks for nothing when the user reviews nothing', async () => {
    await mountRail(['ADMIN'])
    expect(calls).toEqual([])
  })
})
