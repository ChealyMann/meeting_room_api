<script setup lang="ts">
import { Eye, EyeOff } from 'lucide-vue-next'
import { ref } from 'vue'

defineProps<{
  id: string
  autocomplete: 'current-password' | 'new-password'
  placeholder?: string
  describedBy?: string
  invalid?: boolean
}>()

const model = defineModel<string>({ required: true })
const visible = ref(false)
</script>

<template>
  <div class="password">
    <input
      :id="id"
      v-model="model"
      class="input"
      :type="visible ? 'text' : 'password'"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
      spellcheck="false"
      :aria-describedby="describedBy"
      :aria-invalid="invalid || undefined"
    />
    <button
      type="button"
      class="icon-btn"
      aria-label="Show password"
      :aria-pressed="visible"
      @click="visible = !visible"
    >
      <EyeOff v-if="visible" aria-hidden="true" />
      <Eye v-else aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
.password {
  position: relative;
}
.input {
  padding-right: 40px;
}
/* Centred, so it fits any input height. */
.icon-btn {
  position: absolute;
  top: 50%;
  right: 4px;
  transform: translateY(-50%);
}
</style>
