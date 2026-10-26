import { onBeforeUnmount, ref } from 'vue'

/** Whether a CSS media query matches now; follows it as the window changes. */
export function useMediaQuery(query: string) {
  const matches = ref(false)
  if (typeof window.matchMedia !== 'function') return matches

  const list = window.matchMedia(query)
  matches.value = list.matches
  const update = (event: MediaQueryListEvent) => (matches.value = event.matches)
  list.addEventListener('change', update)
  onBeforeUnmount(() => list.removeEventListener('change', update))
  return matches
}
