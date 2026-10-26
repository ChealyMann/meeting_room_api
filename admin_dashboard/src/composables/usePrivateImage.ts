import { onBeforeUnmount, ref, watch } from 'vue'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { getImageBlob } from '../api/me'

/**
 * Show an image that needs the bearer token (photo, signature) as an object URL.
 * It downloads again when `path` or `version` changes (a replaced file keeps its path),
 * frees the old URL each time, and never creates one after the component is gone.
 */
export function usePrivateImage(path: () => string | null, version: () => unknown = () => null) {
  const imageUrl = ref<string | null>(null)
  const loading = ref(false)
  const error = ref('')
  let alive = true
  let latest = 0

  function setImage(url: string | null) {
    if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
    imageUrl.value = url
  }

  async function load() {
    const request = ++latest
    const source = path()
    error.value = ''
    if (!source) {
      setImage(null)
      loading.value = false
      return
    }
    loading.value = true
    try {
      const blob = await getImageBlob(api, source)
      // A newer request, or the component has gone: this answer is no longer wanted.
      if (alive && request === latest) setImage(URL.createObjectURL(blob))
    } catch (err) {
      if (alive && request === latest) {
        error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
      }
    } finally {
      if (request === latest) loading.value = false
    }
  }

  watch([path, version], load, { immediate: true })
  onBeforeUnmount(() => {
    alive = false
    setImage(null)
  })

  return { imageUrl, loading, error, reload: load }
}
