<script setup lang="ts">
// Request slip (Admin, Setup): who signs the slip as Director of Cabinet, and the address line
// printed at its foot. The heads of departments and offices are set on their own forms.
import { CircleAlert } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { getSlipSettings, saveSlipSettings, type SlipSettings } from '../api/slipSettings'
import BaseButton from '../components/base/BaseButton.vue'
import BaseField from '../components/base/BaseField.vue'
import { useFieldErrors } from '../composables/useFieldErrors'
import { useToast } from '../composables/useToast'
import { FIELD_WORDS } from '../utils/pickerWords'
import HeadPicker from './organisation/HeadPicker.vue'

const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

const saved = ref<SlipSettings | null>(null)
const director = ref<number | null>(null)
const address = ref('')
const loadError = ref('')
const saving = ref(false)

function show(settings: SlipSettings) {
  saved.value = settings
  director.value = settings.director?.id ?? null
  address.value = settings.address_kh
}
async function load() {
  loadError.value = ''
  try {
    show(await getSlipSettings(api))
  } catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'The settings could not load.'
  }
}
onMounted(load)

const count = (text: string) => [...text].length

async function save() {
  clear()
  const line = address.value.trim()
  if (!line) errors.value = { address_kh: 'Enter the address line.' }
  else if (count(line) > 500) errors.value = { address_kh: 'Max 500 characters.' }
  if (Object.keys(errors.value).length) return
  saving.value = true
  try {
    show(await saveSlipSettings(api, { director_user_id: director.value, address_kh: line }))
    toast.show('Request slip settings saved')
  } catch (err) {
    apply(err)
    if (Object.keys(errors.value).length) formMessage.value = ''
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="slip-page">
    <div class="head">
      <h1>Request slip</h1>
    </div>
    <p class="lead">
      A confirmed booking gives a request slip (<span class="kh">ប័ណ្ណស្នើ</span>) as a Word file. The heads of departments and offices
      are set on their own pages; this page holds the rest.
    </p>

    <div v-if="loadError" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <div>
        <b>{{ loadError }}</b>
        <BaseButton variant="quiet" @click="load">Try again</BaseButton>
      </div>
    </div>

    <form v-else-if="saved" class="form" novalidate @submit.prevent="save">
      <div v-if="formMessage" class="summary" role="alert">
        <CircleAlert aria-hidden="true" />
        <b>{{ formMessage }}</b>
      </div>

      <BaseField id="director_user_id" label="Director of Cabinet" hint="Signs the director's box" :error="errors.director_user_id">
        <template #default="{ describedBy, invalid }">
          <HeadPicker
            id="director_user_id"
            v-model="director"
            :current="saved.director"
            :words="FIELD_WORDS.director"
            :invalid="invalid"
            :described-by="describedBy"
          />
        </template>
      </BaseField>

      <BaseField id="address_kh" label="Address line" :hint="`${count(address)}/500`" :error="errors.address_kh">
        <template #default="{ describedBy, invalid }">
          <textarea
            id="address_kh"
            v-model="address"
            class="input kh"
            rows="3"
            :aria-describedby="describedBy"
            :aria-invalid="invalid || undefined"
          />
          <p class="help">Printed at the foot of every slip. Check the phone numbers.</p>
        </template>
      </BaseField>

      <div class="actions">
        <BaseButton variant="primary" type="submit" :busy="saving">{{ saving ? 'Saving' : 'Save' }}</BaseButton>
      </div>
    </form>
  </div>
</template>

<style scoped>
.slip-page {
  max-width: 640px;
}
h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.lead {
  margin: 8px 0 20px;
  font-size: 13.5px;
  color: var(--color-intaglio);
}
.form {
  display: grid;
  gap: 16px;
}
.help {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
