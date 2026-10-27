import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useDraftsStore } from '../../stores/drafts'
import { useSessionStore } from '../../stores/session'
import { mountConfirmHost } from '../../test-utils/confirm'
import { choosePicker } from '../../test-utils/picker'
import UsersView from '../UsersView.vue'

enableAutoUnmount(afterEach)

const st = { is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const ROLES = [
  ['ADMIN', 'Admin'],
  ['ROOM_OWNER', 'Room owner'],
  ['STAFF', 'Staff'],
  ['PITIKA', 'Pitika'],
  ['IT_LEAD', 'IT Lead'],
  ['IT_STAFF', 'IT Staff'],
].map(([code, name_en], i) => ({ id: i + 1, code, name_en, name_kh: `តួនាទី ${i + 1}`, is_active: true }))
const user = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  staff_id: 'EMP-007',
  title: 'Ms.',
  name_en: 'Sok Dara',
  name_kh: 'សុខ ដារា',
  email: 'dara@company.com',
  division: { id: 12, name_en: 'Software', name_kh: 'កម្មវិធី' },
  position: { id: 4, name_en: 'IT Lead', name_kh: 'ប្រធាន' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  role_codes: ['STAFF', 'PITIKA'],
  is_active: true,
  last_login_at: null,
  ...changes,
})
const detail = (id: number) => ({
  ...user(id, { name_en: 'Chan Tha', name_kh: 'ចាន់ ថា' }),
  secondary_email: null,
  phone: null,
  avatar_url: null,
  signature_url: null,
  email_notifications: true,
  department: { id: 4, name_en: 'IT Department', name_kh: 'ព័ត៌មានវិទ្យា' },
  roles: [],
  owned_room_ids: [],
  must_change_password: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
})

const listCalls: string[] = []
const posts: string[] = []
let saveAnswer: () => Response

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const page = (items: unknown[]) => json({ items, page: 1, size: 100, total: items.length })

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  listCalls.length = 0
  posts.length = 0
  saveAnswer = () => json(detail(9), 201)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      if ((init?.method ?? 'GET') === 'POST') {
        posts.push(String(init?.body))
        return saveAnswer()
      }
      switch (url.pathname) {
        case '/api/v1/users':
          listCalls.push(url.search)
          return json({ items: [user(7), user(8, { title: null, role_codes: [], last_login_at: '2026-10-20T02:30:00Z' })], page: 1, size: 20, total: 2 })
        case '/api/v1/users/9':
          return json(detail(9))
        case '/api/v1/roles':
          return json({ items: ROLES, total: 6 })
        case '/api/v1/positions':
          return page([{ id: 4, name_en: 'IT Lead', name_kh: 'ប្រធាន', sort_order: 1, ...st }])
        case '/api/v1/departments':
          return page([{ id: 4, location_id: 3, name_en: 'IT Department', name_kh: 'ព័ត៌មានវិទ្យា', sort_order: 1, ...st }])
        case '/api/v1/divisions':
          return page([{ id: 12, department_id: 4, name_en: 'Software', name_kh: 'កម្មវិធី', short_name: null, sort_order: 1, ...st }])
        case '/api/v1/locations':
          return page([{ id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យ', province: { code: 'PP', name_en: 'Phnom Penh', name_kh: '' }, ...st }])
        case '/api/v1/provinces':
          return json({ items: [{ code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }], total: 1 })
        default:
          return page([])
      }
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

async function mountAt(path: string) {
  mountConfirmHost()
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/users', name: 'users', component: UsersView }],
  })
  await router.push(path)
  const wrapper = mount(UsersView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement | null
function type(id: string, value: string) {
  const el = document.getElementById(id) as HTMLInputElement
  el.value = value
  el.dispatchEvent(new Event('input'))
}
async function clickInPanel(text: string) {
  await flushPromises()
  ;[...panel()!.querySelectorAll('button')].find((b) => b.textContent?.trim() === text)!.click()
  await flushPromises()
}
async function openNew(wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper']) {
  await wrapper.findAll('button').find((b) => b.text() === 'New user')!.trigger('click')
  await flushPromises()
}
async function fillNew() {
  type('staff_id', 'EMP-010')
  type('name_kh', 'ចាន់ ថា')
  type('name_en', 'Chan Tha')
  type('email', 'tha@company.com')
  await choosePicker('position_id', 'IT Lead')
  type('temporary_password', ' Secret-123 ')
  await flushPromises()
}

describe('UsersView', () => {
  it('asks the API with the filters from the address', async () => {
    await mountAt('/users?role=PITIKA&department_id=4')

    expect(listCalls[listCalls.length - 1]).toBe('?department_id=4&role=PITIKA&is_active=true&page=1&size=20')
  })

  it('shows serial, names with title, staff ID, role chips and last sign-in', async () => {
    const { wrapper } = await mountAt('/users')

    const [first, second] = wrapper.findAll('tbody tr')
    expect(first!.text()).toContain('US·0007')
    expect(first!.get('.name-plate .kh').text()).toBe('សុខ ដារា')
    expect(first!.get('.name-plate .en').text()).toBe('Ms. Sok Dara')
    expect(first!.text()).toContain('EMP-007')
    expect(first!.findAll('.chip').map((c) => c.text())).toEqual(['Staff', 'Pitika'])
    expect(first!.get('.last').text()).toBe('Never')
    expect(second!.text()).toContain('No roles')
    expect(wrapper.get('.count').text()).toBe('002 users')
  })

  it('filters by role with the picker', async () => {
    const { router } = await mountAt('/users')

    await choosePicker('filter-role', 'IT Lead')

    expect(router.currentRoute.value.query).toEqual({ role: 'IT_LEAD' })
  })

  it('creates a user with a generated or typed temporary password, then opens their roles', async () => {
    const { wrapper, router } = await mountAt('/users')
    await openNew(wrapper)

    await clickInPanel('Generate')
    expect((document.getElementById('temporary_password') as HTMLInputElement).value).toHaveLength(14)

    await fillNew()
    await clickInPanel('Create user')

    expect(JSON.parse(posts[0]!)).toMatchObject({
      staff_id: 'EMP-010',
      name_en: 'Chan Tha',
      email: 'tha@company.com',
      position_id: 4,
      temporary_password: ' Secret-123 ',
    })
    expect(router.currentRoute.value.query).toEqual({ id: '9', tab: 'roles' })
  })

  it('shows a duplicate email under Email', async () => {
    saveAnswer = () => json({ error: { code: 'DUPLICATE', message: 'Used.', fields: { email: 'This email already exists.' } } }, 409)
    const { wrapper } = await mountAt('/users')
    await openNew(wrapper)

    await fillNew()
    await clickInPanel('Create user')

    expect(document.getElementById('email-error')?.textContent).toContain('This email already exists.')
  })

  it('keeps the typing in the draft, but never the password', async () => {
    const { wrapper } = await mountAt('/users')
    await openNew(wrapper)
    type('name_en', 'Chan Tha')
    await clickInPanel('Generate')
    await flushPromises()

    const draft = useDraftsStore().get<{ form: Record<string, unknown> }>('user:new')
    expect(draft?.form.name_en).toBe('Chan Tha')
    expect(draft?.form.temporary_password).toBe('')
  })

  it('is a real page in the sidebar', () => {
    const item = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.label === 'Users')
    expect(item?.route).toBe('users')
  })
})
