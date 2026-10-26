import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useListQuery, type FilterSpec } from '../useListQuery'

const SPEC: FilterSpec = {
  search: 'string',
  location_id: 'int',
  building_id: 'int',
  equipment_ids: 'ints',
  has_owner: 'bool',
}

async function setup(start: string) {
  let list!: ReturnType<typeof useListQuery>
  const Host = defineComponent({
    setup() {
      list = useListQuery(SPEC)
      return () => h('div')
    },
  })
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: Host }],
  })
  await router.push(start)
  await router.isReady()
  mount(defineComponent({ render: () => h(Host) }), { global: { plugins: [router] } })
  return { list, router }
}

const query = (router: Router) => router.currentRoute.value.query

describe('useListQuery', () => {
  it('reads filters, page and status from the address', async () => {
    const { list } = await setup('/?search=board&location_id=3&page=2')

    expect(list.filters.value).toEqual({ search: 'board', location_id: 3 })
    expect(list.page.value).toBe(2)
    expect(list.size.value).toBe(20)
    expect(list.status.value).toBe('active')
    expect(list.apiParams.value).toEqual({
      search: 'board',
      location_id: 3,
      is_active: true,
      page: 2,
      size: 20,
    })
  })

  it('reads lists and true/false values', async () => {
    const { list } = await setup('/?equipment_ids=1,4&has_owner=false')

    expect(list.filters.value).toEqual({ equipment_ids: [1, 4], has_owner: false })
  })

  it('goes back to page 1 when a filter changes', async () => {
    const { list, router } = await setup('/?search=board&page=2')

    list.set({ building_id: 5 })
    await flushPromises()

    expect(query(router)).toEqual({ search: 'board', building_id: '5' })
  })

  it('keeps the filters when only the page changes', async () => {
    const { list, router } = await setup('/?search=board')

    list.set({ page: 3 })
    await flushPromises()

    expect(query(router)).toEqual({ search: 'board', page: '3' })
  })

  it('drops a filter set to an empty value', async () => {
    const { list, router } = await setup('/?search=board&location_id=3')

    list.set({ search: '', location_id: null })
    await flushPromises()

    expect(query(router)).toEqual({})
  })

  it('writes "all" to the address and asks the API for every status', async () => {
    const { list, router } = await setup('/')

    list.status.value = 'all'
    await flushPromises()

    expect(query(router)).toEqual({ status: 'all' })
    expect(list.apiParams.value).not.toHaveProperty('is_active')

    list.status.value = 'inactive'
    await flushPromises()
    expect(list.apiParams.value).toMatchObject({ is_active: false })

    list.status.value = 'active'
    await flushPromises()
    expect(query(router)).toEqual({})
  })

  it('falls back to defaults for bad values', async () => {
    const { list } = await setup('/?page=abc&size=7&location_id=x&status=maybe')

    expect(list.page.value).toBe(1)
    expect(list.size.value).toBe(20)
    expect(list.status.value).toBe('active')
    expect(list.filters.value).toEqual({})
  })

  it('accepts the page sizes 20, 50 and 100', async () => {
    const { list, router } = await setup('/?size=50')
    expect(list.size.value).toBe(50)

    list.size.value = 100
    await flushPromises()

    expect(query(router)).toEqual({ size: '100' })
  })

  it('reset clears the filters but keeps other keys such as an open panel', async () => {
    const { list, router } = await setup('/?search=board&page=2&status=all&room=12')

    list.reset()
    await flushPromises()

    expect(query(router)).toEqual({ room: '12' })
  })

  it('set keeps other keys such as an open panel', async () => {
    const { list, router } = await setup('/?room=12')

    list.set({ search: 'mekong' })
    await flushPromises()

    expect(query(router)).toEqual({ room: '12', search: 'mekong' })
  })
})
