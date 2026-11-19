import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useToast } from '../../composables/useToast'
import CopyValue from '../CopyValue.vue'

enableAutoUnmount(afterEach)

// Click the value to copy it (owner, 19 Nov 2026: "just click to copy", no Copy button).
const writeText = vi.fn<(text: string) => Promise<void>>()

beforeEach(() => {
  writeText.mockReset().mockResolvedValue(undefined)
  vi.stubGlobal('navigator', { clipboard: { writeText } })
  useToast().toasts.value = []
})
afterEach(() => vi.unstubAllGlobals())

describe('CopyValue', () => {
  it('shows the value and copies it on a click, with a toast that says what was copied', async () => {
    const w = mount(CopyValue, { props: { value: '012 345 678', what: 'Phone' } })
    expect(w.text()).toBe('012 345 678')
    await w.get('button').trigger('click')
    await flushPromises()
    expect(writeText).toHaveBeenCalledWith('012 345 678')
    expect(useToast().toasts.value.map((t) => [t.title, t.detail])).toEqual([['Phone copied', '012 345 678']])
    expect(w.get('button').classes()).toContain('copied')
  })

  it('does not let the click reach the row under it (the row opens the panel)', async () => {
    const outer = vi.fn<() => void>()
    const w = mount({ components: { CopyValue }, template: '<div @click="outer"><CopyValue value="a@b.kh" what="Email" /></div>', methods: { outer } })
    await w.get('button').trigger('click')
    expect(outer).not.toHaveBeenCalled()
  })

  it('still copies where the clipboard is off (the app opened by its LAN address over http)', async () => {
    vi.stubGlobal('navigator', {})
    // What a copy would take: the selected text in the hidden box at that moment.
    let copiedText = ''
    const execCommand = vi.fn<(command: string) => boolean>(() => {
      copiedText = document.querySelector('textarea')?.value ?? ''
      return true
    })
    document.execCommand = execCommand as never
    const w = mount(CopyValue, { props: { value: '012 345 678', what: 'Phone' } })
    await w.get('button').trigger('click')
    await flushPromises()
    expect(execCommand).toHaveBeenCalledWith('copy')
    expect(copiedText).toBe('012 345 678')
    expect(useToast().toasts.value.map((t) => t.title)).toEqual(['Phone copied'])
    expect(document.querySelector('textarea')).toBeNull()
  })

  it('says so when the browser refuses to copy both ways', async () => {
    writeText.mockRejectedValue(new Error('denied'))
    document.execCommand = vi.fn<(command: string) => boolean>(() => false) as never
    const w = mount(CopyValue, { props: { value: 'a@b.kh', what: 'Email' } })
    await w.get('button').trigger('click')
    await flushPromises()
    expect(useToast().toasts.value.map((t) => [t.title, t.detail])).toEqual([['Could not copy the email', 'Select it and copy it by hand.']])
    expect(w.get('button').classes()).not.toContain('copied')
  })

  it('names what a click does, for screen readers and on hover', () => {
    const w = mount(CopyValue, { props: { value: '012 345 678', what: 'Phone' } })
    expect(w.get('button').attributes('title')).toBe('Click to copy the phone')
    expect(w.get('button').attributes('aria-label')).toBe('Copy the phone: 012 345 678')
  })
})
