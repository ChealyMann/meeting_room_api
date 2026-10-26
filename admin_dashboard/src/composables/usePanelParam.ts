// Which record's panel is open, kept in the address (?id=12, ?id=new) so a reload keeps it.
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function usePanelParam(key = 'id') {
  const route = useRoute()
  const router = useRouter()

  const param = computed(() => {
    const value = route.query[key]
    return (Array.isArray(value) ? value[0] : value) ?? undefined
  })
  const id = computed(() => (/^\d+$/.test(param.value ?? '') ? Number(param.value) : null))
  const isNew = computed(() => param.value === 'new')

  function withPanel(value: string | null) {
    const query = { ...route.query }
    if (value === null) delete query[key]
    else query[key] = value
    return query
  }

  /** push: Back closes the panel again. */
  function open(target: number | 'new') {
    void router.push({ query: withPanel(String(target)) })
  }
  function close() {
    void router.push({ query: withPanel(null) })
  }

  return { param, id, isNew, open, close }
}
