import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { RAIL_KEY, THEME_KEY, useUiStore } from '../ui'

beforeEach(() => {
  localStorage.clear()
  delete document.documentElement.dataset.theme
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useUiStore', () => {
  it('always starts in day mode, even when the computer prefers dark', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    const ui = useUiStore()
    await nextTick()

    expect(ui.theme).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
    vi.unstubAllGlobals()
  })

  it('switches to night mode and remembers it', async () => {
    const ui = useUiStore()

    ui.toggleTheme()
    await nextTick()

    expect(ui.theme).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem(THEME_KEY)).toBe('dark')
  })

  it('comes back in the remembered theme', async () => {
    localStorage.setItem(THEME_KEY, 'dark')

    const ui = useUiStore()
    await nextTick()

    expect(ui.theme).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('ignores a stored value it does not know', () => {
    localStorage.setItem(THEME_KEY, 'purple')

    expect(useUiStore().theme).toBe('light')
  })

  it('folds and unfolds the sidebar and remembers it', () => {
    const ui = useUiStore()
    expect(ui.railCollapsed).toBe(false)

    ui.toggleRail()
    expect(ui.railCollapsed).toBe(true)
    expect(localStorage.getItem(RAIL_KEY)).toBe('collapsed')

    setActivePinia(createPinia())
    expect(useUiStore().railCollapsed).toBe(true)

    useUiStore().toggleRail()
    expect(localStorage.getItem(RAIL_KEY)).toBe('open')
  })

  it('still works when the browser blocks storage', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })

    const ui = useUiStore()
    ui.toggleTheme()
    ui.toggleRail()

    expect(ui.theme).toBe('dark')
    expect(ui.railCollapsed).toBe(true)
  })
})
