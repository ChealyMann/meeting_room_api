<script setup lang="ts">
// A user's details (DSH-U02, U03): name, contact, work and — when creating — the first password.
// It edits the form object it is given; the panel around it saves.
import { Copy, KeyRound } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import type { DepartmentOut, DivisionOut, PositionOut } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import BaseField from '../../components/base/BaseField.vue'
import BaseSwitch from '../../components/base/BaseSwitch.vue'
import PasswordInput from '../../components/base/PasswordInput.vue'
import SearchPicker, { type PickerItem } from '../../components/list/SearchPicker.vue'
import { useToast } from '../../composables/useToast'
import { generatePassword } from '../../utils/password'
import { FIELD_WORDS } from '../../utils/pickerWords'
import { TITLES, type UserForm } from '../../utils/userForms'

const props = defineProps<{
  form: UserForm
  errors: Record<string, string>
  creating: boolean
  divisions: DivisionOut[]
  departments: DepartmentOut[]
  positions: PositionOut[]
}>()

const toast = useToast()
// A generated password shows as text, so the Admin sees what they hand over.
const shown = ref(false)
const count = (text: string) => [...text].length

const titleItems: PickerItem[] = TITLES.map((t) => ({ value: t, label: t }))

// G08: only active ones, plus the chosen one marked "(off)". Divisions sit under their department.
const label = (item: { name_en: string; is_active: boolean }) => (item.is_active ? item.name_en : `${item.name_en} (off)`)
const divisionItems = computed<PickerItem[]>(() => {
  const departmentName = (id: number) => props.departments.find((d) => d.id === id)?.name_en ?? 'Other'
  return props.divisions
    .filter((d) => d.is_active || d.id === props.form.division_id)
    .map((d) => ({ value: d.id, label: label(d), keywords: `${d.name_kh} ${d.short_name ?? ''}`, group: departmentName(d.department_id) }))
    .sort((a, b) => a.group.localeCompare(b.group))
})
const positionItems = computed<PickerItem[]>(() =>
  props.positions
    .filter((p) => p.is_active || p.id === props.form.position_id)
    .map((p) => ({ value: p.id, label: label(p), keywords: p.name_kh })),
)

function generate() {
  // eslint-disable-next-line vue/no-mutating-props -- the form object is this component's to edit
  props.form.temporary_password = generatePassword()
  shown.value = true
}
async function copy() {
  try {
    await navigator.clipboard.writeText(props.form.temporary_password)
    toast.show('Password copied')
  } catch {
    toast.show('Copy did not work', 'Select the password and copy it by hand.')
  }
}
</script>

<!-- eslint-disable vue/no-mutating-props -- the form object is this component's to edit -->
<template>
  <section class="group" aria-labelledby="g-name">
    <h3 id="g-name">Name</h3>
    <div class="row-title">
      <BaseField id="title" label="Title" :error="errors.title">
        <template #default="{ describedBy, invalid }">
          <SearchPicker
            id="title"
            mode="field"
            nullable
            :items="titleItems"
            :words="FIELD_WORDS.title"
            :model-value="form.title"
            :invalid="invalid"
            :described-by="describedBy"
            @update:model-value="form.title = $event as string | null"
          />
        </template>
      </BaseField>
      <BaseField id="staff_id" label="Staff ID" :hint="`${count(form.staff_id)}/20`" :error="errors.staff_id">
        <template #default="{ describedBy, invalid }">
          <input id="staff_id" v-model="form.staff_id" class="input mono" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
        </template>
      </BaseField>
    </div>
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

  <section class="group" aria-labelledby="g-contact">
    <h3 id="g-contact">Contact</h3>
    <BaseField id="email" label="Email" hint="Used to sign in" :error="errors.email">
      <template #default="{ describedBy, invalid }">
        <input id="email" v-model="form.email" class="input" type="email" autocomplete="off" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
      </template>
    </BaseField>
    <BaseField id="secondary_email" label="Second email" hint="optional" :error="errors.secondary_email">
      <template #default="{ describedBy, invalid }">
        <input id="secondary_email" v-model="form.secondary_email" class="input" type="email" autocomplete="off" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
      </template>
    </BaseField>
    <BaseField id="phone" label="Phone" :hint="`${count(form.phone)}/20 · optional`" :error="errors.phone">
      <template #default="{ describedBy, invalid }">
        <input id="phone" v-model="form.phone" class="input mono" inputmode="tel" :aria-describedby="describedBy" :aria-invalid="invalid || undefined" />
      </template>
    </BaseField>
    <div class="switch-row">
      <div>
        <label for="email_notifications">Email notifications</label>
        <p>Booking news by email.</p>
      </div>
      <BaseSwitch id="email_notifications" v-model="form.email_notifications" />
    </div>
  </section>

  <section class="group" aria-labelledby="g-work">
    <h3 id="g-work">Work</h3>
    <BaseField id="division_id" label="Division" hint="Pitika, IT Lead and IT Staff need one" :error="errors.division_id">
      <template #default="{ describedBy, invalid }">
        <SearchPicker
          id="division_id"
          mode="field"
          nullable
          :items="divisionItems"
          :words="FIELD_WORDS.division"
          :model-value="form.division_id"
          :invalid="invalid"
          :described-by="describedBy"
          @update:model-value="form.division_id = $event as number | null"
        />
      </template>
    </BaseField>
    <BaseField id="position_id" label="Position" :error="errors.position_id">
      <template #default="{ describedBy, invalid }">
        <SearchPicker
          id="position_id"
          mode="field"
          :items="positionItems"
          :words="FIELD_WORDS.position"
          :model-value="form.position_id"
          :invalid="invalid"
          :described-by="describedBy"
          @update:model-value="form.position_id = $event as number | null"
        />
      </template>
    </BaseField>
  </section>

  <section v-if="creating" class="group" aria-labelledby="g-password">
    <h3 id="g-password">First password</h3>
    <BaseField id="temporary_password" label="Temporary password" hint="They must change it when they first sign in." :error="errors.temporary_password">
      <template #default="{ describedBy, invalid }">
        <PasswordInput id="temporary_password" v-model="form.temporary_password" v-model:visible="shown" autocomplete="new-password" :described-by="describedBy" :invalid="invalid" />
      </template>
    </BaseField>
    <div class="password-tools">
      <BaseButton variant="quiet" @click="generate">
        <KeyRound aria-hidden="true" />
        Generate
      </BaseButton>
      <BaseButton variant="quiet" :disabled="!form.temporary_password" @click="copy">
        <Copy aria-hidden="true" />
        Copy
      </BaseButton>
    </div>
  </section>
</template>

<style scoped>
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
.row-title {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  align-items: start;
  gap: 12px;
}
.switch-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.switch-row label {
  font-size: 12.5px;
  font-weight: 500;
}
.switch-row p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
.password-tools {
  display: flex;
  gap: 8px;
}
@media (max-width: 760px) {
  .row-title {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
