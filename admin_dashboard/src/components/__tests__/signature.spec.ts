import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSessionStore } from '../../stores/session'
import SignatureField from '../SignatureField.vue'

const SIG = '/api/v1/users/1/signature'

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

type Route = (init: RequestInit) => Response

function stubApi(routes: Record<string, Route>) {
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const key = `${init?.method ?? 'GET'} ${new URL(String(input)).pathname}`
    const route = routes[key]
    if (!route) throw new Error(`unexpected call ${key}`)
    return route(init ?? {})
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

let urls = 0
const revoked: string[] = []

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  urls = 0
  revoked.length = 0
  URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => `blob:${++urls}`)
  URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>((url) => void revoked.push(url))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

async function mountField(signatureUrl: string | null = SIG) {
  const wrapper = mount(SignatureField, { props: { signatureUrl } })
  await flushPromises()
  return wrapper
}

async function choose(wrapper: Awaited<ReturnType<typeof mountField>>, file: File) {
  const input = wrapper.get('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  await flushPromises()
}

describe('SignatureField', () => {
  it('shows the signature image from the API', async () => {
    stubApi({ [`GET ${SIG}`]: () => new Response('png') })

    const wrapper = await mountField()

    expect(wrapper.get('img').attributes('src')).toBe('blob:1')
    expect(wrapper.text()).toContain('Sign with a dark pen on blank white paper.')
  })

  it('says "No signature yet" when there is none', async () => {
    const fetchMock = stubApi({})

    const wrapper = await mountField(null)

    expect(wrapper.text()).toContain('No signature yet')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('uploads the chosen file and shows the cleaned image', async () => {
    const fetchMock = stubApi({
      [`GET ${SIG}`]: () => new Response('png'),
      'PUT /api/v1/me/signature': () => json(200, { id: 1, signature_url: SIG }),
    })
    const wrapper = await mountField(null)
    const file = new File(['raw'], 'sig.jpg', { type: 'image/jpeg' })

    await choose(wrapper, file)

    const put = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')
    expect(put).toBeDefined()
    expect((put![1]!.body as FormData).get('file')).toBe(file)
    expect(wrapper.get('img').attributes('src')).toBe('blob:1')
    expect(wrapper.emitted('change')?.[0]).toEqual([SIG])
    expect(wrapper.get('input[type="file"]').attributes('accept')).toBe('image/jpeg,image/png,image/webp')
  })

  it('keeps the old image and shows the API message when the file is too big', async () => {
    stubApi({
      [`GET ${SIG}`]: () => new Response('png'),
      'PUT /api/v1/me/signature': () =>
        json(413, { error: { code: 'FILE_TOO_LARGE', message: 'File too big.' } }),
    })
    const wrapper = await mountField()

    await choose(wrapper, new File(['x'.repeat(10)], 'big.png', { type: 'image/png' }))

    expect(wrapper.get('#signature-error').text()).toBe('File too big.')
    expect(wrapper.get('img').attributes('src')).toBe('blob:1')
    expect(revoked).toEqual([])
  })

  it('asks before removing, then removes', async () => {
    const fetchMock = stubApi({
      [`GET ${SIG}`]: () => new Response('png'),
      'DELETE /api/v1/me/signature': () => new Response(null, { status: 204 }),
    })
    const wrapper = await mountField()

    await wrapper.get('button.remove').trigger('click')
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
    expect(wrapper.text()).toContain('Remove your signature?')

    await wrapper.get('button.confirm-remove').trigger('click')
    await flushPromises()

    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(true)
    expect(wrapper.text()).toContain('No signature yet')
    expect(revoked).toEqual(['blob:1'])
    expect(wrapper.emitted('change')?.[0]).toEqual([null])
  })

  it('frees the image when it goes away', async () => {
    stubApi({ [`GET ${SIG}`]: () => new Response('png') })
    const wrapper = await mountField()

    wrapper.unmount()

    expect(revoked).toEqual(['blob:1'])
  })
})
