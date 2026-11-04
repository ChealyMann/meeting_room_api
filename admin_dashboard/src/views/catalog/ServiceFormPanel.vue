<script setup lang="ts">
// Create or edit a catering package or an IT service in the side panel (G03–G07). Every change
// sends the version that was read; if someone saved first (409 STALE_VERSION), "Reload" loads
// the new record.
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { createService, getService, updateService, type ServiceKind, type ServiceOut, type ServiceUpdate } from '../../api/services'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import { serial } from '../../utils/serial'
import {
  emptyServiceForm,
  SERVICE_KINDS,
  serviceChanges,
  serviceCreateBody,
  serviceFormOf,
  serviceProblems,
  type ServiceForm,
} from '../../utils/serviceForms'

const props = defineProps<{ kind: ServiceKind; item: ServiceOut | null }>()
const emit = defineEmits<{ saved: [item: ServiceOut]; close: [] }>()

const words = computed(() => SERVICE_KINDS[props.kind])
const LABELS: Record<string, string> = {
  name: 'Name',
  description: 'Description',
  sort_order: 'Order',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// The record shown: the prop, or the one "Reload" fetched after a STALE_VERSION.
const current = ref<ServiceOut | null>(props.item)
const stale = ref(false)
const reloading = ref(false)

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the record is unchanged on the server (same version).
interface ServiceDraft {
  version: number | null
  form: ServiceForm
}
const draftKey = computed(() => `${props.kind}:${props.item ? props.item.id : 'new'}`)
const base = () => (current.value ? serviceFormOf(current.value) : emptyServiceForm())
function restore(): ServiceForm {
  const draft = drafts.get<ServiceDraft>(draftKey.value)
  if (draft && draft.version === (current.value?.version ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<ServiceForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (current.value ? serviceChanges(form.value, current.value) : null))
const dirty = computed(() =>
  current.value
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(emptyServiceForm()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { version: current.value?.version ?? null, form: form.value })
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

function done(item: ServiceOut, title: string) {
  drafts.clear(draftKey.value)
  toast.show(title, serial(words.value.serial, item.id))
  emit('saved', item)
}

function failed(err: unknown) {
  apply(err)
  stale.value = err instanceof ApiError && err.code === 'STALE_VERSION'
  if (summary.value.length) formMessage.value = ''
}

async function save() {
  clear()
  stale.value = false
  const problems = serviceProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (current.value && !dirty.value) return
  saving.value = true
  try {
    const item = current.value
      ? await updateService(api, props.kind, current.value.id, changes.value as ServiceUpdate)
      : await createService(api, props.kind, serviceCreateBody(form.value))
    done(item, `${item.name} saved`)
  } catch (err) {
    failed(err)
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

/** After a STALE_VERSION: load the saved record and start again from it. */
async function reload() {
  if (!current.value) return
  reloading.value = true
  try {
    current.value = await getService(api, props.kind, current.value.id)
    drafts.clear(draftKey.value)
    form.value = serviceFormOf(current.value)
    clear()
    stale.value = false
  } catch (err) {
    failed(err)
  } finally {
    reloading.value = false
  }
}

async function turn(active: boolean) {
  const item = await updateService(api, props.kind, current.value!.id, { is_active: active, version: current.value!.version })
  done(item, `${item.name} is now ${active ? 'active' : 'inactive'}`)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="current ? current.name : words.newLabel"
    :serial="serial(words.serial, current?.id ?? null)"
    @close="close"
  >
    <form id="service-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <div>
          <b>{{ formMessage }}</b>
          <BaseButton v-if="stale" variant="quiet" :busy="reloading" @click="reload">Reload</BaseButton>
        </div>
      </div>

      <section class="group" aria-labelledby="g-service">
        <h3 id="g-service">{{ kind === 'catering' ? 'Package' : 'Service' }}</h3>
        <BaseField id="name" label="Name" :hint="`${count(form.name)}/200`" :error="errors.name">
          <template #default="{ describedBy, invalid }">
            <input id="name" v-model="form.name" class="input" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
        <BaseField id="description" label="Description" :hint="`${count(form.description)}/1000`" :error="errors.description">
          <template #default="{ describedBy, invalid }">
            <textarea id="description" v-model="form.description" class="input" rows="3" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
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
        v-if="current"
        class="toggle"
        :active="current.is_active"
        :name="current.name"
        :kind="words.kind"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="service-form" :busy="saving" :disabled="!!current && !dirty">
        {{ saving ? (current ? 'Saving' : 'Creating') : current ? 'Save changes' : `Create ${words.one}` }}
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
  min-width: 0;
}
h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}
textarea.input {
  min-height: 72px;
}
.order {
  max-width: 160px;
}
/* The Active switch sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
</style>
