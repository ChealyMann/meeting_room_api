import { describe, expect, it } from 'vitest'

import type { ServiceOut } from '../../api/services'
import { groupLabel, serviceChanges, serviceCreateBody, serviceFormOf, serviceProblems } from '../serviceForms'

const service = (changes: Partial<ServiceOut> = {}): ServiceOut => ({
  id: 3,
  name: 'Coffee break',
  description: 'Coffee and cake',
  group: null,
  icon: null,
  sort_order: 1,
  is_active: true,
  version: 4,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
  ...changes,
})

describe('service form', () => {
  it('needs a name', () => {
    expect(serviceProblems({ name: ' ', description: '', sort_order: '', group: null, icon: null })).toEqual({ name: 'Enter the name.' })
  })

  it('needs 2 to 200 characters in the name', () => {
    expect(serviceProblems({ name: 'A', description: '', sort_order: '', group: null, icon: null }).name).toBe('Use 2 to 200 characters.')
    expect(serviceProblems({ name: 'x'.repeat(201), description: '', sort_order: '', group: null, icon: null }).name).toBe('Use 2 to 200 characters.')
  })

  it('limits the description to 1000 characters', () => {
    expect(serviceProblems({ name: 'Tea', description: 'x'.repeat(1001), sort_order: '', group: null, icon: null }).description).toBe('Max 1000 characters.')
  })

  it('checks the order', () => {
    expect(serviceProblems({ name: 'Tea', description: '', sort_order: '10000', group: null, icon: null }).sort_order).toBe(
      'Order must be a whole number from 0 to 9999.',
    )
  })

  it('creates with trimmed values, no empty description, order 0', () => {
    expect(serviceCreateBody({ name: ' Coffee break ', description: ' ', sort_order: '', group: null, icon: null })).toEqual({ name: 'Coffee break', sort_order: 0, is_active: true })
  })

  it('sends a new group and icon, and null to clear them', () => {
    const form = { ...serviceFormOf(service()), group: 'MEALS', icon: 'utensils' }
    expect(serviceChanges(form, service())).toEqual({ group: 'MEALS', icon: 'utensils', version: 4 })
    const cleared = { ...serviceFormOf(service({ group: 'MEALS' })), group: null }
    expect(serviceChanges(cleared, service({ group: 'MEALS' }))).toEqual({ group: null, version: 4 })
  })

  it('names the groups', () => {
    expect(groupLabel('catering', 'BREAKS')).toBe('Breaks & drinks')
    expect(groupLabel('it', 'SOUND')).toBe('Sound & language')
    expect(groupLabel('it', null)).toBeNull()
  })

  it('sends nothing when nothing changed', () => {
    expect(serviceChanges(serviceFormOf(service()), service())).toEqual({})
  })

  it('sends the change with the version it read', () => {
    const form = { ...serviceFormOf(service()), name: 'Lunch box' }
    expect(serviceChanges(form, service())).toEqual({ name: 'Lunch box', version: 4 })
  })

  it('sends null when the description is cleared', () => {
    const form = { ...serviceFormOf(service()), description: '' }
    expect(serviceChanges(form, service())).toEqual({ description: null, version: 4 })
  })
})
