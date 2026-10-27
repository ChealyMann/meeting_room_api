// A record's sort order, as the forms take it: empty (the API's default, 0) or a whole number
// from 0 to 9999 (the API's SortOrder limit, DSH-G06).
const WHOLE = /^\d+$/

/** The problem with the typed order, or null when it can be sent. */
export function orderProblem(text: string): string | null {
  const value = text.trim()
  if (!value) return null
  return WHOLE.test(value) && Number(value) <= 9999 ? null : 'Order must be a whole number from 0 to 9999.'
}

/** The order to send: empty is 0. */
export function orderValue(text: string): number {
  return text.trim() ? Number(text.trim()) : 0
}
