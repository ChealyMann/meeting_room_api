<script setup lang="ts">
// Rename a role in the side panel (DSH-U08). Only the Khmer and English names can change: the
// code and what the role may do are fixed by the API.
import { CircleAlert } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import type { RoleOut, RoleUpdate } from '../../api/types'
import { updateRole } from '../../api/users'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import FormErrorSummary from '../../components/base/FormErrorSummary.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import { useFieldErrors } from '../../composables/useFieldErrors'
import { useToast } from '../../composables/useToast'
import { nameProblems } from '../../utils/formChecks'

const props = defineProps<{ role: RoleOut }>()
const emit = defineEmits<{ saved: [role: RoleOut]; close: [] }>()

const LABELS: Record<string, string> = { name_kh: 'Khmer name', name_en: 'English name' }

const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

const form = ref({ name_kh: props.role.name_kh, name_en: props.role.name_en })
const saving = ref(false)
const panel = ref<InstanceType<typeof SidePanel> | null>(null)

const changes = computed(() => {
  const body: RoleUpdate = {}
  const kh = form.value.name_kh.trim()
  const en = form.value.name_en.trim()
  if (kh !== props.role.name_kh) body.name_kh = kh
  if (en !== props.role.name_en) body.name_en = en
  return body
})
const dirty = computed(() => Object.keys(changes.value).length > 0)

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

async function save() {
  clear()
  const problems: Record<string, string> = {}
  nameProblems(form.value, problems)
  if (Object.keys(problems).length) {
    errors.value = problems
    await focusProblem()
    return
  }
  if (!dirty.value) return
  saving.value = true
  try {
    const role = await updateRole(api, props.role.id, changes.value)
    toast.show(`${role.name_en} saved`, role.code)
    emit('saved', role)
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
  <SidePanel ref="panel" :open="true" :title="role.name_kh" :subtitle="`${role.name_en} · ${role.code}`" @close="emit('close')">
    <form id="role-form" class="form" novalidate @submit.prevent="save">
      <FormErrorSummary :errors="summary" />
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>
      <p class="note">The code and the rules of a role never change.</p>
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
    </form>

    <template #foot>
      <BaseButton variant="quiet" @click="emit('close')">Cancel</BaseButton>
      <BaseButton variant="primary" type="submit" form="role-form" :busy="saving" :disabled="!dirty">
        {{ saving ? 'Saving' : 'Save changes' }}
      </BaseButton>
    </template>
  </SidePanel>
</template>

<style scoped>
.form {
  display: grid;
  gap: 16px;
}
.note {
  margin: 0;
  font-size: 13px;
  color: var(--color-intaglio);
}
</style>
