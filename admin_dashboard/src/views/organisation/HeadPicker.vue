<script setup lang="ts">
// Pick the person who signs the request slip (ប័ណ្ណស្នើ) for a department, an office, or as
// Director of Cabinet: any active user, or nobody. The one set now stays in the list even when
// they are no longer active ("(off)"), so opening the form never loses them.
import { computed, onMounted, ref } from 'vue'

import { api } from '../../api'
import { listActiveUsers } from '../../api/references'
import SearchPicker from '../../components/list/SearchPicker.vue'
import type { PickerWords } from '../../components/list/SearchPicker.vue'

const props = defineProps<{
  id: string
  /** The head saved on the record now, or null. */
  current: { id: number; name_en: string } | null
  words: PickerWords
  invalid?: boolean
  describedBy?: string
}>()
const model = defineModel<number | null>({ required: true })

const users = ref<{ id: number; name_en: string }[]>([])
onMounted(async () => {
  try {
    users.value = await listActiveUsers(api)
  } catch {
    users.value = [] // the picker still shows the head set now
  }
})

const options = computed(() => {
  const list = users.value.map((u) => ({ value: u.id, label: u.name_en }))
  const now = props.current
  if (now && !list.some((o) => o.value === now.id)) list.unshift({ value: now.id, label: `${now.name_en} (off)` })
  return list
})
</script>

<template>
  <SearchPicker
    :id="id"
    mode="field"
    nullable
    :items="options"
    :words="words"
    :model-value="model"
    :invalid="invalid"
    :described-by="describedBy"
    @update:model-value="model = $event as number | null"
  />
</template>
