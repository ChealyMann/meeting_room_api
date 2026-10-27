import { flushPromises, mount } from '@vue/test-utils'
import { answerConfirm, confirmDialog, mountConfirmHost } from '../../test-utils/confirm'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSessionStore } from '../../stores/session'
import RoomDetailPanel from '../rooms/RoomDetailPanel.vue'

function room(overrides: Record<string, unknown> = {}) {
  return {
    id: 12,
    name_en: 'Mekong Room',
    name_kh: 'បន្ទប់មេគង្គ',
    short_desc: 'Small meetings',
    description: 'Screen and whiteboard.',
    capacity: 12,
    size_sqm: 40,
    start_time: '08:00',
    end_time: '17:00',
    category: { id: 1, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ' },
    floor: { id: 7, floor_label: '3rd floor' },
    building: { id: 5, name_en: 'Building A', name_kh: 'អគារ A', short_name: null },
    location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
    province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
    owner: null,
    cover_photo: null,
    is_active: true,
    is_bookable: true,
    is_private: false,
    photos: [],
    equipment: [],
    created_at: '2026-10-01T02:00:00Z',
    updated_at: '2026-10-23T06:51:03Z',
    ...overrides,
  }
}

let current: ReturnType<typeof room>
let doorCode: string | null
let patchAnswer: (body: Record<string, unknown>) => Response
const calls: Array<{ method: string; path: string; body?: string }> = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  current = room()
  doorCode = '4821#'
  calls.length = 0
  patchAnswer = (body) => {
    current = { ...current, ...body }
    return json(current)
  }
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const path = new URL(String(input)).pathname
      const method = init?.method ?? 'GET'
      calls.push({ method, path, body: init?.body ? String(init.body) : undefined })
      if (path === '/api/v1/rooms/12/door-code') return json({ room_id: 12, door_code: doorCode })
      if (path === '/api/v1/rooms/12' && method === 'PATCH') return patchAnswer(JSON.parse(String(init!.body)))
      if (path === '/api/v1/rooms/12') return json(current)
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

async function mountPanel() {
  mountConfirmHost()
  const wrapper = mount(RoomDetailPanel, {
    props: { roomId: 12 },
    global: { stubs: { teleport: true } },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

const button = (wrapper: Awaited<ReturnType<typeof mountPanel>>, text: string, scope = '') =>
  wrapper.findAll(`${scope} button`).find((b) => b.text() === text)

describe('RoomDetailPanel', () => {
  it('shows the room, but never its door code on its own', async () => {
    const wrapper = await mountPanel()

    expect(wrapper.text()).toContain('បន្ទប់មេគង្គ')
    expect(wrapper.text()).toContain('RM·0012')
    expect(wrapper.text()).toContain('08:00–17:00')
    expect(wrapper.text()).toContain('Head Office › Building A › 3rd floor')
    expect(wrapper.text()).toContain('23 Oct 2026, 13:51')
    expect(wrapper.text()).not.toContain('4821#')
    expect(calls.some((c) => c.path.endsWith('/door-code'))).toBe(false)
  })

  it('shows the door code only when asked, and hides it again', async () => {
    const wrapper = await mountPanel()

    await button(wrapper, 'Show door code')!.trigger('click')
    await flushPromises()
    expect(calls.some((c) => c.path === '/api/v1/rooms/12/door-code')).toBe(true)
    expect(wrapper.get('.door-code').text()).toBe('4821#')

    await button(wrapper, 'Hide')!.trigger('click')
    expect(wrapper.text()).not.toContain('4821#')
  })

  it('says when no door code is set', async () => {
    doorCode = null
    const wrapper = await mountPanel()

    await button(wrapper, 'Show door code')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('No door code set')
  })

  it('asks before making a room inactive with its Active switch, then does it', async () => {
    const wrapper = await mountPanel()

    await wrapper.get('.panel-foot [role="switch"]').trigger('click')
    await flushPromises()
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
    expect(confirmDialog()?.textContent).toContain('Make Mekong Room inactive?')
    expect(confirmDialog()?.textContent).toContain('People can no longer book it. You can make it active again.')

    await answerConfirm('Make inactive')

    expect(calls.find((c) => c.method === 'PATCH')?.body).toBe('{"is_active":false}')
    expect(wrapper.emitted('changed')?.[0]?.[0]).toMatchObject({ is_active: false })
    expect(wrapper.text()).toContain('Inactive')
  })

  it('makes a room active, and shows the reason when the API refuses', async () => {
    current = room({ is_active: false })
    patchAnswer = () =>
      json({ error: { code: 'INACTIVE_REFERENCE', message: 'Turn on its floor first.' } }, 409)
    const wrapper = await mountPanel()

    await wrapper.get('.panel-foot [role="switch"]').trigger('click')
    await flushPromises()

    expect(calls.find((c) => c.method === 'PATCH')?.body).toBe('{"is_active":true}')
    expect(wrapper.get('[role="alert"]').text()).toContain('Turn on its floor first.')
    expect(wrapper.text()).toContain('Inactive')
    expect(wrapper.emitted('changed')).toBeUndefined()
  })

  it('asks the page to open the form with Edit', async () => {
    const wrapper = await mountPanel()

    await button(wrapper, 'Edit')!.trigger('click')

    expect(wrapper.emitted('edit')).toHaveLength(1)
  })
})

describe('RoomDetailPanel tabs', () => {
  it('shows the photo tools in the Photos tab', async () => {
    const wrapper = await mountPanel()

    await wrapper.findAll('[role="tab"]').find((t) => t.text().startsWith('Photos'))!.trigger('click')

    expect(wrapper.get('#tabpanel-photos').text()).toContain('Add photos')
    expect(wrapper.get('#tabpanel-photos').text()).toContain('0/20')
  })
})

describe('RoomDetailPanel opening', () => {
  it('opens only when the room has loaded, so it slides in once', async () => {
    let release: () => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(() => new Promise<Response>((resolve) => (release = () => resolve(json(room()))))),
    )
    const wrapper = mount(RoomDetailPanel, { props: { roomId: 12 }, global: { stubs: { teleport: true } } })
    await flushPromises()
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)

    release()
    await flushPromises()
    expect(wrapper.get('[role="dialog"]').text()).toContain('បន្ទប់មេគង្គ')
  })

  it('opens at once with a room it is given, and still refreshes it', async () => {
    const wrapper = mount(RoomDetailPanel, {
      props: { roomId: 12, initial: room({ name_en: 'Given Room' }) as never },
      global: { stubs: { teleport: true } },
    })
    expect(wrapper.get('[role="dialog"]').text()).toContain('Given Room')

    await flushPromises()
    expect(calls.some((c) => c.path === '/api/v1/rooms/12')).toBe(true)
    expect(wrapper.get('[role="dialog"]').text()).toContain('Mekong Room')
  })
})
