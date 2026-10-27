import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../../api/errors'
import { answerConfirm, confirmDialog, mountConfirmHost } from '../../../test-utils/confirm'
import ActiveToggle from '../ActiveToggle.vue'

enableAutoUnmount(afterEach)

type Kind = 'office' | 'building' | 'floor' | 'room type' | 'equipment' | 'department' | 'division' | 'position'
type Count = () => Promise<number>

const counted = (total: number) => vi.fn<Count>(async () => total)
const failing = () => vi.fn<Count>(async () => Promise.reject(new ApiError(500, 'X', 'Down.')))

beforeEach(() => setActivePinia(createPinia()))

async function mountToggle(
  active: boolean,
  { kind = 'office' as Kind, name = 'Head Office', count = counted(12), turn = vi.fn<(active: boolean) => Promise<void>>(async () => {}) } = {},
) {
  mountConfirmHost()
  const wrapper = mount(ActiveToggle, { props: { active, name, kind, count, turn }, attachTo: document.body })
  await flushPromises()
  return { wrapper, turn, count }
}

const click = async (wrapper: Awaited<ReturnType<typeof mountToggle>>['wrapper'], text: string) => {
  await wrapper.findAll('button').find((b) => b.text() === text)!.trigger('click')
  await flushPromises()
}

/** The dialog text for turning off one kind with one count answer. */
async function warningFor(kind: Kind, count: ReturnType<typeof counted>) {
  const { wrapper } = await mountToggle(true, { kind, count })
  await click(wrapper, 'Turn off')
  const text = confirmDialog()?.textContent ?? ''
  await answerConfirm('Cancel')
  wrapper.unmount()
  return text
}

describe('ActiveToggle', () => {
  it('counts first, warns, then turns off', async () => {
    const { wrapper, turn, count } = await mountToggle(true)

    await click(wrapper, 'Turn off')

    expect(count).toHaveBeenCalledTimes(1)
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
    expect(await warningFor('office', counted(1))).toContain('1 room in this office stops being bookable.')
    expect(await warningFor('office', counted(0))).toContain('No rooms are affected.')
  })

  it('still asks when the count fails', async () => {
    expect(await warningFor('office', failing())).toContain('Its rooms stop being bookable.')
  })

  it('says room types and equipment stay in their rooms', async () => {
    expect(await warningFor('room type', counted(12))).toContain(
      '12 rooms use this room type and keep it. It cannot be chosen for other rooms.',
    )
    expect(await warningFor('equipment', counted(1))).toContain(
      '1 room has this item and keeps it. It cannot be added to other rooms.',
    )
    expect(await warningFor('equipment', failing())).toContain(
      'Rooms that have it keep it, but it cannot be added to other rooms.',
    )
  })

  it('counts users for departments, divisions and positions', async () => {
    expect(await warningFor('department', counted(12))).toContain(
      '12 users work in this department and stay in it. Its divisions stay on, but no new division can be added to it.',
    )
    expect(await warningFor('department', counted(1))).toContain('1 user works in this department and stays in it.')
    expect(await warningFor('department', counted(0))).toContain('No users work in it. Its divisions stay on')
    expect(await warningFor('department', failing())).toContain(
      'Its users and divisions stay as they are, but no new division can be added to it.',
    )
    expect(await warningFor('division', counted(1))).toContain(
      '1 user works in this division and stays in it. No new user can join it.',
    )
    expect(await warningFor('position', failing())).toContain('Users with it keep it, but no new user can get it.')
    expect(await warningFor('position', counted(12))).toContain(
      '12 users have this position and keep it. No new user can get it.',
    )
  })

  it('turns on without asking, and shows a refusal', async () => {
    const turn = vi.fn<(active: boolean) => Promise<void>>(async () => {
      throw new ApiError(409, 'INACTIVE_REFERENCE', 'Turn on its office first.')
    })
    const { wrapper } = await mountToggle(false, { turn })

    await click(wrapper, 'Turn on')

    expect(confirmDialog()).toBeNull()
    expect(turn).toHaveBeenCalledWith(true)
    expect(wrapper.get('[role="alert"]').text()).toContain('Turn on its office first.')
  })
})
