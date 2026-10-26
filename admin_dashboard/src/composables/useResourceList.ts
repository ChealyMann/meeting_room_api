// One list page's data: filters from the address (useListQuery), the newest answer only,
// the API's error message, and a jump to the last page when the page is past the end.
import { computed, ref, watch, type Ref } from 'vue'

import { ApiError } from '../api/errors'
import type { Page } from '../api/types'
import { useListQuery, type FilterSpec } from './useListQuery'

export function useResourceList<T>(
  spec: FilterSpec,
  fetchPage: (params: Record<string, unknown>) => Promise<Page<T>>,
) {
  const list = useListQuery(spec)
  const result = ref<Page<T> | null>(null) as Ref<Page<T> | null>
  const loading = ref(true)
  const error = ref('')
  const savedId = ref<number | null>(null)
  let latest = 0

  async function load() {
    const request = ++latest
    loading.value = true
    error.value = ''
    try {
      const page = await fetchPage(list.apiParams.value)
      if (request !== latest) return
      // A page past the end (after turning off its last record, or an old link): go to the last page.
      const last = Math.ceil(page.total / list.size.value)
      if (!page.items.length && page.total > 0 && list.page.value > last) {
        list.page.value = last
        return
      }
      result.value = page
    } catch (err) {
      if (request === latest) error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
    } finally {
      if (request === latest) loading.value = false
    }
  }

  watch(() => JSON.stringify(list.apiParams.value), load, { immediate: true })

  const filtered = computed(
    () => Object.keys(list.filters.value).length > 0 || list.status.value !== 'active',
  )

  /** After a save: reload and tint the saved row. */
  async function refresh(id?: number) {
    savedId.value = id ?? null
    await load()
  }

  return { list, result, loading, error, filtered, savedId, load, refresh }
}
