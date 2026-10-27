<script setup lang="ts">
// The department filter: a SearchPicker over the departments with each office as a heading (the
// same department name is in many offices). G08 inside each office, as departmentGroups decides.
import { computed, useAttrs } from 'vue'

import type { DepartmentOut, LocationOut } from '../../api/types'
import { departmentGroups } from '../../utils/departmentOptions'
import { FIELD_WORDS, FILTER_WORDS } from '../../utils/pickerWords'
import SearchPicker, { type PickerItem } from './SearchPicker.vue'

/** searchable: as SearchPicker (by default only long lists get a search box). */
const props = withDefaults(defineProps<{ id: string; departments: DepartmentOut[]; offices: LocationOut[]; searchable?: boolean }>(), { searchable: undefined })
const model = defineModel<number | null>({ required: true })

// mode="field" (passed through to SearchPicker) makes it a form field: "Choose an …" wording.
const attrs = useAttrs()
const WORDS = computed(() => (attrs.mode === 'field' ? FIELD_WORDS.department : FILTER_WORDS.department))

const items = computed<PickerItem[]>(() =>
  departmentGroups(props.departments, props.offices, model.value)
    // The unlabelled group holds only an unknown choice: the picker shows that itself.
    .filter((g) => g.label)
    .flatMap((g) =>
      g.options.map((o) => ({
        value: o.value,
        label: o.label,
        keywords: props.departments.find((d) => d.id === o.value)?.name_kh,
        group: g.label,
      })),
    ),
)
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
