import { describe, expect, it } from 'vitest'

import { COMMON, generatePassword, passwordProblem, passwordStrength, PERSONAL, REPEAT, RUN, temporaryPasswordProblem } from '../password'

const EMAIL = 'admin@company.com'

describe('passwordProblem', () => {
  it('needs 8 to 128 characters', () => {
    expect(passwordProblem('short', EMAIL, 'old password')).toBe('Password must be 8 to 128 characters.')
    expect(passwordProblem('x'.repeat(129), EMAIL, 'old password')).toBe(
      'Password must be 8 to 128 characters.',
    )
    expect(passwordProblem(generatePassword(128), EMAIL, 'old password')).toBeNull()
  })

  it('counts characters, not UTF-16 units, like the API', () => {
    // 8 emoji = 16 UTF-16 units but 8 characters.
    expect(passwordProblem('🔑🌧🐟🌿🔔🍵🛶🌙', EMAIL, 'old password')).toBeNull()
    expect(passwordProblem('🔑🌧🐟🌿🔔🍵🛶', EMAIL, 'old password')).toBe(
      'Password must be 8 to 128 characters.',
    )
  })

  it('cannot be the email, ignoring case', () => {
    expect(passwordProblem('ADMIN@company.com', EMAIL, 'old password')).toBe(
      'Password cannot be your email.',
    )
  })

  it('must differ from the current password', () => {
    expect(passwordProblem('Kite@Mekong', EMAIL, 'Kite@Mekong')).toBe('Use a new password.')
  })

  it('counts spaces', () => {
    expect(passwordProblem(' Kite@Mekong', EMAIL, 'Kite@Mekong')).toBeNull()
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
  it('checks 8 to 128 characters without trimming', () => {
    expect(temporaryPasswordProblem('1234567')).toBe('Password must be 8 to 128 characters.')
    expect(temporaryPasswordProblem(' Kite-7 ')).toBeNull()
    expect(temporaryPasswordProblem('x'.repeat(129))).toBe('Password must be 8 to 128 characters.')
  })

  it('uses the same pattern, common and name rules', () => {
    expect(temporaryPasswordProblem('12345678')).toBe(RUN)
    expect(temporaryPasswordProblem('Welcome@2026')).toBe(COMMON)
    expect(temporaryPasswordProblem('Sreymom@26', 'chan.sreymom@company.com', 'Chan Sreymom')).toBe(PERSONAL)
  })

  it('lets every generated password pass', () => {
    for (let i = 0; i < 300; i++) expect(temporaryPasswordProblem(generatePassword(), 'sok.dara@company.com', 'Sok Dara')).toBeNull()
  })
})

// The same examples as tests/test_passwords.py: the API and the dashboard must agree.
describe('patterns, common passwords and names (R18)', () => {
  const ME = 'sok.dara@company.com'
  const problem = (p: string, email = ME, name = 'Sok Dara') => passwordProblem(p, email, 'old password', name)

  it.each(['aaaaaaaa', '11111111', '12121212', 'abcabcab', 'ABababAB', 'zz9!zz9!', 'aaaa1111', '12312344', '11223344', 'aabbccdd', '4567456799'])(
    'refuses the repeat %s',
    (p) => {
      expect(problem(p)).toBe(REPEAT)
    },
  )

  it.each(['12345678', '87654321', 'abcdefgh', 'HGFEDCBA', 'qwertyui', 'asdfghjkl', 'qwerty123', '1q2w3e4r', 'a1b2c3d4', 'abc!def@', 'zxcvbnm1', 'zxc123zxc', 'x1234567'])(
    'refuses the run %s',
    (p) => {
      expect(problem(p)).toBe(RUN)
    },
  )

  it.each(['password', 'Password1', 'P@ssw0rd2026!', 'Welcome@2026', 'admin1234', 'iloveyou', '2026Letmein!', 'nbc@2026!!'])(
    'refuses the common password %s',
    (p) => {
      expect(problem(p)).toBe(COMMON)
    },
  )

  it.each([
    ['Dara@2026!', ME, 'Sok Dara'],
    ['mysokdara9', ME, 'Sok Dara'],
    ['D4r4-Kampot', ME, 'Sok Dara'],
    ['chanthy.rain', 'chanthy@company.com', 'Lim Chanthy'],
    ['vibol#River7', 'x.vibol@company.com', 'X'],
  ])('refuses %s with the name or email in it', (p, email, name) => {
    expect(problem(p, email, name)).toBe(PERSONAL)
  })

  it.each(['Mekong River 7', 'q7!x2#m9', 'aB3$kP9!', 'Tonle-Sap-Blue', 'green tea at 4', 'Kampot pepper 88', 'Sok7!rain-kite', 'Kite@Mekong-7', '93817264', 'pepper and tea 88'])('lets %s pass', (p) => {
    expect(problem(p)).toBeNull()
  })
})

describe('passwordStrength', () => {
  it('is empty, weak, good or strong', () => {
    expect(passwordStrength('', 'a@b.com', 'old')).toBeNull()
    expect(passwordStrength('12345678', 'a@b.com', 'old')).toBe('weak')
    expect(passwordStrength('Kite@Mekong', 'a@b.com', 'old')).toBe('good')
    expect(passwordStrength('Kite@Mekong-7', 'a@b.com', 'old')).toBe('strong')
    expect(passwordStrength('green tea at four', 'a@b.com', 'old')).toBe('strong')
  })
})
