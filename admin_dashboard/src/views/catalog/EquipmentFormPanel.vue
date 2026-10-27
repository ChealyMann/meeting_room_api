<script setup lang="ts">
// Create or edit an equipment item in the side panel (DSH-C02, G03–G07): its one name, order and icon.
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveRooms } from '../../api/places'
import { createEquipment, updateEquipment } from '../../api/catalog'
import type { EquipmentOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import IconPicker from '../../components/IconPicker.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import {
  emptyEquipmentForm,
  equipmentChanges,
  equipmentCreateBody,
  equipmentFormOf,
  equipmentProblems,
  type EquipmentForm,
} from '../../utils/catalogForms'
import { serial } from '../../utils/serial'

const props = defineProps<{ item: EquipmentOut | null }>()
const emit = defineEmits<{ saved: [item: EquipmentOut]; close: [] }>()

const LABELS: Record<string, string> = {
  name: 'Name',
  sort_order: 'Order',
  icon: 'Icon',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the item is unchanged on the server (same updated_at).
interface EquipmentDraft {
  updatedAt: string | null
  form: EquipmentForm
}
const draftKey = computed(() => (props.item ? `equipment:${props.item.id}` : 'equipment:new'))
const base = () => (props.item ? equipmentFormOf(props.item) : emptyEquipmentForm())
function restore(): EquipmentForm {
  const draft = drafts.get<EquipmentDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.item?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<EquipmentForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.item ? equipmentChanges(form.value, props.item) : null))
const dirty = computed(() =>
  props.item
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(emptyEquipmentForm()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.item?.updated_at ?? null, form: form.value })
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

function done(item: EquipmentOut, title: string) {
  drafts.clear(draftKey.value)
  toast.show(title, serial('EQ', item.id))
  emit('saved', item)
}

async function save() {
  clear()
  const problems = equipmentProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.item && !dirty.value) return
  saving.value = true
  try {
    const item = props.item
      ? await updateEquipment(api, props.item.id, changes.value ?? {})
      : await createEquipment(api, equipmentCreateBody(form.value))
    done(item, `${item.name} saved`)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const item = await updateEquipment(api, props.item!.id, { is_active: active })
  done(item, `${item.name} is now ${active ? 'active' : 'inactive'}`)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="item ? item.name : 'New item'"
    :serial="serial('EQ', item?.id ?? null)"
    @close="close"
  >
    <form id="equipment-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <section class="group" aria-labelledby="g-item">
        <h3 id="g-item">Item</h3>
        <BaseField id="name" label="Name" :hint="`${count(form.name)}/200`" :error="errors.name">
          <template #default="{ describedBy, invalid }">
            <input id="name" v-model="form.name" class="input" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
        <BaseField id="sort_order" label="Order" hint="Lower comes first" :error="errors.sort_order">
          <template #default="{ describedBy, invalid }">
            <input id="sort_order" v-model="form.sort_order" class="input mono order" inputmode="numeric" placeholder="0" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
          </template>
        </BaseField>
      </section>

      <section class="group" aria-labelledby="g-icon">
        <h3 id="g-icon">Icon</h3>
        <IconPicker id="icon" v-model="form.icon" />
        <p v-if="errors.icon" id="icon-error" class="error" role="alert">{{ errors.icon }}</p>
      </section>
    </form>

    <template #foot>
      <ActiveToggle
        v-if="item"
        class="toggle"
        :active="item.is_active"
        :name="item.name"
        kind="equipment"
        :count="() => countActiveRooms(api, { equipment_ids: [item!.id] })"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="equipment-form" :busy="saving" :disabled="!!item && !dirty">
        {{ saving ? (item ? 'Saving' : 'Creating') : item ? 'Save changes' : 'Create item' }}
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
.error {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-crimson);
}
/* The Active switch sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
</style>
