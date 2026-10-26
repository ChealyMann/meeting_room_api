export interface SelectOption {
  value: number
  label: string
}

/**
 * Options for a parent select (DSH-G08): active items, plus the chosen item even when it is
 * off (marked " (off)"), plus a placeholder when the chosen id is not in the list at all.
 */
export function selectOptions<T extends { id: number; is_active: boolean }>(
  items: T[],
  chosen: number | null | undefined,
  label: (item: T) => string,
  unknown: string,
): SelectOption[] {
  const options = items
    .filter((item) => item.is_active || item.id === chosen)
    .map((item) => ({ value: item.id, label: item.is_active ? label(item) : `${label(item)} (off)` }))
  if (chosen != null && !items.some((item) => item.id === chosen)) {
    options.unshift({ value: chosen, label: unknown })
  }
  return options
}
