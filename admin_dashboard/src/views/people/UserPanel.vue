<script setup lang="ts">
// One user in the side panel (DSH-U03–U07): details, roles, a temporary password and the
// signature as tabs, with turn off/on in the foot. It stays open after a save, so an Admin can
// choose a division on Details and then the role that needs it.
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { listDepartments, listDivisions, listPositions } from '../../api/references'
import type { DepartmentOut, DivisionOut, PositionOut, RoleOut, UserChanged, UserDetail } from '../../api/types'
import { deleteUserSignature, updateUser, uploadUserSignature } from '../../api/users'
import BaseButton from '../../components/base/BaseButton.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import SignatureField from '../../components/SignatureField.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import { useSessionStore } from '../../stores/session'
import { serial } from '../../utils/serial'
import { userChanges, userFormOf, userProblems, type UserForm } from '../../utils/userForms'
import UserDetailsForm from './UserDetailsForm.vue'
import UserPassword from './UserPassword.vue'
import UserRoles from './UserRoles.vue'

export type UserTab = 'details' | 'roles' | 'password' | 'signature'

const props = defineProps<{ user: UserDetail; roles: RoleOut[]; tab?: UserTab }>()
const emit = defineEmits<{ saved: [user: UserDetail]; close: []; tab: [name: UserTab] }>()

const TABS: Array<{ id: UserTab; label: string }> = [
  { id: 'details', label: 'Details' },
  { id: 'roles', label: 'Roles' },
  { id: 'password', label: 'Password' },
  { id: 'signature', label: 'Signature' },
]
const LABELS: Record<string, string> = {
  title: 'Title',
  staff_id: 'Staff ID',
  name_kh: 'Khmer name',
  name_en: 'English name',
  email: 'Email',
  secondary_email: 'Second email',
  phone: 'Phone',
  division_id: 'Division',
  position_id: 'Position',
}

const drafts = useDraftsStore()
const session = useSessionStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

const tab = ref<UserTab>(props.tab ?? 'details')
watch(
  () => props.tab,
  (name) => (tab.value = name ?? 'details'),
)
function choose(name: UserTab) {
  tab.value = name
  emit('tab', name)
}

const self = computed(() => session.user?.id === props.user.id)
const fullName = computed(() => (props.user.title ? `${props.user.title} ${props.user.name_en}` : props.user.name_en))

// Details. A draft keeps typing across a forced sign-in (DSH-A06) while the user is unchanged on
// the server (same updated_at); Cancel and close drop it. The password is never in it.
interface UserDraft {
  updatedAt: string
  form: UserForm
}
const draftKey = `user:${props.user.id}`
function restore(): UserForm {
  const draft = drafts.get<UserDraft>(draftKey)
  if (draft && draft.updatedAt === props.user.updated_at) return { ...draft.form, temporary_password: '' }
  drafts.clear(draftKey)
  return userFormOf(props.user)
}
const form = ref<UserForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const divisions = ref<DivisionOut[]>([])
const departments = ref<DepartmentOut[]>([])
const positions = ref<PositionOut[]>([])
onMounted(async () => {
  const [v, d, p] = await Promise.all([listDivisions(api), listDepartments(api), listPositions(api)])
  divisions.value = v
  departments.value = d
  positions.value = p
})

const changes = computed(() => userChanges(form.value, props.user))
const dirty = computed(() => Object.keys(changes.value).length > 0)
watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey, { updatedAt: props.user.updated_at, form: { ...form.value, temporary_password: '' } })
      : drafts.clear(draftKey),
  { deep: true },
)

const summary = computed(() =>
  Object.keys(errors.value)
    .filter((key) => key in LABELS)
    .map((key) => ({ id: key, label: LABELS[key] ?? key })),
)

function close() {
  drafts.clear(draftKey)
  emit('close')
}
function cancel() {
  clear()
  form.value = userFormOf(props.user)
  drafts.clear(draftKey)
}

// Turning a user off or taking Room owner away clears the rooms they own: the last answer's
// rooms show here, each linked to its panel on the Rooms page.
const unassigned = ref<number[]>([])
/** Turning off clears every room they own: the turn-off warning's number. */
const ownedRooms = () => Promise.resolve(props.user.owned_room_ids.length)
function changed(user: UserChanged) {
  unassigned.value = user.rooms_unassigned
  emit('saved', user)
}

async function save() {
  clear()
  const problems = userProblems(form.value, false)
  if (Object.keys(problems).length) {
    errors.value = problems
    await nextTick()
    panel.value?.focusFirst()
    return
  }
  if (!dirty.value) return
  saving.value = true
  try {
    const user = await updateUser(api, props.user.id, changes.value)
    drafts.clear(draftKey)
    form.value = userFormOf(user)
    toast.show(`${user.name_en} saved`, serial('US', user.id))
    changed(user)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) {
      await nextTick()
      panel.value?.focusFirst()
    }
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const user = await updateUser(api, props.user.id, { is_active: active })
  toast.show(`${user.name_en} turned ${active ? 'on' : 'off'}`, serial('US', user.id))
  changed(user)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="user.name_kh"
    :subtitle="fullName"
    :serial="serial('US', user.id)"
    @close="close"
  >
    <div v-if="unassigned.length" class="unassigned" role="status">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>These rooms have no owner now:</b>
        <span class="rooms">
          <RouterLink v-for="id in unassigned" :key="id" class="serial" :to="{ name: 'home', query: { room: String(id) } }">
            {{ serial('RM', id) }}
          </RouterLink>
        </span>
      </div>
    </div>

    <div class="tabs" role="tablist" aria-label="User">
      <button
        v-for="t in TABS"
        :id="`tab-${t.id}`"
        :key="t.id"
        type="button"
        role="tab"
        :aria-selected="tab === t.id"
        :aria-controls="`tabpanel-${t.id}`"
        @click="choose(t.id)"
      >
        {{ t.label }}
      </button>
    </div>

    <section v-show="tab === 'details'" id="tabpanel-details" role="tabpanel" aria-labelledby="tab-details">
      <form id="user-form" class="form" novalidate @submit.prevent="save">
        <FormErrorSummary :errors="summary" />
        <div v-if="formMessage" class="summary" role="alert">
          <CircleAlert aria-hidden="true" />
          <b>{{ formMessage }}</b>
        </div>
        <UserDetailsForm
          :form="form"
          :errors="errors"
          :creating="false"
          :divisions="divisions"
          :departments="departments"
          :positions="positions"
        />
      </form>
    </section>
    <section v-show="tab === 'roles'" id="tabpanel-roles" role="tabpanel" aria-labelledby="tab-roles">
      <UserRoles :user="user" :roles="roles" :self="self" @saved="changed" />
    </section>
    <section v-if="tab === 'password'" id="tabpanel-password" role="tabpanel" aria-labelledby="tab-password">
      <UserPassword :user="user" />
    </section>
    <section v-if="tab === 'signature'" id="tabpanel-signature" role="tabpanel" aria-labelledby="tab-signature">
      <SignatureField
        :signature-url="user.signature_url"
        :upload="(file: File) => uploadUserSignature(api, user.id, file)"
        :remove="() => deleteUserSignature(api, user.id)"
        :owner-name="user.name_en"
      />
    </section>

    <template #foot>
      <ActiveToggle
        class="toggle"
        :active="user.is_active"
        :name="user.name_en"
        kind="user"
        :count="ownedRooms"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
        :locked="self ? 'You cannot turn yourself off.' : undefined"
      />
      <template v-if="tab === 'details'">
        <BaseButton variant="quiet" :disabled="!dirty" @click="cancel">Cancel</BaseButton>
        <BaseButton variant="primary" type="submit" form="user-form" :busy="saving" :disabled="!dirty">
          {{ saving ? 'Saving' : 'Save changes' }}
        </BaseButton>
      </template>
    </template>
  </SidePanel>
</template>

<style scoped>
.form {
  display: grid;
  gap: 20px;
}
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--color-rule);
}
.tabs button {
  margin-bottom: -1px;
  padding: 8px 10px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--color-intaglio);
  font-size: 13px;
  cursor: pointer;
}
.tabs button[aria-selected='true'] {
  border-bottom-color: var(--color-crimson);
  color: var(--color-ink);
  font-weight: 500;
}
.unassigned {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  background: var(--color-paper);
  font-size: 13px;
}
.unassigned svg {
  flex: none;
  width: 16px;
  height: 16px;
  margin-top: 2px;
  color: var(--color-crimson);
}
.unassigned b {
  display: block;
  font-weight: 500;
}
.rooms {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-top: 4px;
}
.rooms a {
  color: var(--color-crimson);
}
/* Turn off sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
</style>
