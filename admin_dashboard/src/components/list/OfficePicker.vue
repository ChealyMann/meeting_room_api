<script setup lang="ts">
// The office filter: a SearchPicker over the offices. Main offices first, a thin line, then the
// branches. G08: offices that are off are offered only when chosen, marked "(off)".
import { computed, useAttrs } from 'vue'

import type { LocationOut } from '../../api/types'
import { FIELD_WORDS, FILTER_WORDS } from '../../utils/pickerWords'
import SearchPicker, { type PickerItem } from './SearchPicker.vue'

/** searchable: as SearchPicker (by default only long lists get a search box). */
const props = withDefaults(defineProps<{ id: string; offices: LocationOut[]; searchable?: boolean }>(), { searchable: undefined })
const model = defineModel<number | null>({ required: true })

// mode="field" (passed through to SearchPicker) makes it a form field: "Choose an …" wording.
const attrs = useAttrs()
const WORDS = computed(() => (attrs.mode === 'field' ? FIELD_WORDS.office : FILTER_WORDS.office))

const isBranch = (o: LocationOut) => /\bbranch$/i.test(o.name_en.trim())
const items = computed<PickerItem[]>(() => {
  const shown = props.offices.filter((o) => o.is_active || o.id === model.value)
  const item = (o: LocationOut): PickerItem => ({
    value: o.id,
    label: o.is_active ? o.name_en : `${o.name_en} (off)`,
    keywords: `${o.name_kh} ${o.province?.name_en ?? ''}`,
    section: isBranch(o) ? 'branches' : 'main',
  })
  return [...shown.filter((o) => !isBranch(o)).map(item), ...shown.filter(isBranch).map(item)]
})
</script>

<template>
  <SearchPicker
    :id="id"
    :model-value="model"
    :items="items"
    :words="WORDS"
    :searchable="searchable"
    @update:model-value="model = $event as number | null"
  />
</template>
