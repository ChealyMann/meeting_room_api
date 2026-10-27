<script setup lang="ts">
// Create, edit or move a division in the side panel (DSH-O02, G03–G08).
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveUsers, createDivision, updateDivision } from '../../api/organisation'
import { listDepartments, listOffices } from '../../api/references'
import type { DepartmentOut, DivisionOut, LocationOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import DepartmentPicker from '../../components/list/DepartmentPicker.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import { departmentGroups } from '../../utils/departmentOptions'
import {
  divisionChanges,
  divisionCreateBody,
  divisionFormOf,
  divisionProblems,
  emptyDivisionForm,
  type DivisionForm,
} from '../../utils/orgForms'
import { serial } from '../../utils/serial'

const props = defineProps<{ division: DivisionOut | null; defaultDepartmentId?: number | null }>()
const emit = defineEmits<{ saved: [division: DivisionOut]; close: [] }>()

const LABELS: Record<string, string> = {
  department_id: 'Department',
  name_kh: 'Khmer name',
  name_en: 'English name',
  short_name: 'Short name',
  sort_order: 'Order',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the division is unchanged on the server (same updated_at).
interface DivisionDraft {
  updatedAt: string | null
  form: DivisionForm
}
const draftKey = computed(() => (props.division ? `division:${props.division.id}` : 'division:new'))
const base = () =>
  props.division ? divisionFormOf(props.division) : emptyDivisionForm(props.defaultDepartmentId ?? null)
function restore(): DivisionForm {
  const draft = drafts.get<DivisionDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.division?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<DivisionForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const offices = ref<LocationOut[]>([])
const departments = ref<DepartmentOut[]>([])
onMounted(async () => {
  const [o, d] = await Promise.all([listOffices(api), listDepartments(api)])
  offices.value = o
  departments.value = d
})
// One group per office: the office is how an admin tells the IT departments apart.
const groups = computed(() => departmentGroups(departments.value, offices.value, form.value.department_id))
const departmentName = (id: number) => departments.value.find((d) => d.id === id)?.name_en ?? `#${id}`

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.division ? divisionChanges(form.value, props.division) : null))
const dirty = computed(() =>
  props.division
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(base()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.division?.updated_at ?? null, form: form.value })
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

function done(division: DivisionOut, title: string) {
  drafts.clear(draftKey.value)
  toast.show(title, `${serial('DV', division.id)} · ${departmentName(division.department_id)}`)
  emit('saved', division)
}

async function save() {
  clear()
  const problems = divisionProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.division && !dirty.value) return
  saving.value = true
  try {
    const division = props.division
      ? await updateDivision(api, props.division.id, changes.value ?? {})
      : await createDivision(api, divisionCreateBody(form.value))
    done(division, `${division.name_en} saved`)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const division = await updateDivision(api, props.division!.id, { is_active: active })
  done(division, `${division.name_en} turned ${active ? 'on' : 'off'}`)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="division ? division.name_kh : 'New division'"
    :subtitle="division?.name_en"
    :serial="serial('DV', division?.id ?? null)"
    @close="close"
  >
    <form id="division-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <section class="group" aria-labelledby="g-where">
        <h3 id="g-where">Where</h3>
        <BaseField
          id="department_id"
          label="Department"
          :hint="division ? 'Change to move the division' : undefined"
          :error="errors.department_id"
        >
          <template #default="{ describedBy, invalid }">
            <DepartmentPicker
              id="department_id"
              mode="field"
              :departments="departments"
              :offices="offices"
              :model-value="form.department_id"
              :invalid="invalid"
              :described-by="division ? `move-help ${describedBy ?? ''}`.trim() : describedBy"
              @update:model-value="form.department_id = $event"
            />
            <p v-if="division" id="move-help" class="help">Its users' province follows the new department's office.</p>
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
        <div class="row2">
          <BaseField id="short_name" label="Short name" :hint="`${count(form.short_name)}/20`" :error="errors.short_name">
            <template #default="{ describedBy, invalid }">
              <input id="short_name" v-model="form.short_name" class="input mono" placeholder="optional, e.g. IT" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
            </template>
          </BaseField>
          <BaseField id="sort_order" label="Order" hint="Lower comes first" :error="errors.sort_order">
            <template #default="{ describedBy, invalid }">
              <input id="sort_order" v-model="form.sort_order" class="input mono" inputmode="numeric" placeholder="0" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
            </template>
          </BaseField>
        </div>
      </section>
    </form>

    <template #foot>
      <ActiveToggle
        v-if="division"
        class="toggle"
        :active="division.is_active"
        :name="division.name_en"
        kind="division"
        :count="() => countActiveUsers(api, { division_id: division!.id })"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="division-form" :busy="saving" :disabled="!!division && !dirty">
        {{ saving ? (division ? 'Saving' : 'Creating') : division ? 'Save changes' : 'Create division' }}
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
.help {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: start;
  gap: 12px;
}
@media (max-width: 760px) {
  .row2 {
    grid-template-columns: minmax(0, 1fr);
  }
}
/* Turn off sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
</style>
