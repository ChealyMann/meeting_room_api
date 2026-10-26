<script setup lang="ts">
import { CircleAlert } from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps<{
  id: string
  label: string
  hint?: string
  error?: string
}>()

const errorId = computed(() => `${props.id}-error`)
</script>

<template>
  <div class="field" :class="{ 'has-error': error }">
    <label :for="id">
      {{ label }}
      <span v-if="hint" class="hint">{{ hint }}</span>
    </label>
    <!-- Bind describedBy to the control's aria-describedby so the error is read with it. -->
    <slot :id="id" :described-by="error ? errorId : undefined" :invalid="!!error" />
    <p v-if="error" :id="errorId" class="error">
      <CircleAlert aria-hidden="true" />
      <span>{{ error }}</span>
    </p>
  </div>
</template>
