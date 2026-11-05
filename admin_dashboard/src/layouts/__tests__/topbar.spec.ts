import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useSessionStore } from '../../stores/session'
import AppTopbar from '../AppTopbar.vue'

const Page = defineComponent({ render: () => h('p') })

async function titleAt(roles: string[], name: string, metaTitle: string) {
  useSessionStore().user = { roles: roles.map((code) => ({ code })) } as never
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/x', name, component: Page, meta: { title: metaTitle } }] })
  await router.push('/x')
  const wrapper = mount(AppTopbar, { props: { menuOpen: false }, global: { plugins: [router] } })
  return wrapper.text()
}

beforeEach(() => setActivePinia(createPinia()))

describe('AppTopbar title', () => {
  it('says My rooms on the owner page of a Pitika who owns a room', async () => {
    expect(await titleAt(['PITIKA', 'ROOM_OWNER'], 'owner-review', 'To review')).toContain('My rooms')
  })

  it('keeps the page title otherwise', async () => {
    expect(await titleAt(['ROOM_OWNER'], 'owner-review', 'To review')).toContain('To review')
    expect(await titleAt(['ADMIN'], 'profile', 'My profile')).toContain('My profile')
  })
})
