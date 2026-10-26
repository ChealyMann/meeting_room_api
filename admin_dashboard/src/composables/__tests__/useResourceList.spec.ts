import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { ApiError } from '../../api/errors'
import type { Page } from '../../api/types'
import { useResourceList } from '../useResourceList'

type Item = { id: number }
type Fetcher = (params: Record<string, unknown>) => Promise<Page<Item>>
const pageOf = (items: Item[], total = items.length, page = 1): Page<Item> => ({ items, page, size: 20, total })

async function setup(start: string, fetchPage: (params: Record<string, unknown>) => Promise<Page<Item>>) {
  let api!: ReturnType<typeof useResourceList<Item>>
  const Host = defineComponent({
    setup() {
      api = useResourceList<Item>({ search: 'string' }, fetchPage)
      return () => h('div')
    },
  })
  const router: Router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: Host }] })
  await router.push(start)
  await router.isReady()
  mount(defineComponent({ render: () => h(Host) }), { global: { plugins: [router] } })
  await flushPromises()
  return { api, router }
}

describe('useResourceList', () => {
  it('loads with the default status and paging', async () => {
    const fetchPage = vi.fn<Fetcher>(async () => pageOf([{ id: 1 }]))
    const { api } = await setup('/', fetchPage)

    expect(fetchPage).toHaveBeenCalledWith({ is_active: true, page: 1, size: 20 })
    expect(api.result.value?.items).toEqual([{ id: 1 }])
    expect(api.loading.value).toBe(false)
    expect(api.filtered.value).toBe(false)
  })

  it('keeps only the newest answer', async () => {
    const answers: Array<(p: Page<Item>) => void> = []
    const fetchPage = vi.fn<Fetcher>(() => new Promise<Page<Item>>((resolve) => answers.push(resolve)))
    const { api, router } = await setup('/', fetchPage)

    await router.push('/?search=new')
    await flushPromises()
    answers[1]!(pageOf([{ id: 2 }]))
    await flushPromises()
    answers[0]!(pageOf([{ id: 1 }]))
    await flushPromises()

    expect(api.result.value?.items).toEqual([{ id: 2 }])
    expect(api.filtered.value).toBe(true)
  })

  it('shows the API message, and clears it on the next load', async () => {
    let fail = true
    const fetchPage = vi.fn<Fetcher>(async () => {
      if (fail) throw new ApiError(500, 'X', 'Database is down.')
      return pageOf([])
    })
    const { api } = await setup('/', fetchPage)
    expect(api.error.value).toBe('Database is down.')

    fail = false
    await api.load()
    expect(api.error.value).toBe('')
  })

  it('moves to the last page when the page is past the end', async () => {
    const fetchPage = vi.fn<Fetcher>(async (params: Record<string, unknown>) =>
      params.page === 3 ? pageOf([], 40, 3) : pageOf([{ id: 1 }], 40, 2),
    )
    const { router } = await setup('/?page=3', fetchPage)

    expect(router.currentRoute.value.query).toEqual({ page: '2' })
  })

  it('refresh reloads and marks the saved row', async () => {
    const fetchPage = vi.fn<Fetcher>(async () => pageOf([{ id: 7 }]))
    const { api } = await setup('/', fetchPage)

    await api.refresh(7)

    expect(fetchPage).toHaveBeenCalledTimes(2)
    expect(api.savedId.value).toBe(7)
  })
})
