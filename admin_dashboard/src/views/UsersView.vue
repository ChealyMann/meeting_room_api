<script setup lang="ts">
// Users (DSH-U01, U02): a filtered, paged list. The open user lives in the address (?id=7, with
// &tab=roles and so on; ?id=new for a new user), so a reload keeps the panel open.
import { CircleAlert, Ellipsis, LoaderCircle, Plus } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import type { RoleOut, UserDetail, UserListItem } from '../api/types'
import { getUser, listRoles, listUserPage, type UserFilters as UserFilterParams } from '../api/users'
import BaseButton from '../components/base/BaseButton.vue'
import EmptyState from '../components/list/EmptyState.vue'
import PagingFoot from '../components/list/PagingFoot.vue'
import StateMarks from '../components/list/StateMarks.vue'
import TableSkeleton from '../components/list/TableSkeleton.vue'
import { usePanelParam } from '../composables/usePanelParam'
import { usePanelRecord } from '../composables/usePanelRecord'
import { useResourceList } from '../composables/useResourceList'
import { serial } from '../utils/serial'
import { formatPhnomPenh } from '../utils/time'
import NewUserPanel from './people/NewUserPanel.vue'
import UserPanel, { type UserTab } from './people/UserPanel.vue'
import UserFilters from './people/UserFilters.vue'
import { USER_FILTERS } from './people/userFilters'

const route = useRoute()
const router = useRouter()
const { list, result, loading, error, filtered, savedId, load, refresh } = useResourceList<UserListItem>(
  USER_FILTERS,
  (params) => listUserPage(api, params as UserFilterParams),
)
const panel = usePanelParam()

const roles = ref<RoleOut[]>([])
onMounted(async () => {
  roles.value = await listRoles(api)
})
const roleName = (code: string) => roles.value.find((r) => r.code === code)?.name_en ?? code
const fullName = (u: UserListItem) => (u.title ? `${u.title} ${u.name_en}` : u.name_en)

const total = computed(() => result.value?.total ?? 0)
const count = computed(() => `${String(total.value).padStart(3, '0')} ${total.value === 1 ? 'user' : 'users'}`)

/** A new user has no roles yet: their panel opens on the Roles tab. */
async function onCreated(user: UserDetail) {
  void router.push({ query: { ...route.query, id: String(user.id), tab: 'roles' } })
  await refresh(user.id)
}

// The user is loaded before the panel opens (see usePanelRecord), so a reload on ?id=… works too.
const { record: openUser, error: openError, openingId, load: loadOpen } = usePanelRecord(panel.id, (id) => getUser(api, id))
const TABS: UserTab[] = ['details', 'roles', 'password', 'signature']
const tab = computed(() => {
  const value = route.query.tab
  return TABS.find((t) => t === value) ?? 'details'
})
function setTab(name: UserTab) {
  void router.replace({ query: { ...route.query, tab: name === 'details' ? undefined : name } })
}
/** Another user's panel, or none, starts on Details again. */
function withoutTab() {
  const query = { ...route.query }
  delete query.tab
  return query
}
function show(id: number) {
  void router.push({ query: { ...withoutTab(), id: String(id) } })
}
function closePanel() {
  const query = withoutTab()
  delete query.id
  void router.push({ query })
}

/** The panel stays open after a save: show the new values and refresh the list. */
async function onSaved(user: UserDetail) {
  openUser.value = user
  await refresh(user.id)
}

const SKELETON_COLUMNS = ['72px', '1.6fr', '96px', '1.4fr', '1.2fr', '1fr', '96px', '120px', '32px']
</script>

<template>
  <div class="places-page">
    <div class="page-head">
      <h1>Users</h1>
      <span v-if="result" class="mono count">{{ count }}</span>
      <BaseButton variant="primary" class="new" @click="panel.open('new')">
        <Plus aria-hidden="true" />
        New user
      </BaseButton>
    </div>

    <UserFilters :roles="roles" />

    <div v-if="openError" class="summary open-error" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ serial('US', panel.id.value) }}: {{ openError }}</b>
        <BaseButton variant="quiet" @click="loadOpen">Try again</BaseButton>
        <BaseButton variant="quiet" @click="closePanel">Close</BaseButton>
      </div>
    </div>

    <div class="sheet">
      <div v-if="error" class="summary load-error" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ error }}</b>
          <BaseButton variant="quiet" @click="load">Try again</BaseButton>
        </div>
      </div>
      <TableSkeleton v-else-if="loading && !result" :columns="SKELETON_COLUMNS" />
      <template v-else-if="result && !result.items.length">
        <EmptyState v-if="filtered" title="No users match" text="Nothing matches these filters.">
          <BaseButton @click="list.reset()">Clear filters</BaseButton>
          <BaseButton variant="primary" @click="panel.open('new')">New user</BaseButton>
        </EmptyState>
        <EmptyState v-else title="No users yet" text="Add the first user.">
          <BaseButton variant="primary" @click="panel.open('new')">New user</BaseButton>
        </EmptyState>
      </template>
      <div v-else-if="result" class="table-scroll" :aria-busy="loading || undefined">
        <table class="list">
          <caption class="sr-only">Users</caption>
          <thead>
            <tr>
              <th class="col-serial" scope="col">Serial</th>
              <th scope="col">Name</th>
              <th class="col-staff" scope="col">Staff ID</th>
              <th class="col-email" scope="col">Email</th>
              <th class="col-work" scope="col">Work</th>
              <th scope="col">Roles</th>
              <th scope="col">State</th>
              <th class="col-last" scope="col">Last sign-in</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="user in result.items"
              :key="user.id"
              :class="{ 'is-off': !user.is_active, 'just-saved': user.id === savedId }"
              tabindex="0"
              :aria-busy="user.id === openingId || undefined"
              @click="show(user.id)"
              @keydown.enter="show(user.id)"
            >
              <td class="col-serial"><span class="serial"><span class="prefix">US</span>·{{ String(user.id).padStart(4, '0') }}</span></td>
              <td class="name-plate">
                <span class="kh">{{ user.name_kh }}</span>
                <span class="en">{{ fullName(user) }}</span>
              </td>
              <td class="col-staff mono">{{ user.staff_id }}</td>
              <td class="col-email email">{{ user.email }}</td>
              <td class="col-work work">
                <span class="division" :class="{ none: !user.division }">{{ user.division?.name_en ?? 'No division' }}</span>
                <span class="position">{{ user.position.name_en }}<template v-if="user.province"> · {{ user.province.name_en }}</template></span>
              </td>
              <td>
                <span v-if="user.role_codes.length" class="chips">
                  <span v-for="code in user.role_codes" :key="code" class="chip">{{ roleName(code) }}</span>
                </span>
                <span v-else class="none">No roles</span>
              </td>
              <td class="state-col"><StateMarks :active="user.is_active" /></td>
              <td class="col-last">
                <span class="last mono" :class="{ none: !user.last_login_at }">{{ user.last_login_at ? formatPhnomPenh(user.last_login_at) : 'Never' }}</span>
              </td>
              <td class="row-actions">
                <button type="button" class="icon-btn" :aria-label="`Open ${user.name_en}`" @click.stop="show(user.id)">
                  <LoaderCircle v-if="user.id === openingId" class="spin" aria-hidden="true" />
                  <Ellipsis v-else aria-hidden="true" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <NewUserPanel v-if="panel.isNew.value" @created="onCreated" @close="panel.close" />
    <UserPanel
      v-else-if="openUser"
      :key="`user-${openUser.id}`"
      :user="openUser"
      :roles="roles"
      :tab="tab"
      @saved="onSaved"
      @tab="setTab"
      @close="closePanel"
    />

    <PagingFoot
      v-if="result && total > 0"
      :page="list.page.value"
      :size="list.size.value"
      :total="total"
      @update:page="list.page.value = $event"
      @update:size="list.size.value = $event"
    />
  </div>
</template>

<style scoped src="./listPage.css"></style>

<style scoped>
.email {
  overflow-wrap: anywhere;
}
.work span {
  display: block;
}
.work .position {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.chip {
  padding: 1px 8px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 999px;
  font-size: 12px;
  white-space: nowrap;
}
.none {
  color: var(--color-ink-off);
}
.last {
  font-size: 12px;
  white-space: nowrap;
}
@media (max-width: 1280px) {
  .col-email {
    display: none;
  }
}
@media (max-width: 1100px) {
  .col-staff,
  .col-last {
    display: none;
  }
}
@media (max-width: 760px) {
  .col-work {
    display: none;
  }
}
</style>
