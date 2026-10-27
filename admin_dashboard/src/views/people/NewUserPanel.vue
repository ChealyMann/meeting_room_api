<script setup lang="ts">
// Create a user in the side panel (DSH-U02). The new user has no roles yet, so the page then
// opens their panel on the Roles tab. The draft keeps the typing across a forced sign-in, but
// never the temporary password.
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { listDepartments, listDivisions, listPositions } from '../../api/references'
import type { DepartmentOut, DivisionOut, PositionOut, UserDetail } from '../../api/types'
import { createUser } from '../../api/users'
import BaseButton from '../../components/base/BaseButton.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import { serial } from '../../utils/serial'
import { emptyUserForm, userCreateBody, userProblems, type UserForm } from '../../utils/userForms'
import UserDetailsForm from './UserDetailsForm.vue'

const emit = defineEmits<{ created: [user: UserDetail]; close: [] }>()

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
  temporary_password: 'Temporary password',
}
const DRAFT = 'user:new'

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

interface UserDraft {
  updatedAt: null
  form: UserForm
}
function restore(): UserForm {
  const draft = drafts.get<UserDraft>(DRAFT)
  return draft ? { ...draft.form, temporary_password: '' } : emptyUserForm()
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

const dirty = computed(() => JSON.stringify({ ...form.value, temporary_password: '' }) !== JSON.stringify(emptyUserForm()))
watch(
  form,
  () =>
    dirty.value
      ? drafts.set(DRAFT, { updatedAt: null, form: { ...form.value, temporary_password: '' } })
      : drafts.clear(DRAFT),
  { deep: true },
)

function close() {
  drafts.clear(DRAFT)
  emit('close')
}

const summary = computed(() =>
  Object.keys(errors.value)
    .filter((key) => key in LABELS)
    .map((key) => ({ id: key, label: LABELS[key] ?? key })),
)

async function focusProblem() {
  await nextTick()
  panel.value?.focusFirst()
}

async function save() {
  clear()
  const problems = userProblems(form.value, true)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  saving.value = true
  try {
    const user = await createUser(api, userCreateBody(form.value))
    drafts.clear(DRAFT)
    toast.show(`${user.name_en} added`, `${serial('US', user.id)} · no roles yet`)
    emit('created', user)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <SidePanel ref="panel" :open="true" title="New user" :serial="serial('US', null)" @close="close">
    <form id="new-user-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>
      <UserDetailsForm
        :form="form"
        :errors="errors"
        creating
        :divisions="divisions"
        :departments="departments"
        :positions="positions"
      />
    </form>

    <template #foot>
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="new-user-form" :busy="saving">
        {{ saving ? 'Creating' : 'Create user' }}
      </BaseButton>
    </template>
  </SidePanel>
</template>

<style scoped>
.form {
  display: grid;
  gap: 20px;
}
</style>
