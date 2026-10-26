import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { REFRESH_KEY } from '../../stores/session'
import router from '../index'

afterEach(() => {
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

describe('router', () => {
  it('a reload with a refused refresh token lands on sign-in once, without a loop', async () => {
    setActivePinia(createPinia())
    sessionStorage.setItem(REFRESH_KEY, 'R-old')
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify({ error: { code: 'UNAUTHORIZED', message: 'Please sign in.' } }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await router.push('/profile')

    expect(router.currentRoute.value.name).toBe('sign-in')
    expect(router.currentRoute.value.query).toEqual({ redirect: '/profile' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(sessionStorage.getItem(REFRESH_KEY)).toBeNull()
  })
})
