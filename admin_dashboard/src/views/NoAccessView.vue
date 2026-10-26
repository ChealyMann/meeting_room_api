<script setup lang="ts">
import { LogOut } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import BaseButton from '../components/base/BaseButton.vue'
import AuthFrame from '../layouts/AuthFrame.vue'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const router = useRouter()
const busy = ref(false)

async function signOut() {
  busy.value = true
  await session.signOut()
  busy.value = false
  await router.replace({ name: 'sign-in' })
}
</script>

<template>
  <AuthFrame title="You do not have access">
    <p class="lead">
      This dashboard is for administrators. Your account
      <b v-if="session.user">{{ session.user.email }}</b> does not have the Admin role.
    </p>
    <p class="hint">Ask an administrator to add the role, then sign in again.</p>
    <BaseButton :busy="busy" @click="signOut">
      <LogOut v-if="!busy" aria-hidden="true" />
      {{ busy ? 'Signing out' : 'Sign out' }}
    </BaseButton>
  </AuthFrame>
</template>

<style scoped>
.lead {
  margin: 0;
  max-width: 40ch;
}
.lead b {
  font-weight: 500;
  overflow-wrap: anywhere;
}
.hint {
  margin: 8px 0 24px;
  font-size: 13px;
  color: var(--color-intaglio);
}
</style>
