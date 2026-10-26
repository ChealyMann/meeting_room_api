<script setup lang="ts">
import { CircleAlert, Eye, EyeOff } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '../api/errors'
import BaseButton from '../components/base/BaseButton.vue'
import BaseField from '../components/base/BaseField.vue'
import { useFieldErrors } from '../composables/useFieldErrors'
import AuthFrame from '../layouts/AuthFrame.vue'
import { useSessionStore } from '../stores/session'
import { safeRedirect } from '../utils/redirect'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const { errors, formMessage, apply, clear } = useFieldErrors()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const busy = ref(false)

function waitMessage(seconds: number): string {
  const minutes = Math.max(1, Math.ceil(seconds / 60))
  return `Too many tries. Try again in ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}.`
}

async function submit() {
  clear()
  const typedEmail = email.value.trim()
  if (!typedEmail) errors.value.email = 'Enter your email.'
  if (!password.value) errors.value.password = 'Enter your password.'
  if (Object.keys(errors.value).length) return

  busy.value = true
  try {
    // The password goes as typed: spaces are part of it.
    await session.signIn(typedEmail, password.value)
    await router.replace(safeRedirect(route.query.redirect) ?? { name: 'home' })
  } catch (err) {
    apply(err)
    if (err instanceof ApiError && err.status === 429 && err.retryAfterSeconds) {
      formMessage.value = waitMessage(err.retryAfterSeconds)
    }
    // Field errors speak for themselves; the general message would only repeat them.
    if (Object.keys(errors.value).length) formMessage.value = ''
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthFrame title="Sign in">
    <form class="form" novalidate @submit.prevent="submit">
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <BaseField id="email" label="Email" :error="errors.email">
        <template #default="{ describedBy, invalid }">
          <input
            id="email"
            v-model="email"
            class="input"
            type="email"
            autocomplete="username"
            inputmode="email"
            spellcheck="false"
            :aria-describedby="describedBy"
            :aria-invalid="invalid || undefined"
          />
        </template>
      </BaseField>

      <BaseField id="password" label="Password" :error="errors.password">
        <template #default="{ describedBy, invalid }">
          <div class="with-toggle">
            <input
              id="password"
              v-model="password"
              class="input"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              :aria-describedby="describedBy"
              :aria-invalid="invalid || undefined"
            />
            <button
              type="button"
              class="icon-btn toggle"
              aria-label="Show password"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >
              <EyeOff v-if="showPassword" aria-hidden="true" />
              <Eye v-else aria-hidden="true" />
            </button>
          </div>
        </template>
      </BaseField>

      <BaseButton variant="primary" type="submit" :busy="busy" class="submit">
        {{ busy ? 'Signing in' : 'Sign in' }}
      </BaseButton>
    </form>
  </AuthFrame>
</template>

<style scoped>
.form {
  display: grid;
  gap: 16px;
}
.with-toggle {
  position: relative;
}
.with-toggle .input {
  padding-right: 40px;
}
.toggle {
  position: absolute;
  top: 2px;
  right: 2px;
}
.submit {
  width: 100%;
  margin-top: 8px;
}
</style>
