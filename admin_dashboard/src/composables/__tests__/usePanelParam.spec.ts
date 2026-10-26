import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { usePanelParam } from '../usePanelParam'

async function setup(start: string) {
  let panel!: ReturnType<typeof usePanelParam>
  const Host = defineComponent({
    setup() {
      panel = usePanelParam()
      return () => h('div')
    },
  })
  const router: Router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: Host }] })
  await router.push(start)
  await router.isReady()
  mount(defineComponent({ render: () => h(Host) }), { global: { plugins: [router] } })
  return { panel, router }
}

describe('usePanelParam', () => {
  it('opens a record and keeps the other address keys', async () => {
    const { panel, router } = await setup('/?search=a')

    panel.open(12)
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ search: 'a', id: '12' })
    expect(panel.id.value).toBe(12)
    expect(panel.isNew.value).toBe(false)
  })

  it('opens the create form and closes it again', async () => {
    const { panel, router } = await setup('/?search=a')

    panel.open('new')
    await flushPromises()
    expect(panel.isNew.value).toBe(true)
    expect(panel.id.value).toBeNull()

    panel.close()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ search: 'a' })
  })

  it('ignores a value that is not an id', async () => {
    const { panel } = await setup('/?id=abc')

    expect(panel.id.value).toBeNull()
    expect(panel.isNew.value).toBe(false)
  })
})
