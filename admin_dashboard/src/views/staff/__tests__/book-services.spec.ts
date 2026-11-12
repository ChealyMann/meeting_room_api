import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useSessionStore } from '../../../stores/session'
import { bookingStubs, roomDetail, service } from '../../../test-utils/staff'
import BookView from '../BookView.vue'

enableAutoUnmount(afterEach)

const FOODS = [
  service(1, 'Coffee and tea', 'BREAKS'),
  service(2, 'Rice soup', 'BREAKFAST', 'Warm and steamed'),
  service(3, 'Lunch box', 'MEALS'),
  service(4, 'Fruit plate', null),
]
const ITS = [service(10, 'Projector', 'SCREENS'), service(11, 'Microphone', 'SOUND')]

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  vi.stubGlobal('fetch', bookingStubs(roomDetail(12, 'Mekong Room'), { foods: FOODS, its: ITS }).fetch)
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function step3(start = '08:00', end = '09:00') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/book/:roomId', name: 'book', component: BookView },
      { path: '/find-room/:roomId', name: 'staff-room', component: { template: '<div />' } },
    ],
  })
  await router.push(`/book/12?date=2026-11-13&start=${start}&end=${end}`)
  const w = mount(BookView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  await w.get('button.next').trigger('click')
  await w.get('input[name="title"]').setValue('Budget review')
  await w.get('button.next').trigger('click')
  await flushPromises()
  return w
}
const food = (w: VueWrapper) => w.get('.svc[data-kind="food"]')
const groups = (w: VueWrapper) => food(w).findAll('.grp-h').map((h) => h.text())
const names = (w: VueWrapper) => food(w).findAll('.row .name').map((n) => n.text())

describe('Booking step 3: food and IT', () => {
  it('puts Breakfast first for an early meeting and no group last as Other', async () => {
    const w = await step3()
    expect(w.get('.bf-steps button.on').text()).toContain('Food & IT')
    expect(groups(w)).toEqual(['Breakfast', 'Meals', 'Breaks & drinks', 'Other'])
  })

  it('puts Breaks & drinks first for an afternoon meeting', async () => {
    const w = await step3('14:00', '15:00')
    expect(groups(w)[0]).toBe('Breaks & drinks')
  })

  it('groups IT help by its own groups', async () => {
    const w = await step3()
    expect(w.get('.svc[data-kind="it"]').findAll('.grp-h').map((h) => h.text())).toEqual(['Screens & video', 'Sound & language'])
  })

  it('searches from the start of words', async () => {
    const w = await step3()
    await food(w).get('input[type="search"]').setValue('tea')
    expect(names(w)).toEqual(['Coffee and tea'])
  })

  it('says when nothing matches and clears the search', async () => {
    const w = await step3()
    await food(w).get('input[type="search"]').setValue('zzz')
    expect(food(w).text()).toContain('No food matches “zzz”.')
    await food(w)
      .findAll('button')
      .find((b) => b.text() === 'Clear search')!
      .trigger('click')
    expect(names(w)).toHaveLength(4)
  })

  it('counts a pick made while searching, with servings and a note field', async () => {
    const w = await step3()
    expect(food(w).get('.svc-h').text()).toContain('None')
    expect(food(w).find('textarea[name="foodNote"]').exists()).toBe(false)
    await food(w).get('input[type="search"]').setValue('coffee')
    await food(w).get('.row').trigger('click')
    expect(food(w).get('.svc-h').text()).toContain('1 picked')
    expect(food(w).text()).toContain('× 8 · served at 08:00')
    expect(food(w).find('textarea[name="foodNote"]').exists()).toBe(true)
  })
})
