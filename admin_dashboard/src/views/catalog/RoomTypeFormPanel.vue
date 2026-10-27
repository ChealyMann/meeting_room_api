<script setup lang="ts">
// Create or edit a room type in the side panel (DSH-C01, G03–G07).
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import { countActiveRooms } from '../../api/places'
import { createRoomType, updateRoomType } from '../../api/catalog'
import type { CategoryOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ActiveToggle from '../../components/list/ActiveToggle.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { useDraftsStore } from '../../stores/drafts'
import {
  emptyRoomTypeForm,
  roomTypeChanges,
  roomTypeCreateBody,
  roomTypeFormOf,
  roomTypeProblems,
  type RoomTypeForm,
} from '../../utils/catalogForms'
import { serial } from '../../utils/serial'

const props = defineProps<{ roomType: CategoryOut | null }>()
const emit = defineEmits<{ saved: [roomType: CategoryOut]; close: [] }>()

const LABELS: Record<string, string> = {
  name_kh: 'Khmer name',
  name_en: 'English name',
  sort_order: 'Order',
}

const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

// A draft keeps typing across a forced sign-in (DSH-A06). It is dropped on Cancel/close, and
// for an edit it only counts while the room type is unchanged on the server (same updated_at).
interface RoomTypeDraft {
  updatedAt: string | null
  form: RoomTypeForm
}
const draftKey = computed(() => (props.roomType ? `room-type:${props.roomType.id}` : 'room-type:new'))
const base = () => (props.roomType ? roomTypeFormOf(props.roomType) : emptyRoomTypeForm())
function restore(): RoomTypeForm {
  const draft = drafts.get<RoomTypeDraft>(draftKey.value)
  if (draft && draft.updatedAt === (props.roomType?.updated_at ?? null)) return { ...draft.form }
  drafts.clear(draftKey.value)
  return base()
}
const form = ref<RoomTypeForm>(restore())
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

function close() {
  drafts.clear(draftKey.value)
  emit('close')
}

const changes = computed(() => (props.roomType ? roomTypeChanges(form.value, props.roomType) : null))
const dirty = computed(() =>
  props.roomType
    ? Object.keys(changes.value ?? {}).length > 0
    : JSON.stringify(form.value) !== JSON.stringify(emptyRoomTypeForm()),
)

watch(
  form,
  () =>
    dirty.value
      ? drafts.set(draftKey.value, { updatedAt: props.roomType?.updated_at ?? null, form: form.value })
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

function done(roomType: CategoryOut, title: string) {
  drafts.clear(draftKey.value)
  toast.show(title, serial('RT', roomType.id))
  emit('saved', roomType)
}

async function save() {
  clear()
  const problems = roomTypeProblems(form.value)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (props.roomType && !dirty.value) return
  saving.value = true
  try {
    const roomType = props.roomType
      ? await updateRoomType(api, props.roomType.id, changes.value ?? {})
      : await createRoomType(api, roomTypeCreateBody(form.value))
    done(roomType, `${roomType.name_en} saved`)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
    if (err instanceof ApiError) await focusProblem()
  } finally {
    saving.value = false
  }
}

async function turn(active: boolean) {
  const roomType = await updateRoomType(api, props.roomType!.id, { is_active: active })
  done(roomType, `${roomType.name_en} is now ${active ? 'active' : 'inactive'}`)
}
</script>

<template>
  <SidePanel
    ref="panel"
    :open="true"
    :title="roomType ? roomType.name_kh : 'New room type'"
    :subtitle="roomType?.name_en"
    :serial="serial('RT', roomType?.id ?? null)"
    @close="close"
  >
    <form id="room-type-form" class="form" novalidate @submit.prevent="save">
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
        v-if="roomType"
        class="toggle"
        :active="roomType.is_active"
        :name="roomType.name_en"
        kind="room type"
        :count="() => countActiveRooms(api, { category_id: roomType!.id })"
        :turn="turn"
        :blocked="dirty ? 'Save or cancel your changes first.' : undefined"
      />
      <BaseButton variant="quiet" @click="close">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="room-type-form" :busy="saving" :disabled="!!roomType && !dirty">
        {{ saving ? (roomType ? 'Saving' : 'Creating') : roomType ? 'Save changes' : 'Create room type' }}
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
/* The Active switch sits apart, at the start of the foot. */
.toggle {
  margin-right: auto;
}
</style>
