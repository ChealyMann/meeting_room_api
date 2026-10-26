<script setup lang="ts">
import { CircleAlert } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '../api/errors'
import BaseButton from '../components/base/BaseButton.vue'
import BaseField from '../components/base/BaseField.vue'
import PasswordInput from '../components/base/PasswordInput.vue'
import { useFieldErrors } from '../composables/useFieldErrors'
import { useToast } from '../composables/useToast'
import AuthFrame from '../layouts/AuthFrame.vue'
import { useSessionStore } from '../stores/session'
import { passwordProblem } from '../utils/password'

const session = useSessionStore()
const router = useRouter()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

const current = ref('')
const next = ref('')
const confirm = ref('')
const busy = ref(false)

const forced = computed(() => session.mustChangePassword)

async function submit() {
  clear()
  if (!current.value) errors.value.current_password = 'Enter your current password.'
  const problem = passwordProblem(next.value, session.user?.email ?? '', current.value)
  if (problem) errors.value.new_password = problem
  else if (confirm.value !== next.value) errors.value.confirm_password = 'The passwords do not match.'
  if (Object.keys(errors.value).length) return

  busy.value = true
  try {
    await session.changePassword(current.value, next.value)
    toast.show('Password changed')
    await router.replace({ name: 'home' })
  } catch (err) {
    apply(err)
    if (err instanceof ApiError && err.code === 'WRONG_PASSWORD') {
      errors.value = { current_password: err.message }
    }
    if (Object.keys(errors.value).length) formMessage.value = ''
  } finally {
    busy.value = false
  }
}

async function signOut() {
  await session.signOut()
  await router.replace({ name: 'sign-in' })
}
</script>

<template>
  <AuthFrame title="Choose a new password">
    <p v-if="forced" class="lead">Your password was set by an administrator. Choose your own to continue.</p>

    <form class="form" novalidate @submit.prevent="submit">
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <BaseField id="current_password" label="Current password" :error="errors.current_password">
        <template #default="{ describedBy, invalid }">
          <PasswordInput
            id="current_password"
            v-model="current"
            autocomplete="current-password"
            :described-by="describedBy"
            :invalid="invalid"
          />
        </template>
      </BaseField>

      <BaseField id="new_password" label="New password" hint="8 to 128 characters" :error="errors.new_password">
        <template #default="{ describedBy, invalid }">
          <PasswordInput
            id="new_password"
            v-model="next"
            autocomplete="new-password"
            :described-by="describedBy"
            :invalid="invalid"
          />
        </template>
      </BaseField>

      <BaseField id="confirm_password" label="Confirm new password" :error="errors.confirm_password">
        <template #default="{ describedBy, invalid }">
          <PasswordInput
            id="confirm_password"
            v-model="confirm"
            autocomplete="new-password"
            :described-by="describedBy"
            :invalid="invalid"
          />
        </template>
      </BaseField>

      <div class="actions">
        <BaseButton v-if="forced" variant="quiet" class="sign-out" @click="signOut">Sign out</BaseButton>
        <RouterLink v-else :to="{ name: 'profile' }" class="btn quiet">Cancel</RouterLink>
        <BaseButton variant="primary" type="submit" :busy="busy">
          {{ busy ? 'Saving' : 'Save password' }}
        </BaseButton>
      </div>
    </form>
  </AuthFrame>
</template>

<style scoped>
.lead {
  margin: -12px 0 24px;
  font-size: 13px;
  color: var(--color-intaglio);
}
.form {
  display: grid;
  gap: 16px;
}
.actions {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}
.actions .btn {
  text-decoration: none;
}
</style>
