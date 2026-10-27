import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import RolesView from '../RolesView.vue'

enableAutoUnmount(afterEach)

const ROLES = [
  ['ADMIN', 'Admin', 'អ្នកគ្រប់គ្រង'],
  ['ROOM_OWNER', 'Room owner', 'ម្ចាស់បន្ទប់'],
  ['STAFF', 'Staff', 'បុគ្គលិក'],
  ['PITIKA', 'Pitika', 'ពិធីការ'],
  ['IT_LEAD', 'IT Lead', 'ប្រធានព័ត៌មានវិទ្យា'],
  ['IT_STAFF', 'IT Staff', 'បុគ្គលិកព័ត៌មានវិទ្យា'],
].map(([code, name_en, name_kh], i) => ({ id: i + 1, code, name_en, name_kh, is_active: true }))
const COUNTS: Record<string, number> = { ADMIN: 2, ROOM_OWNER: 5, STAFF: 140, PITIKA: 3, IT_LEAD: 1, IT_STAFF: 4 }

const calls: Array<{ method: string; path: string; body: unknown }> = []
const countQueries: string[] = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  countQueries.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      if (method !== 'GET') {
        const body = JSON.parse(String(init?.body))
        calls.push({ method, path: url.pathname, body })
        const id = Number(url.pathname.split('/').pop())
        return json({ ...ROLES[id - 1], ...body })
      }
      if (url.pathname === '/api/v1/roles') return json({ items: ROLES, total: 6 })
      if (url.pathname === '/api/v1/users') {
        countQueries.push(url.search)
        const code = url.searchParams.get('role') ?? ''
        return json({ items: [], page: 1, size: 1, total: COUNTS[code] ?? 0 })
      }
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

async function mountAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/roles', name: 'roles', component: RolesView }],
  })
  await router.push(path)
  const wrapper = mount(RolesView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement
const button = (text: string) => [...panel().querySelectorAll('button')].find((b) => b.textContent?.trim() === text)
function type(id: string, value: string) {
  const input = document.getElementById(id) as HTMLInputElement
  input.value = value
  input.dispatchEvent(new Event('input'))
}

describe('RolesView', () => {
  it('lists the six roles in the API order, with codes, Khmer over English and the user counts', async () => {
    const { wrapper } = await mountAt('/roles')

    expect(wrapper.get('.count').text()).toBe('006 roles')
    const rows = wrapper.findAll('tbody tr')
    expect(rows.map((r) => r.get('.code').text())).toEqual(['ADMIN', 'ROOM_OWNER', 'STAFF', 'PITIKA', 'IT_LEAD', 'IT_STAFF'])
    expect(rows[2]!.get('.kh').text()).toBe('បុគ្គលិក')
    expect(rows[2]!.get('.en').text()).toBe('Staff')
    expect(rows.map((r) => r.get('.users').text())).toEqual(['2', '5', '140', '3', '1', '4'])
    expect(countQueries).toContain('?role=STAFF&is_active=true&page=1&size=1')
    expect(rows.map((r) => r.text().includes('Needs a division'))).toEqual([false, false, false, true, true, true])
    expect(wrapper.text()).not.toContain('New role')
  })

  it('renames a role and sends only the English name', async () => {
    await mountAt('/roles?id=3')

    expect(panel().textContent).toContain('The code and the rules of a role never change.')
    expect(button('Save changes')!.disabled).toBe(true)
    type('name_en', 'Employee')
    await flushPromises()
    button('Save changes')!.click()
    await flushPromises()

    expect(calls).toEqual([{ method: 'PATCH', path: '/api/v1/roles/3', body: { name_en: 'Employee' } }])
  })

  it('asks for the English name and sends nothing when it is empty', async () => {
    await mountAt('/roles?id=3')

    type('name_en', '   ')
    await flushPromises()
    button('Save changes')!.click()
    await flushPromises()

    expect(panel().textContent).toContain('Enter the English name.')
    expect(calls).toEqual([])
  })

  it('has a nav item for the Roles page', () => {
    const item = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Roles')
    expect(item?.route).toBe('roles')
  })
})
