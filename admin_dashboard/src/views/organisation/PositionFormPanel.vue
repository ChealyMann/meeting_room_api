<script setup lang="ts">
// Create or edit a position (job title) in the side panel (DSH-O03, G03–G07).
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveUsers, createPosition, updatePosition } from '../../api/organisation'
import type { PositionOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import {
  emptyPositionForm,
  positionChanges,
  positionCreateBody,
  positionFormOf,
  positionProblems,
  type PositionForm,
} from '../../utils/orgForms'
import { serial } from '../../utils/serial'

const props = defineProps<{ position: PositionOut | null }>()
const emit = defineEmits<{ saved: [position: PositionOut]; close: [] }>()

const LABELS: Record<string, string> = {
  name_kh: 'Khmer name',
  name_en: 'English name',
  sort_order: 'Order',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the position is unchanged on the server (same updated_at).
interface PositionDraft {
  updatedAt: string | null
  form: PositionForm
}
const draftKey = computed(() => (props.position ? `position:${props.position.id}` : 'position:new'))
const base = () => (props.position ? positionFormOf(props.position) : emptyPositionForm())
function restore(): PositionForm {
  const draft = drafts.get<PositionDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.position?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<PositionForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.position ? positionChanges(form.value, props.position) : null))
const dirty = computed(() =>
  props.position
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(emptyPositionForm()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.position?.updated_at ?? null, form: form.value })
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

function done(position: PositionOut, title: string) {
  drafts.clear(draftKey.value)
  toast.show(title, serial('PS', position.id))
  emit('saved', position)
}

async function save() {
  clear()
  const problems = positionProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.position && !dirty.value) return
  saving.value = true
  try {
    const position = props.position
      ? await updatePosition(api, props.position.id, changes.value ?? {})
      : await createPosition(api, positionCreateBody(form.value))
    done(position, `${position.name_en} saved`)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const position = await updatePosition(api, props.position!.id, { is_active: active })
  done(position, `${position.name_en} turned ${active ? 'on' : 'off'}`)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="position ? position.name_kh : 'New position'"
    :subtitle="position?.name_en"
    :serial="serial('PS', position?.id ?? null)"
    @close="close"
  >
    <form id="position-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

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
      </section>

      <section class="group" aria-labelledby="g-order">
        <h3 id="g-order">Order</h3>
        <BaseField id="sort_order" label="Order" hint="Lower comes first" :error="errors.sort_order">
          <template #default="{ describedBy, invalid }">
            <input id="sort_order" v-model="form.sort_order" class="input mono order" inputmode="numeric" placeholder="0" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
      </section>
    </form>

    <template #foot>
      <ActiveToggle
        v-if="position"
        class="toggle"
        :active="position.is_active"
        :name="position.name_en"
        kind="position"
        :count="() => countActiveUsers(api, { position_id: position!.id })"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="position-form" :busy="saving" :disabled="!!position && !dirty">
        {{ saving ? (position ? 'Saving' : 'Creating') : position ? 'Save changes' : 'Create position' }}
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
/* Turn off sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
</style>
