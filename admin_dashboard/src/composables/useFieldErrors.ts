import { ref } from 'vue'

import { ApiError } from '../api/errors'

/** Field errors and the form message from the last failed API call. */
export function useFieldErrors() {
  const errors = ref<Record<string, string>>({})
  const formMessage = ref('')

  function apply(err: unknown): void {
    if (err instanceof ApiError) {
      errors.value = { ...err.fields }
      formMessage.value = err.message
    } else {
      errors.value = {}
      formMessage.value = 'Something went wrong.'
    }
  }

  function clear(): void {
    errors.value = {}
    formMessage.value = ''
  }

  return { errors, formMessage, apply, clear }
}
