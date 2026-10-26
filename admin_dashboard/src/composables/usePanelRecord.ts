// The record whose panel is open (?id=3). It is loaded before the panel opens, so the panel
// slides in once with its form already built (a loading panel swapped mid-slide stutters).
// While another record loads, the open one stays; only the answer for the address counts.
import { computed, ref, watch, type Ref } from 'vue'

import { ApiError } from '../api/errors'

export function usePanelRecord<T extends { id: number }>(id: Ref<number | null>, fetch: (id: number) => Promise<T>) {
  const record = ref<T | null>(null) as Ref<T | null>
  const error = ref('')
  let latest = 0

  async function load() {
    const request = ++latest
    error.value = ''
    const wanted = id.value
    if (wanted === null) {
      record.value = null
      return
    }
    try {
      const found = await fetch(wanted)
      if (request === latest) record.value = found
    } catch (err) {
      if (request !== latest) return
      record.value = null
      error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
    }
  }
  watch(id, load, { immediate: true })

  /** The id being loaded for its panel, for a busy mark on its row. */
  const openingId = computed(() =>
    id.value !== null && record.value?.id !== id.value && !error.value ? id.value : null,
  )

  return { record, error, openingId, load }
}
