<script setup lang="ts">
// Under a new password while it is typed: three short bars and a word (Weak / Good / Strong),
// and, when it is weak, the rule it breaks. The same rules as the API (R18, utils/password.ts).
import { computed } from 'vue'

import { passwordProblem, passwordStrength } from '../utils/password'

const props = defineProps<{ password: string; email: string; current?: string; name?: string }>()

const strength = computed(() => passwordStrength(props.password, props.email, props.current ?? '', props.name ?? ''))
const reason = computed(() =>
  strength.value === 'weak' ? passwordProblem(props.password, props.email, props.current ?? '', props.name ?? '') : null,
)
const filled = computed(() => ({ weak: 1, good: 2, strong: 3 })[strength.value ?? 'weak'])
const WORDS = { weak: 'Weak', good: 'Good', strong: 'Strong' } as const
</script>

<template>
  <div v-if="strength" class="pw-strength" :class="strength" aria-live="polite">
    <span class="bars" aria-hidden="true"><i v-for="n in 3" :key="n" :class="{ on: n <= filled }" /></span>
    <span class="word">{{ WORDS[strength] }}</span>
    <span v-if="reason" class="why">{{ reason }}</span>
  </div>
</template>

<style scoped>
.pw-strength {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  font-size: 12.5px;
}
.bars {
  display: inline-flex;
  gap: 4px;
}
.bars i {
  width: 28px;
  height: 4px;
  border-radius: 2px;
  background: var(--color-rule);
  transition: background-color 160ms ease;
}
.weak .bars i.on {
  background: var(--color-crimson);
}
.good .bars i.on {
  background: var(--color-warn);
}
.strong .bars i.on {
  background: var(--color-ok);
}
.word {
  font-weight: 500;
}
.weak .word {
  color: var(--color-crimson);
}
.good .word {
  color: var(--color-warn);
}
.strong .word {
  color: var(--color-ok);
}
.why {
  flex-basis: 100%;
  color: var(--color-intaglio);
}
@media (prefers-reduced-motion: reduce) {
  .bars i {
    transition: none;
  }
}
</style>
