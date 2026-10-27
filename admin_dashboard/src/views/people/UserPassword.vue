<script setup lang="ts">
// Set a temporary password for a user (DSH-U05). It signs them out everywhere and they must choose
// a new one at their next sign-in. The password is never kept: not in drafts, the address or toasts.
import { CircleAlert, Copy, KeyRound } from 'lucide-vue-next'
import { ref } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import type { UserDetail } from '../../api/types'
import { resetPassword } from '../../api/users'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import PasswordInput from '../../components/base/PasswordInput.vue'
import { useConfirm } from '../../composables/useConfirm'
import { useToast } from '../../composables/useToast'
import { generatePassword, temporaryPasswordProblem } from '../../utils/password'

const props = defineProps<{ user: UserDetail }>()

const toast = useToast()
const { confirm } = useConfirm()

const password = ref('')
const problem = ref('')
const error = ref('')
const saving = ref(false)

function generate() {
  password.value = generatePassword()
  problem.value = ''
}
async function copy() {
  try {
    await navigator.clipboard.writeText(password.value)
    toast.show('Password copied')
  } catch {
    toast.show('Copy did not work', 'Select the password and copy it by hand.')
  }
}

async function save() {
  error.value = ''
  problem.value = temporaryPasswordProblem(password.value) ?? ''
  if (problem.value) {
    document.getElementById('reset_password')?.focus()
    return
  }
  const ok = await confirm({
    title: `Set a temporary password for ${props.user.name_en}?`,
    text: 'They are signed out everywhere and must choose a new password when they next sign in.',
    confirmLabel: 'Set password',
    icon: 'warning',
  })
  if (!ok) return
  saving.value = true
  try {
    await resetPassword(api, props.user.id, password.value)
    password.value = ''
    toast.show('Temporary password set', `${props.user.name_en} must choose a new one at the next sign-in.`)
  } catch (err) {
    error.value = err instanceof ApiError ? (err.fields.temporary_password ?? err.message) : 'Something went wrong.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="password">
    <div v-if="error" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <b>{{ error }}</b>
    </div>
    <p class="lead">They are signed out everywhere and must choose a new password when they next sign in.</p>
    <BaseField id="reset_password" label="Temporary password" hint="8 to 128 characters" :error="problem">
      <template #default="{ describedBy, invalid }">
        <PasswordInput id="reset_password" v-model="password" autocomplete="new-password" :described-by="describedBy" :invalid="invalid" />
      </template>
    </BaseField>
    <div class="tools">
      <BaseButton variant="quiet" @click="generate">
        <KeyRound aria-hidden="true" />
        Generate
      </BaseButton>
      <BaseButton variant="quiet" :disabled="!password" @click="copy">
        <Copy aria-hidden="true" />
        Copy
      </BaseButton>
      <span class="spacer" />
      <BaseButton variant="primary" :busy="saving" :disabled="!password" @click="save">
        {{ saving ? 'Setting' : 'Set temporary password' }}
      </BaseButton>
    </div>
  </div>
</template>

<style scoped>
.password {
  display: grid;
  gap: 12px;
}
.lead {
  margin: 0;
  font-size: 13px;
  color: var(--color-intaglio);
}
.tools {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.spacer {
  flex: 1;
}
</style>
