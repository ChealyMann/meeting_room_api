import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../../api/errors'
import { useSessionStore } from '../../../stores/session'
import { answerConfirm, confirmDialog, mountConfirmHost } from '../../../test-utils/confirm'
import ActiveToggle from '../ActiveToggle.vue'

enableAutoUnmount(afterEach)

let roomsAnswer: () => Response
const roomCalls: string[] = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const rooms = (total: number) => () => json({ items: [], page: 1, size: 1, total })

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  roomCalls.length = 0
  roomsAnswer = rooms(12)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      roomCalls.push(url.pathname + url.search)
      return roomsAnswer()
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

async function mountToggle(active: boolean, turn = vi.fn<(active: boolean) => Promise<void>>(async () => {})) {
  mountConfirmHost()
  const wrapper = mount(ActiveToggle, {
    props: { active, name: 'Head Office', kind: 'office', rooms: { location_id: 3 }, turn },
    attachTo: document.body,
  })
  await flushPromises()
  return { wrapper, turn }
}

const click = async (wrapper: Awaited<ReturnType<typeof mountToggle>>['wrapper'], text: string) => {
  await wrapper.findAll('button').find((b) => b.text() === text)!.trigger('click')
  await flushPromises()
}

describe('ActiveToggle', () => {
  it('warns how many rooms stop being bookable, then turns off', async () => {
    const { wrapper, turn } = await mountToggle(true)

    await click(wrapper, 'Turn off')

    expect(roomCalls).toContain('/api/v1/rooms?location_id=3&is_active=true&page=1&size=1')
    expect(confirmDialog()?.textContent).toContain('Turn off Head Office?')
    expect(confirmDialog()?.textContent).toContain('12 rooms in this office stop being bookable.')
    await answerConfirm('Turn off')
    expect(turn).toHaveBeenCalledWith(false)
    expect(turn).toHaveBeenCalledTimes(1)
  })

  it('does nothing when cancelled', async () => {
    const { wrapper, turn } = await mountToggle(true)

    await click(wrapper, 'Turn off')
    await answerConfirm('Cancel')

    expect(turn).not.toHaveBeenCalled()
  })

  it('says "1 room" and "No rooms are affected."', async () => {
    roomsAnswer = rooms(1)
    let { wrapper } = await mountToggle(true)
    await click(wrapper, 'Turn off')
    expect(confirmDialog()?.textContent).toContain('1 room in this office stops being bookable.')
    await answerConfirm('Cancel')
    wrapper.unmount()

    roomsAnswer = rooms(0)
    ;({ wrapper } = await mountToggle(true))
    await click(wrapper, 'Turn off')
    expect(confirmDialog()?.textContent).toContain('No rooms are affected.')
  })

  it('still asks when the rooms cannot be counted', async () => {
    roomsAnswer = () => json({ error: { code: 'X', message: 'Down.' } }, 500)
    const { wrapper } = await mountToggle(true)

    await click(wrapper, 'Turn off')

    expect(confirmDialog()?.textContent).toContain('Its rooms stop being bookable.')
  })

  it('says room types and equipment stay in their rooms', async () => {
    mountConfirmHost()
    const roomType = mount(ActiveToggle, {
      props: { active: true, name: 'Meeting room', kind: 'room type', rooms: { category_id: 2 }, turn: vi.fn<(a: boolean) => Promise<void>>() },
      attachTo: document.body,
    })
    await click(roomType, 'Turn off')
    expect(roomCalls).toContain('/api/v1/rooms?category_id=2&is_active=true&page=1&size=1')
    expect(confirmDialog()?.textContent).toContain('12 rooms use this room type and keep it. It cannot be chosen for other rooms.')
    await answerConfirm('Cancel')
    roomType.unmount()

    roomsAnswer = rooms(1)
    const item = mount(ActiveToggle, {
      props: { active: true, name: 'Projector', kind: 'equipment', rooms: { equipment_ids: [4] }, turn: vi.fn<(a: boolean) => Promise<void>>() },
      attachTo: document.body,
    })
    await click(item, 'Turn off')
    expect(confirmDialog()?.textContent).toContain('1 room has this item and keeps it. It cannot be added to other rooms.')
    await answerConfirm('Cancel')

    roomsAnswer = () => json({ error: { code: 'X', message: 'Down.' } }, 500)
    await click(item, 'Turn off')
    expect(confirmDialog()?.textContent).toContain('Rooms that have it keep it, but it cannot be added to other rooms.')
  })

  it('turns on without asking, and shows a refusal', async () => {
    const turn = vi.fn<(active: boolean) => Promise<void>>(async () => {
      throw new ApiError(409, 'INACTIVE_REFERENCE', 'Turn on its office first.')
    })
    const { wrapper } = await mountToggle(false, turn)

    await click(wrapper, 'Turn on')

    expect(confirmDialog()).toBeNull()
    expect(turn).toHaveBeenCalledWith(true)
    expect(wrapper.get('[role="alert"]').text()).toContain('Turn on its office first.')
  })
})
