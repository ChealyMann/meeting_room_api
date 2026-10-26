<script setup lang="ts">
import { ArrowRight, CircleAlert } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '../api/errors'
import BaseButton from '../components/base/BaseButton.vue'
import BaseField from '../components/base/BaseField.vue'
import PasswordInput from '../components/base/PasswordInput.vue'
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
// There is no self-service reset: an Admin sets a new temporary password.
const forgotOpen = ref(false)
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
  <AuthFrame title="Sign in" subtitle="Continue to the meeting rooms dashboard">
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
            placeholder="name@nbc.gov.kh"
            spellcheck="false"
            :aria-describedby="describedBy"
            :aria-invalid="invalid || undefined"
          />
        </template>
      </BaseField>

      <div class="password-field">
        <BaseField id="password" label="Password" :error="errors.password">
          <template #default="{ describedBy, invalid }">
            <PasswordInput
              id="password"
              v-model="password"
              autocomplete="current-password"
              placeholder="Enter your password"
              :described-by="describedBy"
              :invalid="invalid"
            />
          </template>
        </BaseField>
        <button
          type="button"
          class="forgot"
          aria-controls="forgot-note"
          :aria-expanded="forgotOpen"
          @click="forgotOpen = !forgotOpen"
        >
          Forgot password?
        </button>
        <p v-if="forgotOpen" id="forgot-note" class="forgot-note">
          Ask an administrator to reset your password. You will get a temporary one and choose
          your own when you sign in.
        </p>
      </div>

      <BaseButton variant="primary" type="submit" :busy="busy" class="submit">
        {{ busy ? 'Signing in' : 'Sign in' }}
        <ArrowRight v-if="!busy" aria-hidden="true" />
      </BaseButton>
    </form>
  </AuthFrame>
</template>

<style scoped>
.form {
  display: grid;
  gap: 16px;
}
.password-field {
  position: relative;
}
/* Sits on the label row, at the right. */
.forgot {
  position: absolute;
  top: 0;
  right: 0;
  padding: 0;
  border: 0;
  background: none;
  font-size: 12.5px;
  color: var(--color-intaglio);
  cursor: pointer;
}
.forgot:hover {
  color: var(--color-crimson);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.forgot-note {
  margin: 8px 0 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-crimson-wash);
  font-size: 12.5px;
  color: var(--color-ink);
}
.submit {
  width: 100%;
  margin-top: 12px;
}
</style>
