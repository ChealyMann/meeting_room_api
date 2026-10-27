import { describe, expect, it } from 'vitest'

import type { UserDetail } from '../../api/types'
import { emptyUserForm, userChanges, userCreateBody, userFormOf, userProblems } from '../userForms'

const USER = {
  id: 7,
  staff_id: 'EMP-007',
  title: 'Ms.',
  name_en: 'Sok Dara',
  name_kh: 'សុខ ដារា',
  email: 'dara@company.com',
  secondary_email: null,
  phone: '012 345 678',
  division: { id: 12, name_en: 'Software', name_kh: 'កម្មវិធី' },
  position: { id: 4, name_en: 'IT Lead', name_kh: 'ប្រធាន' },
  email_notifications: true,
  updated_at: '2026-10-01T00:00:00Z',
} as unknown as UserDetail

const filled = () => ({
  ...emptyUserForm(),
  staff_id: 'EMP-010',
  name_kh: 'ចាន់ ថា',
  name_en: 'Chan Tha',
  email: 'tha@company.com',
  position_id: 4,
  temporary_password: 'Secret-123',
})

describe('user form', () => {
  it('needs staff ID, names, email, position and, when creating, a password', () => {
    expect(userProblems(emptyUserForm(), true)).toEqual({
      staff_id: 'Enter the staff ID.',
      name_kh: 'Enter the Khmer name.',
      name_en: 'Enter the English name.',
      email: 'Enter the email.',
      position_id: 'Choose a position.',
      temporary_password: 'Password must be 8 to 128 characters.',
    })
    expect(userProblems(userFormOf(USER), false)).toEqual({})
  })

  it('checks the emails and lengths', () => {
    expect(userProblems({ ...filled(), email: 'not-an-email' }, true)).toEqual({ email: 'Enter a valid email.' })
    expect(userProblems({ ...filled(), secondary_email: 'THA@company.com' }, true)).toEqual({
      secondary_email: 'Use a different email from the main one.',
    })
    expect(userProblems({ ...filled(), staff_id: 'x'.repeat(21), phone: '1'.repeat(21) }, true)).toEqual({
      staff_id: 'Max 20 characters.',
      phone: 'Max 20 characters.',
    })
  })

  it('leaves out empty optional fields on create, and keeps the password as typed', () => {
    expect(userCreateBody({ ...filled(), temporary_password: ' Secret-123 ', phone: '  ' })).toEqual({
      staff_id: 'EMP-010',
      name_en: 'Chan Tha',
      name_kh: 'ចាន់ ថា',
      email: 'tha@company.com',
      position_id: 4,
      email_notifications: true,
      temporary_password: ' Secret-123 ',
    })
  })

  it('sends only what changed, null for a cleared field', () => {
    expect(userChanges(userFormOf(USER), USER)).toEqual({})
    expect(userChanges({ ...userFormOf(USER), phone: '' }, USER)).toEqual({ phone: null })
    expect(userChanges({ ...userFormOf(USER), title: null }, USER)).toEqual({ title: null })
    expect(userChanges({ ...userFormOf(USER), email: 'DARA@company.com' }, USER)).toEqual({})
    expect(userChanges({ ...userFormOf(USER), division_id: null }, USER)).toEqual({ division_id: null })
  })
})
