// One list page's data: filters from the address (useListQuery), the newest answer only,
// the API's error message, and a jump to the last page when the page is past the end.
import { computed, ref, watch, type Ref } from 'vue'

import { ApiError } from '../api/errors'
import type { Page } from '../api/types'
import { useListQuery, type FilterSpec, type ListQueryOptions } from './useListQuery'
import { useLiveRefresh } from './useLiveRefresh'

export function useResourceList<T>(
  spec: FilterSpec,
  fetchPage: (params: Record<string, unknown>) => Promise<Page<T>>,
  options: ListQueryOptions = {},
) {
  const list = useListQuery(spec, options)
  const result = ref<Page<T> | null>(null) as Ref<Page<T> | null>
  const loading = ref(true)
  const error = ref('')
  /** The API's field messages of the last failed load (e.g. a filter it refused). */
  const errorFields = ref<Record<string, string>>({})
  const savedId = ref<number | null>(null)
  let latest = 0

  /** `quiet`: the live refresh — no spinner, and a failure keeps what is shown with no message. */
  async function load(quietRefresh?: unknown) {
    // Only a real `true` is quiet: `@click="load"` passes the click event.
    const quiet = quietRefresh === true
    const request = ++latest
    if (!quiet) {
      loading.value = true
      error.value = ''
      errorFields.value = {}
    }
    try {
      const page = await fetchPage(list.apiParams.value)
      if (request !== latest) return
      // A page past the end (after turning off its last record, or an old link): go to the last page.
      const last = Math.ceil(page.total / list.size.value)
      if (options.paged !== false && !page.items.length && page.total > 0 && list.page.value > last) {
        list.page.value = last
        return
      }
      result.value = page
    } catch (err) {
      if (request !== latest || quiet) return
      // The old page no longer matches the filters the API refused: drop it, so the count and
      // the paging foot do not show numbers from before.
      result.value = null
      error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
      errorFields.value = err instanceof ApiError ? err.fields : {}
    } finally {
      if (request === latest) loading.value = false
    }
  }

  watch(() => JSON.stringify(list.apiParams.value), () => load(), { immediate: true })
  // New, changed and deleted records show with no click; a load already on its way goes first.
  useLiveRefresh(() => (loading.value ? undefined : load(true)))

  const filtered = computed(
    () =>
      Object.keys(list.filters.value).length > 0 ||
      (options.activeFilter !== false && list.status.value !== 'active'),
  )

  /** After a save: reload and tint the saved row. */
  async function refresh(id?: number) {
    savedId.value = id ?? null
    await load()
  }

  return { list, result, loading, error, errorFields, filtered, savedId, load, refresh }
}
