<script setup lang="ts">
defineProps<{ id: string }>()

const model = defineModel<boolean>({ required: true })
</script>

<template>
  <button :id="id" type="button" role="switch" class="switch" :aria-checked="model" @click="model = !model" />
</template>
