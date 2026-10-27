import { describe, expect, it } from 'vitest'

import { generatePassword, passwordProblem, temporaryPasswordProblem } from '../password'

const EMAIL = 'admin@company.com'

describe('passwordProblem', () => {
  it('needs 8 to 128 characters', () => {
    expect(passwordProblem('short', EMAIL, 'old password')).toBe('Password must be 8 to 128 characters.')
    expect(passwordProblem('x'.repeat(129), EMAIL, 'old password')).toBe(
      'Password must be 8 to 128 characters.',
    )
    expect(passwordProblem('x'.repeat(128), EMAIL, 'old password')).toBeNull()
  })

  it('counts characters, not UTF-16 units, like the API', () => {
    // 8 emoji = 16 UTF-16 units but 8 characters.
    expect(passwordProblem('🔑'.repeat(8), EMAIL, 'old password')).toBeNull()
    expect(passwordProblem('🔑'.repeat(7), EMAIL, 'old password')).toBe(
      'Password must be 8 to 128 characters.',
    )
  })

  it('cannot be the email, ignoring case', () => {
    expect(passwordProblem('ADMIN@company.com', EMAIL, 'old password')).toBe(
      'Password cannot be your email.',
    )
  })

  it('must differ from the current password', () => {
    expect(passwordProblem('abc12345', EMAIL, 'abc12345')).toBe('Use a new password.')
  })

  it('counts spaces', () => {
    expect(passwordProblem(' abc12345', EMAIL, 'abc12345')).toBeNull()
  })
})

describe('generatePassword', () => {
  it('makes 14 characters with every kind and no look-alikes', () => {
    for (let i = 0; i < 200; i++) {
      const password = generatePassword()
      expect(password).toHaveLength(14)
      expect(password).toMatch(/[a-z]/)
      expect(password).toMatch(/[A-Z]/)
      expect(password).toMatch(/[0-9]/)
      expect(password).toMatch(/[!@#$%^&*\-_=+?]/)
      expect(password).not.toMatch(/[0Oo1lI]/)
    }
  })
})

describe('temporaryPasswordProblem', () => {
  it('checks 8 to 128 characters only, without trimming', () => {
    expect(temporaryPasswordProblem('1234567')).toBe('Password must be 8 to 128 characters.')
    expect(temporaryPasswordProblem(' 123456 ')).toBeNull()
    expect(temporaryPasswordProblem('x'.repeat(129))).toBe('Password must be 8 to 128 characters.')
  })
})
