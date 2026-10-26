// A list's filters, page, page size and status, kept in the page address (DSH-G01, G02),
// so a filtered list survives a reload and can be shared. Defaults stay out of the address.
import { computed, type ComputedRef, type Ref } from 'vue'
import { useRoute, useRouter, type LocationQuery, type LocationQueryRaw } from 'vue-router'

export type FilterKind = 'string' | 'int' | 'bool' | 'ints'
export type FilterSpec = Record<string, FilterKind>
export type Status = 'active' | 'inactive' | 'all'

export const PAGE_SIZES = [20, 50, 100] as const
const DEFAULT_SIZE = 20

function first(value: LocationQuery[string] | undefined): string | null {
  return (Array.isArray(value) ? value[0] : value) ?? null
}

function positiveInt(text: string): number | null {
  return /^\d+$/.test(text) && Number(text) > 0 ? Number(text) : null
}

function parse(kind: FilterKind, text: string): unknown {
  switch (kind) {
    case 'string':
      return text || null
    case 'int':
      return positiveInt(text)
    case 'bool':
      return text === 'true' ? true : text === 'false' ? false : null
    case 'ints': {
      const ids = text.split(',').map(positiveInt)
      return ids.length && ids.every((id) => id !== null) ? ids : null
    }
  }
}

function isEmpty(value: unknown): boolean {
  return value === undefined || value === null || value === '' || (Array.isArray(value) && !value.length)
}

function serialize(value: unknown): string {
  return Array.isArray(value) ? value.join(',') : String(value)
}

export function useListQuery(spec: FilterSpec) {
  const route = useRoute()
  const router = useRouter()
  const managed = new Set([...Object.keys(spec), 'page', 'size', 'status'])

  const filters: ComputedRef<Record<string, unknown>> = computed(() => {
    const out: Record<string, unknown> = {}
    for (const [key, kind] of Object.entries(spec)) {
      const text = first(route.query[key])
      if (text === null) continue
      const value = parse(kind, text)
      if (!isEmpty(value)) out[key] = value
    }
    return out
  })

  const currentPage = computed(() => positiveInt(first(route.query.page) ?? '') ?? 1)
  const currentSize = computed(() => {
    const size = positiveInt(first(route.query.size) ?? '')
    return size !== null && (PAGE_SIZES as readonly number[]).includes(size) ? size : DEFAULT_SIZE
  })
  const currentStatus = computed<Status>(() => {
    const status = first(route.query.status)
    return status === 'inactive' || status === 'all' ? status : 'active'
  })

  /** Write the address: keys this list does not own (an open panel) are kept. */
  function write(next: { filters: Record<string, unknown>; page: number; size: number; status: Status }) {
    const query: LocationQueryRaw = {}
    for (const [key, value] of Object.entries(route.query)) {
      if (!managed.has(key)) query[key] = value
    }
    for (const [key, value] of Object.entries(next.filters)) {
      if (!isEmpty(value)) query[key] = serialize(value)
    }
    if (next.page > 1) query.page = String(next.page)
    if (next.size !== DEFAULT_SIZE) query.size = String(next.size)
    if (next.status !== 'active') query.status = next.status
    // replace: typing in a filter must not add a history entry per change.
    void router.replace({ query })
  }

  const state = () => ({
    filters: { ...filters.value },
    page: currentPage.value,
    size: currentSize.value,
    status: currentStatus.value,
  })

  /** Change filters (and/or `page`). Any change other than the page goes back to page 1. */
  function set(changes: Record<string, unknown>) {
    const next = state()
    for (const [key, value] of Object.entries(changes)) {
      if (key === 'page') continue
      next.filters[key] = value
    }
    next.page = 'page' in changes ? Number(changes.page) || 1 : 1
    write(next)
  }

  function reset() {
    write({ filters: {}, page: 1, size: DEFAULT_SIZE, status: 'active' })
  }

  const page: Ref<number> = computed({
    get: () => currentPage.value,
    set: (value) => write({ ...state(), page: value }),
  })
  const size: Ref<number> = computed({
    get: () => currentSize.value,
    set: (value) => write({ ...state(), size: value, page: 1 }),
  })
  const status: Ref<Status> = computed({
    get: () => currentStatus.value,
    set: (value) => write({ ...state(), status: value, page: 1 }),
  })

  const apiParams: ComputedRef<Record<string, unknown>> = computed(() => {
    const params: Record<string, unknown> = { ...filters.value }
    if (currentStatus.value !== 'all') params.is_active = currentStatus.value === 'active'
    params.page = currentPage.value
    params.size = currentSize.value
    return params
  })

  return { filters, page, size, status, set, reset, apiParams }
}
