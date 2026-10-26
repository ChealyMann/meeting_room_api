// Unsaved form values, kept in memory only, so a forced sign-in does not lose
// what the user typed (DSH-A06). Never written to storage.
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDraftsStore = defineStore('drafts', () => {
  const drafts = ref<Record<string, unknown>>({})

  function get<T>(key: string): T | undefined {
    return drafts.value[key] as T | undefined
  }

  function set(key: string, value: unknown): void {
    // A plain copy: later edits to the form must not change the saved draft.
    drafts.value[key] = JSON.parse(JSON.stringify(value))
  }

  function clear(key: string): void {
    delete drafts.value[key]
  }

  /** Forget every draft: on sign-out, so the next person sees none of them. */
  function clearAll(): void {
    drafts.value = {}
  }

  return { get, set, clear, clearAll }
})
