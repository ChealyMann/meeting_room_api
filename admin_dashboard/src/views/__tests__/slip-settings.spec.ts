import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useToast } from '../../composables/useToast'
import { useSessionStore } from '../../stores/session'
import { choosePicker, pickerLabel } from '../../test-utils/picker'
import SlipSettingsView from '../SlipSettingsView.vue'

enableAutoUnmount(afterEach)

// The Admin's Request slip page: who signs as Director of Cabinet, and the address line.
const ADDRESS = 'ប្រអប់សំបុត្រលេខ ២៥, ផ្ទះលេខ ៨៨'
const USERS = [
  { id: 21, name_en: 'Pich Visal', name_kh: 'ពេជ្រ វិសាល', is_active: true },
  { id: 22, name_en: 'Chan Sophea', name_kh: 'ចាន់ សុភា', is_active: true },
]
let settings: { director: { id: number; name_en: string; name_kh: string } | null; address_kh: string; updated_at: string }
let writes: Array<{ method: string; body: unknown }>
let saveAnswer: (() => Response) | null

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useToast().toasts.value = []
  settings = { director: null, address_kh: ADDRESS, updated_at: '2026-11-13T00:00:00Z' }
  writes = []
  saveAnswer = null
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      if (url.pathname === '/api/v1/users') return json({ items: USERS, page: 1, size: 100, total: USERS.length })
      if (url.pathname === '/api/v1/slip-settings' && init?.method === 'PUT') {
        const body = JSON.parse(String(init.body))
        writes.push({ method: 'PUT', body })
        if (saveAnswer) return saveAnswer()
        settings = { ...settings, address_kh: body.address_kh, director: USERS.find((u) => u.id === body.director_user_id) ?? null }
        return json(settings)
      }
      if (url.pathname === '/api/v1/slip-settings') return json(settings)
      return json({}, 404)
    }),
  )
})
afterEach(() => {
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

async function open() {
  const wrapper = mount(SlipSettingsView, { attachTo: document.body })
  await flushPromises()
  return wrapper
}
const save = async (w: Awaited<ReturnType<typeof open>>) => {
  await w.get('form').trigger('submit')
  await flushPromises()
}

describe('Request slip settings', () => {
  it('shows who signs as Director of Cabinet and the address line', async () => {
    settings.director = USERS[0]!
    const w = await open()
    expect(w.get('h1').text()).toBe('Request slip')
    expect(pickerLabel('director_user_id')).toBe('Pich Visal')
    expect((w.get('#address_kh').element as HTMLTextAreaElement).value).toBe(ADDRESS)
  })

  it('saves the director and the address, and says so', async () => {
    const w = await open()
    await choosePicker('director_user_id', 'Chan Sophea')
    await w.get('#address_kh').setValue('  ផ្ទះលេខ ៨៨  ')
    await save(w)
    expect(writes).toEqual([{ method: 'PUT', body: { director_user_id: 22, address_kh: 'ផ្ទះលេខ ៨៨' } }])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Request slip settings saved')
  })

  it('can leave nobody as director', async () => {
    settings.director = USERS[0]!
    const w = await open()
    await choosePicker('director_user_id', 'No director')
    await save(w)
    expect(writes[0]!.body).toEqual({ director_user_id: null, address_kh: ADDRESS })
  })

  it('needs an address before it sends', async () => {
    const w = await open()
    await w.get('#address_kh').setValue('   ')
    await save(w)
    expect(writes).toEqual([])
    expect(w.get('#address_kh-error').text()).toBe('Enter the address line.')
  })

  it('shows what the API refuses under its field', async () => {
    saveAnswer = () =>
      json({ error: { code: 'INACTIVE_REFERENCE', message: 'This user is inactive.', fields: { director_user_id: 'This user is inactive.' } } }, 409)
    const w = await open()
    await choosePicker('director_user_id', 'Chan Sophea')
    await save(w)
    expect(w.get('#director_user_id-error').text()).toBe('This user is inactive.')
  })
})
