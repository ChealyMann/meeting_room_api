<script setup lang="ts">
import { CircleAlert } from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps<{ errors: Array<{ id: string; label: string }> }>()

const heading = computed(() =>
  props.errors.length === 1
    ? '1 field needs attention:'
    : `${props.errors.length} fields need attention:`,
)

function focusField(id: string) {
  document.getElementById(id)?.focus()
}
</script>

<template>
  <div v-if="errors.length" class="summary" role="alert">
    <CircleAlert aria-hidden="true" />
    <div>
      <b>{{ heading }}</b>
      <ul>
        <li v-for="error in errors" :key="error.id">
          <a :href="`#${error.id}`" @click.prevent="focusField(error.id)">{{ error.label }}</a>
        </li>
      </ul>
    </div>
  </div>
</template>
