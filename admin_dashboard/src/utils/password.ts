/**
 * The API's rules for a new password (R18), checked before sending.
 * Passwords are never trimmed; length counts characters like the API does.
 */
export function passwordProblem(next: string, email: string, current: string): string | null {
  const length = [...next].length
  if (length < 8 || length > 128) return 'Password must be 8 to 128 characters.'
  if (next.toLowerCase() === email.trim().toLowerCase()) return 'Password cannot be your email.'
  if (next === current) return 'Use a new password.'
  return null
}

/** A temporary password set by the Admin (R18): only the length counts, and it is never trimmed. */
export function temporaryPasswordProblem(text: string): string | null {
  const length = [...text].length
  return length < 8 || length > 128 ? 'Password must be 8 to 128 characters.' : null
}

// No look-alikes (0 O o 1 l I), so a password read out or copied by hand is not mistyped.
const LOWER = 'abcdefghijkmnpqrstuvwxyz'
const UPPER = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
const DIGITS = '23456789'
const SYMBOLS = '!@#$%^&*-_=+?'
const ALL = LOWER + UPPER + DIGITS + SYMBOLS

function randomIndex(below: number): number {
  // Rejection sampling keeps every character equally likely.
  const limit = Math.floor(0x100000000 / below) * below
  const word = new Uint32Array(1)
  do crypto.getRandomValues(word)
  while (word[0]! >= limit)
  return word[0]! % below
}

/** A random temporary password with at least one lower, upper, digit and symbol. */
export function generatePassword(size = 14): string {
  const chars = [LOWER, UPPER, DIGITS, SYMBOLS].map((set) => set[randomIndex(set.length)]!)
  while (chars.length < size) chars.push(ALL[randomIndex(ALL.length)]!)
  for (let i = chars.length - 1; i > 0; i--) {
    const j = randomIndex(i + 1)
    ;[chars[i], chars[j]] = [chars[j]!, chars[i]!]
  }
  return chars.join('')
}
