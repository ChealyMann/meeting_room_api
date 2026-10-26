<script setup lang="ts">
// A list's search box. It waits until typing stops (300ms), so the list is not reloaded per key,
// and follows the address when the search changes there (Back, "Clear filters").
import { Search } from 'lucide-vue-next'
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{ value: string; label: string; placeholder: string }>()
const emit = defineEmits<{ search: [text: string] }>()

const text = ref(props.value)
let timer: ReturnType<typeof setTimeout> | undefined
watch(text, (typed) => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    if (typed.trim() !== props.value) emit('search', typed.trim())
  }, 300)
})
watch(
  () => props.value,
  (value) => {
    if (value !== text.value.trim()) text.value = value
  },
)
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <label class="search">
    <span class="sr-only">{{ label }}</span>
    <Search aria-hidden="true" />
    <input v-model="text" class="input" type="search" :placeholder="placeholder" />
  </label>
</template>

<style scoped>
.search {
  position: relative;
  flex: 1 1 240px;
  max-width: 320px;
}
.search svg.lucide {
  position: absolute;
  top: 50%;
  left: 10px;
  transform: translateY(-50%);
  color: var(--color-intaglio);
  pointer-events: none;
}
.search .input {
  padding-left: 34px;
}
</style>
