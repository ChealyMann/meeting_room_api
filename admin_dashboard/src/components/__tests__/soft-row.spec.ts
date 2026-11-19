import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SoftRow from '../SoftRow.vue'

const base = { start: '12:00', end: '14:00', photo: null, photoAlt: 'Room', reference: 'NBC-26-63490', title: 'Demo Booking V2' }
const stubs = { RoomPhoto: true, StaffAvatar: true }

describe('SoftRow (look E, owner pick 18 Nov 2026)', () => {
  it('signs the row with who booked, their position and department, the status and when it was sent', () => {
    const wrapper = mount(SoftRow, {
      props: {
        ...base,
        booker: { name: 'Heng Rathana', photo: '/api/v1/users/7/avatar', position: 'Officer', department: 'Statistics Department' },
        sent: 'Sent yesterday, 16:20',
      },
      slots: { status: '<span class="soon">Starts in 3 h 31 min</span>' },
      global: { stubs },
    })
    const foot = wrapper.get('.foot')
    expect(foot.get('.booked-by').text()).toBe('Booked by')
    expect(foot.get('.who').text()).toBe('Heng Rathana')
    expect(foot.get('.role').text()).toBe('Officer · Statistics Department')
    expect(foot.get('.soon').text()).toBe('Starts in 3 h 31 min')
    expect(foot.get('.sent').text()).toBe('Sent yesterday, 16:20')
  })

  it('leaves out a missing position or department, and the whole line when both are missing', () => {
    const one = mount(SoftRow, {
      props: { ...base, booker: { name: 'Meas Sreyneang', photo: null, position: null, department: 'Research' } },
      global: { stubs },
    })
    expect(one.get('.role').text()).toBe('Research')
    const none = mount(SoftRow, {
      props: { ...base, booker: { name: 'Meas Sreyneang', photo: null, position: null, department: null } },
      global: { stubs },
    })
    expect(none.find('.role').exists()).toBe(false)
  })

  it('puts the booker’s phone after the department, to copy with a click (owner pick B “Plain”, 19 Nov 2026)', () => {
    const wrapper = mount(SoftRow, {
      props: { ...base, booker: { name: 'Heng Rathana', photo: null, position: 'Officer', department: 'Cabinet', phone: '012 345 678' } },
      global: { stubs },
    })
    const parts = wrapper.get('.foot').element.children
    const names = [...parts].map((el) => el.className.split(' ')[0])
    expect(names.indexOf('phone')).toBe(names.indexOf('role') + 1)
    expect(wrapper.get('.foot .phone .copy-value').text()).toBe('012 345 678')
  })

  it('shows no phone line when the booker has no phone', () => {
    const wrapper = mount(SoftRow, {
      props: { ...base, booker: { name: 'Heng Rathana', photo: null, position: null, department: null, phone: null } },
      global: { stubs },
    })
    expect(wrapper.find('.copy-value').exists()).toBe(false)
  })

  it('has no footer with nothing to put in it, and no button column without buttons', () => {
    const wrapper = mount(SoftRow, { props: base, global: { stubs } })
    expect(wrapper.find('.foot').exists()).toBe(false)
    expect(wrapper.find('.side').exists()).toBe(false)
  })

  it('gives today’s time tile the crimson wash', () => {
    const today = mount(SoftRow, { props: { ...base, soon: true }, global: { stubs } })
    const later = mount(SoftRow, { props: base, global: { stubs } })
    expect(today.get('.time').classes()).toContain('is-soon')
    expect(later.get('.time').classes()).not.toContain('is-soon')
  })
})
