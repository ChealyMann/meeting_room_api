/**
 * The API's rules for a new password (R18), checked before sending and while typing. Same rules
 * as app/services/passwords.py; keep the two in step. Passwords are never trimmed; length counts
 * characters like the API does.
 */
export const REPEAT = 'Do not repeat the same characters, like aaaaaaaa or 12121212.'
export const RUN = 'Do not use keys or letters in a row, like 12345678, abcdefgh or qwerty.'
export const COMMON = 'This password is too common. Pick one that is hard to guess.'
export const PERSONAL = 'Do not use your name or email in the password.'

const SEQUENCES = ['abcdefghijklmnopqrstuvwxyz', '01234567890', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm', 'qazwsxedcrfvtgbyhnujmikolp']
// Common passwords and words people build them from, once numbers and symbols are taken off the
// ends and look-alike swaps (p@ssw0rd) are undone.
const COMMON_WORDS = new Set(
  (
    'password passw pass passwd passcode welcome admin administrator root user login letmein iloveyou love loveyou ' +
    'monkey dragon master shadow sunshine princess football baseball soccer superman batman trustno whatever ' +
    'freedom hello secret changeme default guest test temp qwerty abc abcd asdf zxcv god money computer internet ' +
    'office company summer winter spring autumn nbc nationalbank bank cambodia kampuchea khmer phnompenh angkor ' +
    'meeting booking'
  ).split(' '),
)
const LOOK_ALIKES: Record<string, string> = { '@': 'a', '4': 'a', '3': 'e', '1': 'i', '0': 'o', '!': 'i', $: 's', '5': 's' }
const EDGE = /^[^a-z]+|[^a-z]+$/g

const chars = (text: string) => [...text]
const plain = (text: string) => chars(text).map((c) => LOOK_ALIKES[c] ?? c).join('')

/** One short block said again: aaaa, 1212, abcabcab. */
function isRepeat(text: string): boolean {
  const c = chars(text)
  if (c.length < 3) return false
  for (let size = 1; size <= c.length / 2; size++) {
    if (c.every((ch, i) => ch === c[i % size])) return true
  }
  return false
}

/** 3 or more keys or letters in a row, either way: abc, 4321, qwerty. */
function isRun(text: string): boolean {
  if (chars(text).length < 3) return false
  return SEQUENCES.some((seq) => seq.includes(text) || chars(seq).reverse().join('').includes(text))
}

/** REPEAT or RUN when the password is only a pattern: whole, then by kind (letters, digits, rest). */
function patternProblem(lower: string): string | null {
  if (isRepeat(lower)) return REPEAT
  const c = chars(lower)
  const kinds = [
    c.filter((ch) => /\p{L}/u.test(ch)).join(''),
    c.filter((ch) => /\p{Nd}/u.test(ch)).join(''),
    c.filter((ch) => !/[\p{L}\p{N}]/u.test(ch)).join(''),
  ]
  const counted = kinds.filter((k) => chars(k).length >= 3)
  if (counted.length && counted.every(isRepeat)) return REPEAT
  if (counted.length && counted.every((k) => isRepeat(k) || isRun(k))) return RUN
  return piecesProblem(lower)
}

/**
 * REPEAT or RUN when the password is built from pattern pieces with at most 1 character left
 * over: "12312344" is 123 + 123 again + 44. From left to right, take the longest piece that
 * starts here: the same character 2+ times, a run of 3+, or 2+ characters already seen earlier.
 * REPEAT when something repeats in it (a doubled character, or 3 characters that come again).
 */
function piecesProblem(lower: string): string | null {
  const c = chars(lower)
  const n = c.length
  const part = (from: number, to: number) => c.slice(from, to).join('')
  let i = 0
  let leftOver = 0
  while (i < n) {
    let same = 1
    while (i + same < n && c[i + same] === c[i]) same++
    let run = 0
    for (let k = n - i; k >= 3; k--) {
      if (isRun(part(i, i + k))) {
        run = k
        break
      }
    }
    let seen = 0
    for (let k = n - i; k >= 2; k--) {
      if (part(0, i).includes(part(i, i + k))) {
        seen = k
        break
      }
    }
    const size = Math.max(same >= 2 ? same : 0, run, seen)
    if (size) i += size
    else {
      leftOver++
      i++
    }
  }
  if (leftOver > 1) return null
  return hasRepeat(c) ? REPEAT : RUN
}

/** A doubled character (44), or 3 characters that come again later (123 ... 123). */
function hasRepeat(c: string[]): boolean {
  if (c.some((ch, i) => i > 0 && ch === c[i - 1])) return true
  for (let j = 0; j + 3 <= c.length; j++) {
    if (c.slice(j + 3).join('').includes(c.slice(j, j + 3).join(''))) return true
  }
  return false
}

function isCommon(lower: string): boolean {
  const core = plain(lower.replace(EDGE, ''))
  return COMMON_WORDS.has(core) || COMMON_WORDS.has(core.replace(EDGE, ''))
}

/** Name and email words of 4 or more letters, and the email name joined (sokdara). */
function personalParts(email: string, name: string): string[] {
  const local = email.trim().toLowerCase().split('@')[0] ?? ''
  const words = [...local.split(/[^a-z]+/), ...name.toLowerCase().split(/[^a-z]+/)]
  const parts = new Set(words.filter((w) => w.length >= 4))
  const joined = local.replace(/[^a-z]+/g, '')
  if (joined.length >= 4) parts.add(joined)
  return [...parts]
}

/** The first rule a new password breaks, or null. `current` is left out for a temporary password. */
function ruleProblem(next: string, email: string, name: string, current?: string): string | null {
  const length = chars(next).length
  if (length < 8 || length > 128) return 'Password must be 8 to 128 characters.'
  if (next.toLowerCase() === email.trim().toLowerCase()) return 'Password cannot be your email.'
  if (current !== undefined && next === current) return 'Use a new password.'
  const lower = next.toLowerCase()
  const pattern = patternProblem(lower)
  if (pattern) return pattern
  if (isCommon(lower)) return COMMON
  const p = plain(lower)
  if (personalParts(email, name).some((part) => p.includes(part))) return PERSONAL
  return null
}

/** A password the user chooses for themselves. */
export function passwordProblem(next: string, email: string, current: string, name = ''): string | null {
  return ruleProblem(next, email, name, current)
}

/** A temporary password set by the Admin for a user (same rules; never trimmed). */
export function temporaryPasswordProblem(text: string, email = '', name = ''): string | null {
  return ruleProblem(text, email, name)
}

export type Strength = 'weak' | 'good' | 'strong'
/** For the bar under a new password: weak breaks a rule; strong is 12+ characters of 3+ kinds, or 16+. */
export function passwordStrength(next: string, email: string, current: string, name = ''): Strength | null {
  if (!next) return null
  if (passwordProblem(next, email, current, name)) return 'weak'
  const length = chars(next).length
  const kinds = [/[a-z]/, /[A-Z]/, /\p{Nd}/u, /[^\p{L}\p{N}]/u].filter((r) => r.test(next)).length
  return length >= 16 || (length >= 12 && kinds >= 3) ? 'strong' : 'good'
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
