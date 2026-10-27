import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import type { EquipmentOut, RoomDetail } from '../../api/types'
import { useToast } from '../../composables/useToast'
import { useSessionStore } from '../../stores/session'
import RoomEquipment from '../rooms/RoomEquipment.vue'
import RoomFormPanel from '../rooms/RoomFormPanel.vue'
import RoomsView from '../RoomsView.vue'

enableAutoUnmount(afterEach)

const item = (id: number, name: string, is_active = true): EquipmentOut => ({
  id,
  name,
  icon: null,
  sort_order: id,
  is_active,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
})
const ALL = [item(1, 'Projector'), item(2, 'Whiteboard'), item(3, 'Old TV', false)]

const NEW_ROOM = {
  id: 99,
  name_en: 'Mekong Room',
  name_kh: 'បន្ទប់មេគង្គ',
  short_desc: null,
  description: null,
  capacity: 12,
  size_sqm: null,
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
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

const calls: Array<{ method: string; path: string; body?: string }> = []
let putAnswer: (ids: number[]) => Response

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const page = <T>(items: T[]) => ({ items, page: 1, size: 100, total: items.length })

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useToast().toasts.value = []
  calls.length = 0
  putAnswer = (ids) => json({ items: ALL.filter((e) => ids.includes(e.id)), total: ids.length })
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      calls.push({ method, path: url.pathname + url.search, body: init?.body ? String(init.body) : undefined })
      if (url.pathname === '/api/v1/equipment') return json(page(ALL))
      if (url.pathname === '/api/v1/rooms/12/equipment' && method === 'PUT') {
        return putAnswer(JSON.parse(String(init!.body)).equipment_ids)
      }
      if (url.pathname === '/api/v1/rooms/99') return json(NEW_ROOM)
      if (url.pathname === '/api/v1/rooms') return json({ items: [], page: 1, size: 20, total: 0 })
      return json(page([]))
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

describe('RoomEquipment', () => {
  async function mountList(equipment: EquipmentOut[]) {
    const wrapper = mount(RoomEquipment, { props: { roomId: 12, equipment } })
    await flushPromises()
    return wrapper
  }
  const box = (wrapper: Awaited<ReturnType<typeof mountList>>, name: string) =>
    wrapper.findAll('label.check').find((l) => l.text().startsWith(name))
  const saveButton = (wrapper: Awaited<ReturnType<typeof mountList>>) =>
    wrapper.findAll('button').find((b) => b.text() === 'Save equipment')!

  it("shows each item's icon beside its name, as the equipment list does", async () => {
    ALL[0] = { ...item(1, 'Projector'), icon: 'projector' }
    const wrapper = await mountList([])
    ALL[0] = item(1, 'Projector')

    const [projector, whiteboard] = wrapper.findAll('label')
    expect(projector!.find('svg.lucide-projector').exists()).toBe(true)
    expect(projector!.find('svg.lucide-projector').attributes('aria-hidden')).toBe('true')
    expect(whiteboard!.find('svg.lucide').exists()).toBe(false)
  })

  it('offers active equipment and keeps an inactive item the room has, marked off', async () => {
    const wrapper = await mountList([item(3, 'Old TV', false), item(1, 'Projector')])

    expect(wrapper.findAll('label.check').map((l) => l.text())).toEqual(['Projector', 'Whiteboard', 'Old TV (off)'])
    expect((box(wrapper, 'Projector')!.get('input').element as HTMLInputElement).checked).toBe(true)
    expect((box(wrapper, 'Whiteboard')!.get('input').element as HTMLInputElement).checked).toBe(false)
    expect((box(wrapper, 'Old TV')!.get('input').element as HTMLInputElement).checked).toBe(true)
  })

  it('saves only when the set changed, and drops an unticked inactive item for good', async () => {
    const wrapper = await mountList([item(3, 'Old TV', false), item(1, 'Projector')])
    expect(saveButton(wrapper).attributes('disabled')).toBeDefined()

    await box(wrapper, 'Old TV')!.get('input').setValue(false)
    expect(saveButton(wrapper).attributes('disabled')).toBeUndefined()
    await saveButton(wrapper).trigger('click')
    await flushPromises()

    expect(calls.find((c) => c.method === 'PUT')?.body).toBe('{"equipment_ids":[1]}')
    expect(wrapper.findAll('label.check').map((l) => l.text())).toEqual(['Projector', 'Whiteboard'])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Equipment saved')
    const events = wrapper.emitted('change') ?? []
    expect((events[events.length - 1]![0] as EquipmentOut[]).map((e) => e.id)).toEqual([1])
  })

  it('shows the API message when the save is refused', async () => {
    putAnswer = () => json({ error: { code: 'INACTIVE_REFERENCE', message: 'Whiteboard is turned off.' } }, 409)
    const wrapper = await mountList([item(1, 'Projector')])

    await box(wrapper, 'Whiteboard')!.get('input').setValue(true)
    await saveButton(wrapper).trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('Whiteboard is turned off.')
  })
})

describe('Creating a room in steps', () => {
  it('goes from the form to photos, then equipment, then closes', async () => {
    const router: Router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', name: 'home', component: RoomsView }],
    })
    await router.push('/?room=new')
    const wrapper = mount(RoomsView, { global: { plugins: [router] }, attachTo: document.body })
    await flushPromises()

    wrapper.findComponent(RoomFormPanel).vm.$emit('saved', NEW_ROOM as unknown as RoomDetail)
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ room: '99', step: 'photos' })
    const dialog = () => document.body.querySelector('[role="dialog"]')!
    expect(dialog().textContent).toContain('Step 2 of 3 · Photos')

    ;[...dialog().querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Next: equipment')!.click()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ room: '99', step: 'equipment' })
    expect(dialog().textContent).toContain('Step 3 of 3 · Equipment')

    const roomListCalls = () => calls.filter((c) => c.path.startsWith('/api/v1/rooms?')).length
    const before = roomListCalls()
    ;[...dialog().querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Done')!.click()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
    expect(roomListCalls()).toBeGreaterThan(before)
  })
})
