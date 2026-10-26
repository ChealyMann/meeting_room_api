/** A record id as a banknote serial: `RM·0012`; `RM·new` before it has an id. */
export function serial(prefix: string, id: number | null): string {
  return `${prefix}·${id === null ? 'new' : String(id).padStart(4, '0')}`
}
