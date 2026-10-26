import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import SidePanel from '../SidePanel.vue'

afterEach(() => {
  document.body.innerHTML = ''
})

function mountPanel(body: () => ReturnType<typeof h>[], open = true) {
  return mount(SidePanel, {
    props: { open, title: 'ម៉ាន់ ជាលី', subtitle: 'Mekong Room', serial: 'RM·0012' },
    slots: { default: body, foot: () => h('button', { class: 'save' }, 'Save') },
    attachTo: document.body,
  })
}

const inBody = (selector: string) => document.body.querySelector(selector) as HTMLElement

describe('SidePanel', () => {
  it('shows the title, the second name and the serial', async () => {
    mountPanel(() => [h('input', { id: 'a' })])
    await nextTick()

    const dialog = inBody('[role="dialog"]')
    expect(dialog.textContent).toContain('ម៉ាន់ ជាលី')
    expect(dialog.textContent).toContain('Mekong Room')
    expect(dialog.textContent).toContain('RM·0012')
    expect(dialog.getAttribute('aria-labelledby')).toBe(inBody('[role="dialog"] h2').id)
  })

  it('moves focus to the first field when it opens', async () => {
    mountPanel(() => [h('input', { id: 'first' }), h('input', { id: 'second' })])
    await nextTick()
    await nextTick()

    expect(document.activeElement?.id).toBe('first')
  })

  it('moves focus to the first field with an error instead', async () => {
    mountPanel(() => [h('input', { id: 'first' }), h('input', { id: 'bad', 'aria-invalid': 'true' })])
    await nextTick()
    await nextTick()

    expect(document.activeElement?.id).toBe('bad')
  })

  it('closes with Escape, the scrim and the close button', async () => {
    const wrapper = mountPanel(() => [h('input')])
    await nextTick()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    inBody('.scrim').click()
    inBody('button[aria-label="Close"]').click()

    expect(wrapper.emitted('close')).toHaveLength(3)
  })

  it('gives focus back to what opened it after closing', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()
    const wrapper = mountPanel(() => [h('input', { id: 'first' })], false)

    await wrapper.setProps({ open: true })
    await nextTick()
    expect(document.activeElement?.id).toBe('first')

    await wrapper.setProps({ open: false })
    await nextTick()
    expect(document.activeElement).toBe(opener)
  })
})

describe('SidePanel used with v-if, as the app does', () => {
  it('gives focus back to what opened it when it is removed', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()
    const shown = ref(true)
    const Host = defineComponent({
      setup: () => () =>
        shown.value ? h(SidePanel, { open: true, title: 'Room' }, { default: () => [h('input', { id: 'first' })] }) : null,
    })
    mount(Host, { attachTo: document.body })
    await nextTick()
    await nextTick()
    expect(document.activeElement?.id).toBe('first')

    shown.value = false
    await nextTick()

    expect(document.activeElement).toBe(opener)
  })
})
