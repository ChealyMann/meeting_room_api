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
