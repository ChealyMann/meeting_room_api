<script setup lang="ts">
// Create, edit or move a department in the side panel (DSH-O01, G03–G08).
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveUsers, createDepartment, updateDepartment } from '../../api/organisation'
import { listOffices } from '../../api/references'
import type { DepartmentOut, LocationOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import OfficePicker from '../../components/list/OfficePicker.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import {
  departmentChanges,
  departmentCreateBody,
  departmentFormOf,
  departmentProblems,
  emptyDepartmentForm,
  type DepartmentForm,
} from '../../utils/orgForms'
import { serial } from '../../utils/serial'

const props = defineProps<{ department: DepartmentOut | null; defaultOfficeId?: number | null }>()
const emit = defineEmits<{ saved: [department: DepartmentOut]; close: [] }>()

const LABELS: Record<string, string> = {
  location_id: 'Office',
  name_kh: 'Khmer name',
  name_en: 'English name',
  sort_order: 'Order',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the department is unchanged on the server (same updated_at).
interface DepartmentDraft {
  updatedAt: string | null
  form: DepartmentForm
}
const draftKey = computed(() => (props.department ? `department:${props.department.id}` : 'department:new'))
const base = () =>
  props.department ? departmentFormOf(props.department) : emptyDepartmentForm(props.defaultOfficeId ?? null)
function restore(): DepartmentForm {
  const draft = drafts.get<DepartmentDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.department?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<DepartmentForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const offices = ref<LocationOut[]>([])
onMounted(async () => {
  offices.value = await listOffices(api)
})
const officeName = (id: number) => offices.value.find((o) => o.id === id)?.name_en ?? `#${id}`

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.department ? departmentChanges(form.value, props.department) : null))
const dirty = computed(() =>
  props.department
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(base()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.department?.updated_at ?? null, form: form.value })
      : drafts.clear(draftKey.value),
  { deep: true },
)

const summary = computed(() =>
  Object.keys(errors.value)
    .filter((key) => key in LABELS)
    .map((key) => ({ id: key, label: LABELS[key] ?? key })),
)
const count = (text: string) => [...text].length

async function focusProblem() {
  await nextTick()
  panel.value?.focusFirst()
}

function done(department: DepartmentOut, title: string) {
  drafts.clear(draftKey.value)
  toast.show(title, `${serial('DP', department.id)} · ${officeName(department.location_id)}`)
  emit('saved', department)
}

async function save() {
  clear()
  const problems = departmentProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.department && !dirty.value) return
  saving.value = true
  try {
    const department = props.department
      ? await updateDepartment(api, props.department.id, changes.value ?? {})
      : await createDepartment(api, departmentCreateBody(form.value))
    done(department, `${department.name_en} saved`)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const department = await updateDepartment(api, props.department!.id, { is_active: active })
  done(department, `${department.name_en} is now ${active ? 'active' : 'inactive'}`)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="department ? department.name_kh : 'New department'"
    :subtitle="department?.name_en"
    :serial="serial('DP', department?.id ?? null)"
    @close="close"
  >
    <form id="department-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <section class="group" aria-labelledby="g-where">
        <h3 id="g-where">Where</h3>
        <BaseField
          id="location_id"
          label="Office"
          :hint="department ? 'Change to move the department' : undefined"
          :error="errors.location_id"
        >
          <template #default="{ describedBy, invalid }">
            <OfficePicker
              id="location_id"
              mode="field"
              :offices="offices"
              :model-value="form.location_id"
              :invalid="invalid"
              :described-by="department ? `move-help ${describedBy ?? ''}`.trim() : describedBy"
              @update:model-value="form.location_id = $event"
            />
            <p v-if="department" id="move-help" class="help">Its users' province changes with it.</p>
          </template>
        </BaseField>
      </section>

      <section class="group" aria-labelledby="g-names">
        <h3 id="g-names">Names</h3>
        <BaseField id="name_kh" label="Khmer name" :hint="`${count(form.name_kh)}/100`" :error="errors.name_kh">
          <template #default="{ describedBy, invalid }">
            <input id="name_kh" v-model="form.name_kh" class="input kh" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
        <BaseField id="name_en" label="English name" :hint="`${count(form.name_en)}/100`" :error="errors.name_en">
          <template #default="{ describedBy, invalid }">
            <input id="name_en" v-model="form.name_en" class="input" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
        <BaseField id="sort_order" label="Order" hint="Lower comes first" :error="errors.sort_order">
          <template #default="{ describedBy, invalid }">
            <input id="sort_order" v-model="form.sort_order" class="input mono order" inputmode="numeric" placeholder="0" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
      </section>
    </form>

    <template #foot>
      <ActiveToggle
        v-if="department"
        class="toggle"
        :active="department.is_active"
        :name="department.name_en"
        kind="department"
        :count="() => countActiveUsers(api, { department_id: department!.id })"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="department-form" :busy="saving" :disabled="!!department && !dirty">
        {{ saving ? (department ? 'Saving' : 'Creating') : department ? 'Save changes' : 'Create department' }}
      </BaseButton>
    </template>
  </SidePanel>
</template>

<style scoped>
.form {
  display: grid;
  gap: 20px;
}
.group {
  display: grid;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--color-rule);
}
.group:first-of-type {
  padding-top: 0;
  border-top: 0;
}
h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}
.order {
  max-width: 160px;
}
.help {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
/* The Active switch sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
</style>
