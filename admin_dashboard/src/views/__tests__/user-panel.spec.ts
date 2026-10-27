import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { defineComponent, h } from 'vue'

import type { UserDetail } from '../../api/types'
import { useSessionStore } from '../../stores/session'
import { answerConfirm, confirmDialog, mountConfirmHost } from '../../test-utils/confirm'
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
const role = (code: string) => {
  const r = ROLES.find((x) => x.code === code)!
  return { code: r.code, name_en: r.name_en, name_kh: r.name_kh }
}

let detail: Record<string, unknown>
const calls: Array<{ method: string; path: string; body: unknown }> = []
let rolesAnswer: () => Response

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const page = (items: unknown[]) => json({ items, page: 1, size: 100, total: items.length })

beforeEach(() => {
  setActivePinia(createPinia())
  const session = useSessionStore()
  session.accessToken = 'A1'
  session.user = { id: 1, roles: [role('ADMIN')] } as unknown as UserDetail
  calls.length = 0
  detail = {
    id: 7,
    staff_id: 'EMP-007',
    title: 'Ms.',
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
    position: { id: 4, name_en: 'IT Lead', name_kh: 'ប្រធាន' },
    province: null,
    roles: [role('ROOM_OWNER'), role('STAFF')],
    owned_room_ids: [12, 13],
    must_change_password: false,
    last_login_at: null,
    ...st,
  }
  rolesAnswer = () => json({ ...detail, roles: [role('STAFF')], owned_room_ids: [], rooms_unassigned: [12, 13] })
  URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => 'blob:1')
  URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>()
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      const body = init?.body instanceof FormData ? 'form' : init?.body ? JSON.parse(String(init.body)) : undefined
      if (method !== 'GET') calls.push({ method, path: url.pathname, body })
      if (method === 'PATCH') return json({ ...detail, ...(body as object), rooms_unassigned: [] })
      if (method === 'PUT' && url.pathname.endsWith('/roles')) return rolesAnswer()
      if (method === 'PUT' && url.pathname.endsWith('/signature')) return json({ ...detail, signature_url: '/api/v1/users/7/signature' })
      if (method === 'POST') return new Response(null, { status: 204 })
      switch (url.pathname) {
        case '/api/v1/users/7':
          return json(detail)
        case '/api/v1/users/7/avatar':
        case '/api/v1/users/7/signature':
          return new Response(new Blob(['png']))
        case '/api/v1/users':
          return json({ items: [], page: 1, size: 20, total: 0 })
        case '/api/v1/roles':
          return json({ items: ROLES, total: 6 })
        case '/api/v1/positions':
          return page([{ id: 4, name_en: 'IT Lead', name_kh: 'ប្រធាន', sort_order: 1, ...st }])
        default:
          return page([])
      }
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

async function mountAt(path: string) {
  mountConfirmHost()
  const Stub = defineComponent({ render: () => h('div') })
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: Stub },
      { path: '/users', name: 'users', component: UsersView },
    ],
  })
  await router.push(path)
  const wrapper = mount(UsersView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement
const button = (text: string) => [...panel().querySelectorAll('button')].find((b) => b.textContent?.trim() === text)
const box = (label: string) => [...panel().querySelectorAll('#tabpanel-roles label')].find((l) => l.textContent?.includes(label))!.querySelector('input') as HTMLInputElement
async function click(el: HTMLElement | undefined) {
  await flushPromises()
  el!.click()
  await flushPromises()
}

describe('UserPanel', () => {
  it('shows the photo in the head, or the initials when there is none', async () => {
    detail.avatar_url = '/api/v1/users/7/avatar'
    await mountAt('/users?id=7')

    expect(panel().querySelector('.panel-head .avatar img')?.getAttribute('src')).toBe('blob:1')

    detail.avatar_url = null
    await mountAt('/users?id=7')
    const heads = document.body.querySelectorAll('.panel-head .avatar')
    expect(heads[heads.length - 1]!.textContent?.trim()).toBe('SD')
  })

  it('opens on Details with the values, and sends only what changed', async () => {
    await mountAt('/users?id=7')

    expect(panel().querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim()).toBe('Details')
    expect((document.getElementById('name_en') as HTMLInputElement).value).toBe('Sok Dara')
    expect(button('Save changes')!.disabled).toBe(true)

    const phone = document.getElementById('phone') as HTMLInputElement
    phone.value = '012 345 678'
    phone.dispatchEvent(new Event('input'))
    await click(button('Save changes'))

    expect(calls).toEqual([{ method: 'PATCH', path: '/api/v1/users/7', body: { phone: '012 345 678' } }])
  })

  it('warns that some roles need a division, and keeps Save roles off', async () => {
    await mountAt('/users?id=7&tab=roles')

    await click(box('IT Lead'))

    expect(panel().textContent).toContain('Pitika, IT Lead and IT Staff need a division. Choose one on the Details tab first.')
    expect(button('Save roles')!.disabled).toBe(true)
  })

  it('lists the rooms that lost their owner after removing Room owner', async () => {
    await mountAt('/users?id=7&tab=roles')

    await click(box('Room owner'))
    await click(button('Save roles'))

    expect(calls).toEqual([{ method: 'PUT', path: '/api/v1/users/7/roles', body: { role_codes: ['STAFF'] } }])
    const links = [...panel().querySelectorAll('.unassigned a')].map((a) => [a.textContent?.trim(), a.getAttribute('href')])
    expect(links).toEqual([
      ['RM·0012', '/?room=12'],
      ['RM·0013', '/?room=13'],
    ])
  })

  it('keeps the signed-in Admin from turning themselves off or dropping their Admin role', async () => {
    useSessionStore().user = { id: 7, roles: [role('ADMIN')] } as unknown as UserDetail
    detail.roles = [role('ADMIN'), role('STAFF')]
    await mountAt('/users?id=7&tab=roles')

    expect(box('Admin').disabled).toBe(true)
    expect(panel().textContent).toContain('You cannot remove your own Admin role.')
    expect(panel().querySelector('.panel-foot [role="switch"]')!.getAttribute('aria-disabled')).toBe('true')
    expect(panel().textContent).toContain('You cannot make yourself inactive.')
  })

  it('sets a temporary password after asking, then empties the field', async () => {
    await mountAt('/users?id=7&tab=password')

    const input = document.getElementById('reset_password') as HTMLInputElement
    input.value = 'Secret-123'
    input.dispatchEvent(new Event('input'))
    await click(button('Set temporary password'))
    expect(confirmDialog()?.textContent).toContain('Set a temporary password for Sok Dara?')
    await answerConfirm('Set password')

    expect(calls).toEqual([{ method: 'POST', path: '/api/v1/users/7/reset-password', body: { temporary_password: 'Secret-123' } }])
    expect((document.getElementById('reset_password') as HTMLInputElement).value).toBe('')
  })

  it("uploads the user's signature on the Signature tab", async () => {
    await mountAt('/users?id=7&tab=signature')

    const input = panel().querySelector('input[type="file"]') as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [new File(['x'], 'sign.png', { type: 'image/png' })], configurable: true })
    input.dispatchEvent(new Event('change'))
    await flushPromises()

    expect(calls).toEqual([{ method: 'PUT', path: '/api/v1/users/7/signature', body: 'form' }])
  })
})
