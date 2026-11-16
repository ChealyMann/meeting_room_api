<script setup lang="ts">
// Request slip (Admin, Setup): who signs the slip as Director of Cabinet, and the address line
// printed at its foot. The heads of departments and offices are set on their own pages (linked
// here). Clean look (13 Nov 2026): settings rows with the label and help on the left, the field on
// the right, hairlines between; Save is on only when something changed.
import { ChevronRight, CircleAlert } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { getSlipSettings, saveSlipSettings, type SlipSettings } from '../api/slipSettings'
import BaseButton from '../components/base/BaseButton.vue'
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
const changed = computed(() => !!saved.value && (director.value !== (saved.value.director?.id ?? null) || address.value.trim() !== saved.value.address_kh))

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
    <h1>Request slip</h1>
    <p class="lead">Settings for the Word slip (<span class="kh">ប័ណ្ណស្នើ</span>) of a confirmed booking.</p>

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

      <div class="set-row">
        <div class="say">
          <label for="director_user_id">Director of Cabinet</label>
          <p>Signs the director's box.</p>
        </div>
        <div class="field" :class="{ 'has-error': errors.director_user_id }">
          <HeadPicker
            id="director_user_id"
            v-model="director"
            :current="saved.director"
            :words="FIELD_WORDS.director"
            :invalid="!!errors.director_user_id"
            :described-by="errors.director_user_id ? 'director_user_id-error' : undefined"
          />
          <p v-if="errors.director_user_id" id="director_user_id-error" class="error">
            <CircleAlert aria-hidden="true" /><span>{{ errors.director_user_id }}</span>
          </p>
        </div>
      </div>

      <div class="set-row">
        <div class="say">
          <label for="address_kh">Address line</label>
          <p>Printed at the foot of every slip. Check the phone numbers.</p>
        </div>
        <div class="field" :class="{ 'has-error': errors.address_kh }">
          <textarea
            id="address_kh"
            v-model="address"
            class="input kh"
            rows="3"
            :aria-describedby="errors.address_kh ? 'address_kh-error' : 'address_kh-count'"
            :aria-invalid="!!errors.address_kh || undefined"
          />
          <div class="under">
            <p v-if="errors.address_kh" id="address_kh-error" class="error">
              <CircleAlert aria-hidden="true" /><span>{{ errors.address_kh }}</span>
            </p>
            <span id="address_kh-count" class="count" :class="{ over: count(address) > 500 }">{{ count(address) }}/500</span>
          </div>
        </div>
      </div>

      <div class="set-row">
        <div class="say">
          <span class="name">Heads</span>
          <p>Each department and office signs with its own head.</p>
        </div>
        <div class="links">
          <RouterLink :to="{ name: 'departments' }">Departments<ChevronRight :size="16" aria-hidden="true" /></RouterLink>
          <RouterLink :to="{ name: 'offices' }">Offices<ChevronRight :size="16" aria-hidden="true" /></RouterLink>
        </div>
      </div>

      <div class="actions">
        <span class="state" aria-live="polite">{{ changed ? 'Not saved yet' : '' }}</span>
        <BaseButton variant="primary" type="submit" :busy="saving" :disabled="!changed">{{ saving ? 'Saving' : 'Save' }}</BaseButton>
      </div>
    </form>
  </div>
</template>

<style scoped>
.slip-page {
  max-width: 880px;
}
h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.lead {
  margin: 6px 0 20px;
  font-size: 13.5px;
  color: var(--color-intaglio);
}
.form {
  display: grid;
}
.form > .summary {
  margin-bottom: 16px;
}
/* One setting per row: what it is on the left, the field on the right, a hairline between. */
.set-row {
  display: grid;
  grid-template-columns: minmax(0, 260px) minmax(0, 1fr);
  gap: 12px 40px;
  padding: 22px 0;
  border-top: 1px solid var(--color-rule);
}
.say {
  display: grid;
  gap: 4px;
  align-content: start;
}
.say label,
.say .name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-ink);
}
.say p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--color-intaglio);
}
textarea.input {
  height: auto;
  min-height: 84px;
  padding: 10px 12px;
  line-height: 1.7;
  field-sizing: content;
  resize: none;
}
.under {
  display: flex;
  gap: 12px;
}
.count {
  margin-left: auto;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-ink-off);
}
.count.over {
  color: var(--color-crimson);
}
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: start;
}
.links a {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 36px;
  padding: 0 10px 0 14px;
  border-radius: 8px;
  background: var(--color-field-disabled);
  color: var(--color-ink);
  font-size: 13.5px;
  text-decoration: none;
  transition: background-color 140ms ease;
}
.links a:hover {
  background: var(--color-rule);
}
.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  padding-top: 18px;
  border-top: 1px solid var(--color-rule);
}
.state {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
@media (max-width: 720px) {
  .set-row {
    grid-template-columns: minmax(0, 1fr);
    padding: 18px 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .links a {
    transition: none;
  }
}
</style>
