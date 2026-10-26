export type QueryValue = string | number | boolean | number[] | null | undefined

/**
 * `?a=1&b=2` from a params object, in the given key order. Empty values (undefined, null,
 * '' and empty lists) are left out; lists are joined with commas (`equipment_ids=1,4`).
 */
export function toQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      if (value.length) search.append(key, value.join(','))
      continue
    }
    search.append(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}
