<script setup lang="ts">
// Roles (DSH-U08): the six fixed roles with how many active users have each. Only the names can
// change; the open role lives in the address (?id=3), so a reload keeps its panel open.
import { CircleAlert, Ellipsis } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '../api'
import { ApiError } from '../api/errors'
import type { RoleOut } from '../api/types'
import { countUsersWithRole, listRoles } from '../api/users'
import BaseButton from '../components/base/BaseButton.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { usePanelParam } from '../composables/usePanelParam'
import RolePanel from './people/RolePanel.vue'

const NEED_DIVISION = new Set(['PITIKA', 'IT_LEAD', 'IT_STAFF'])

const panel = usePanelParam()
const roles = ref<RoleOut[] | null>(null)
const users = ref<Record<string, number>>({})
const loading = ref(false)
const error = ref('')
const savedId = ref<number | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    roles.value = await listRoles(api)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
    return
  } finally {
    loading.value = false
  }
  // The counts come one request per role; each fills in when it arrives.
  for (const role of roles.value) {
    countUsersWithRole(api, role.code)
      .then((n) => (users.value = { ...users.value, [role.code]: n }))
      .catch(() => undefined)
  }
}
onMounted(load)

const count = computed(() => {
  const n = roles.value?.length ?? 0
  return `${String(n).padStart(3, '0')} ${n === 1 ? 'role' : 'roles'}`
})
const openRole = computed(() => roles.value?.find((r) => r.id === panel.id.value) ?? null)

function onSaved(role: RoleOut) {
  roles.value = roles.value?.map((r) => (r.id === role.id ? role : r)) ?? null
  savedId.value = role.id
  panel.close()
}

const SKELETON_COLUMNS = ['140px', '2fr', '80px', '1.2fr', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Roles</h1>
      <span v-if="roles" class="mono count">{{ count }}</span>
    </div>

    <div class="sheet">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && !roles" :columns="SKELETON_COLUMNS" />
      <div v-else-if="roles" class="table-scroll">
        <table class="list">
          <caption class="sr-only">Roles</caption>
          <thead>
            <tr>
              <th scope="col">Code</th>
              <th scope="col">Role</th>
              <th class="num" scope="col">Users</th>
              <th scope="col"><span class="sr-only">Rule</span></th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="role in roles"
              :key="role.id"
              :class="{ 'just-saved': role.id === savedId }"
              tabindex="0"
              @click="panel.open(role.id)"
              @keydown.enter="panel.open(role.id)"
            >
              <td><span class="code mono">{{ role.code }}</span></td>
              <td class="name-plate">
                <span class="kh">{{ role.name_kh }}</span>
                <span class="en">{{ role.name_en }}</span>
              </td>
              <td class="num"><span class="users mono">{{ users[role.code] ?? '–' }}</span></td>
              <td><span v-if="NEED_DIVISION.has(role.code)" class="rule">Needs a division</span></td>
              <td class="row-actions">
                <button type="button" class="icon-btn" :aria-label="`Open ${role.name_en}`" @click.stop="panel.open(role.id)">
                  <Ellipsis aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <RolePanel v-if="openRole" :key="`role-${openRole.id}`" :role="openRole" @saved="onSaved" @close="panel.close" />
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.code {
  font-size: 12.5px;
}
.rule {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
</style>
