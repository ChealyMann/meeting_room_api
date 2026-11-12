import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import type { LiveRefresh } from '../../../composables/useLiveRefresh'
import OfflineNote from '../OfflineNote.vue'
import RefreshButton, { updatedAgo } from '../RefreshButton.vue'

const T0 = Date.parse('2026-11-12T03:00:00Z')
function fakeLive(changes: Partial<Record<'refreshing' | 'failing', boolean>> = {}): LiveRefresh {
  return {
    run: vi.fn(async () => undefined),
    refreshing: ref(changes.refreshing ?? false),
    failing: ref(changes.failing ?? false),
    lastOk: ref(T0),
  }
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
  vi.setSystemTime(T0)
})
afterEach(() => vi.useRealTimers())

describe('updatedAgo', () => {
  it('says how long ago, in plain words', () => {
    expect(updatedAgo(T0, T0 + 4_000)).toBe('just now')
    expect(updatedAgo(T0, T0 + 42_000)).toBe('42 s ago')
    expect(updatedAgo(T0, T0 + 3 * 60_000)).toBe('3 min ago')
    expect(updatedAgo(T0, T0 + 2 * 3_600_000)).toBe('2 h ago')
  })
})

describe('RefreshButton', () => {
  it('refreshes on click and says when it was updated', async () => {
    const live = fakeLive()
    const w = mount(RefreshButton, { props: { live } })
    const button = w.get('button')
    expect(button.attributes('aria-label')).toBe('Refresh')
    expect(button.attributes('title')).toBe('Updated just now · Refresh')
    vi.setSystemTime(T0 + 3 * 60_000)
    vi.advanceTimersByTime(10_000)
    await w.vm.$nextTick()
    expect(button.attributes('title')).toBe('Updated 3 min ago · Refresh')
    await button.trigger('click')
    expect(live.run).toHaveBeenCalledTimes(1)
  })

  it('turns while it refreshes', () => {
    const w = mount(RefreshButton, { props: { live: fakeLive({ refreshing: true }) } })
    expect(w.get('button').classes()).toContain('turning')
    expect(w.get('button').attributes('aria-busy')).toBe('true')
  })

  it('says when the server cannot be reached', () => {
    const w = mount(RefreshButton, { props: { live: fakeLive({ failing: true }) } })
    expect(w.get('button').classes()).toContain('off')
    expect(w.get('button').attributes('title')).toBe("Can't reach the server · Try again")
  })
})

describe('OfflineNote', () => {
  it('shows nothing while refreshes work', () => {
    const w = mount(OfflineNote, { props: { live: fakeLive() } })
    expect(w.find('[role="status"]').exists()).toBe(false)
  })

  it('says what is shown and offers Try again when the server cannot be reached', async () => {
    const live = fakeLive({ failing: true })
    vi.setSystemTime(T0 + 2 * 60_000)
    const w = mount(OfflineNote, { props: { live } })
    expect(w.get('[role="status"]').text()).toContain("Can't reach the server. Showing what was loaded 2 min ago.")
    await w.get('button').trigger('click')
    expect(live.run).toHaveBeenCalledTimes(1)
  })
})
