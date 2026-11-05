import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

import { phnomPenhDate } from '../utils/time'

/**
 * Today in Phnom Penh ("YYYY-MM-DD"), kept current: a page left open past midnight moves to
 * the new day. Checked every minute, and at once when the tab is shown again (a hidden tab's
 * timers may be slowed down by the browser).
 */
export function usePhnomPenhToday(): Ref<string> {
  const today = ref(phnomPenhDate(new Date()))
  const check = () => {
    const now = phnomPenhDate(new Date())
    if (now !== today.value) today.value = now
  }
  const onVisible = () => {
    if (document.visibilityState === 'visible') check()
  }
  let timer: ReturnType<typeof setInterval> | undefined
  onMounted(() => {
    timer = setInterval(check, 60_000)
    document.addEventListener('visibilitychange', onVisible)
  })
  onBeforeUnmount(() => {
    clearInterval(timer)
    document.removeEventListener('visibilitychange', onVisible)
  })
  return today
}
