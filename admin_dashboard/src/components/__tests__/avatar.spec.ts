import { flushPromises, mount } from '@vue/test-utils'
import { answerConfirm, confirmDialog, mountConfirmHost } from '../../test-utils/confirm'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSessionStore } from '../../stores/session'
import AvatarField from '../AvatarField.vue'

const AV = '/api/v1/users/1/avatar'

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

type Route = (init: RequestInit) => Response | Promise<Response>

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

async function mountField(avatarUrl: string | null = AV, version = 't1') {
  mountConfirmHost()
  const wrapper = mount(AvatarField, { props: { avatarUrl, version } })
  await flushPromises()
  return wrapper
}

async function choose(wrapper: Awaited<ReturnType<typeof mountField>>, file: File) {
  const input = wrapper.get('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  await flushPromises()
}

describe('AvatarField', () => {
  it('shows the photo from the API', async () => {
    stubApi({ [`GET ${AV}`]: () => new Response('jpg') })

    const wrapper = await mountField()

    expect(wrapper.get('img').attributes('src')).toBe('blob:1')
    expect(wrapper.get('input[type="file"]').attributes('accept')).toBe(
      'image/jpeg,image/png,image/webp',
    )
  })

  it('says "No photo yet" when there is none', async () => {
    const fetchMock = stubApi({})

    const wrapper = await mountField(null)

    expect(wrapper.text()).toContain('No photo yet')
    expect(wrapper.text()).toContain('Upload photo')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('uploads the chosen file and hands back the updated user', async () => {
    const user = { id: 1, avatar_url: AV, updated_at: 't2' }
    const fetchMock = stubApi({
      'PUT /api/v1/me/avatar': () => json(200, user),
      [`GET ${AV}`]: () => new Response('jpg'),
    })
    const wrapper = await mountField(null)
    const file = new File(['raw'], 'me.jpg', { type: 'image/jpeg' })

    await choose(wrapper, file)

    const put = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')
    expect(put).toBeDefined()
    expect((put![1]!.body as FormData).get('file')).toBe(file)
    expect(wrapper.emitted('uploaded')?.[0]).toEqual([user])

    await wrapper.setProps({ avatarUrl: AV, version: 't2' })
    await flushPromises()
    expect(wrapper.get('img').attributes('src')).toBe('blob:1')
  })

  it('downloads again when the photo is replaced at the same address', async () => {
    stubApi({ [`GET ${AV}`]: () => new Response('jpg') })
    const wrapper = await mountField()

    await wrapper.setProps({ version: 't2' })
    await flushPromises()

    expect(wrapper.get('img').attributes('src')).toBe('blob:2')
    expect(revoked).toEqual(['blob:1'])
  })

  it('keeps the old photo and shows the API message when the file is refused', async () => {
    stubApi({
      [`GET ${AV}`]: () => new Response('jpg'),
      'PUT /api/v1/me/avatar': () =>
        json(415, { error: { code: 'UNSUPPORTED_FILE_TYPE', message: 'Wrong file type.' } }),
    })
    const wrapper = await mountField()

    await choose(wrapper, new File(['gif'], 'me.gif', { type: 'image/gif' }))

    expect(wrapper.get('#avatar-error').text()).toBe('Wrong file type.')
    expect(wrapper.get('img').attributes('src')).toBe('blob:1')
    expect(wrapper.emitted('uploaded')).toBeUndefined()
  })

  it('asks before removing, then removes', async () => {
    const fetchMock = stubApi({
      [`GET ${AV}`]: () => new Response('jpg'),
      'DELETE /api/v1/me/avatar': () => new Response(null, { status: 204 }),
    })
    const wrapper = await mountField()

    await wrapper.get('button.remove').trigger('click')
    await flushPromises()
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
    expect(confirmDialog()?.textContent).toContain('Remove your photo?')

    await answerConfirm('Remove photo')

    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(true)
    expect(wrapper.emitted('removed')).toHaveLength(1)
    await wrapper.setProps({ avatarUrl: null })
    await flushPromises()
    expect(wrapper.text()).toContain('No photo yet')
    expect(revoked).toEqual(['blob:1'])
  })

  it('frees the image when it goes away, even if the download ends later', async () => {
    let answer: (r: Response) => void = () => {}
    stubApi({ [`GET ${AV}`]: () => new Promise<Response>((resolve) => (answer = resolve)) })
    const wrapper = await mountField()

    wrapper.unmount()
    answer(new Response('jpg'))
    await flushPromises()

    expect(URL.createObjectURL).not.toHaveBeenCalled()
  })
})
