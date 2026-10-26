<script setup lang="ts">
import { CircleAlert, KeyRound } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { getMe, updateMe } from '../api/me'
import type { MeUpdate, UserDetail } from '../api/types'
import BaseButton from '../components/base/BaseButton.vue'
import BaseField from '../components/base/BaseField.vue'
import BaseSwitch from '../components/base/BaseSwitch.vue'
import FormErrorSummary from '../components/base/FormErrorSummary.vue'
import AvatarField from '../components/AvatarField.vue'
import SignatureField from '../components/SignatureField.vue'
import { useFieldErrors } from '../composables/useFieldErrors'
import { useToast } from '../composables/useToast'
import { useDraftsStore } from '../stores/drafts'
import { useSessionStore } from '../stores/session'
import { formatPhnomPenh } from '../utils/time'

interface ProfileForm {
  secondary_email: string
  phone: string
  email_notifications: boolean
}

/** One draft per user, so an unsaved edit never shows up in someone else's profile. */
const draftKey = (user: UserDetail) => `profile:${user.id}`
const LABELS: Record<string, string> = {
  secondary_email: 'Second email',
  phone: 'Phone',
  email_notifications: 'Email notifications',
}

const session = useSessionStore()
const drafts = useDraftsStore()
const toast = useToast()
const { errors, formMessage, apply, clear } = useFieldErrors()

const profile = ref<UserDetail | null>(null)
const form = ref<ProfileForm | null>(null)
const loadError = ref('')
const saving = ref(false)

function formOf(user: UserDetail): ProfileForm {
  return {
    secondary_email: user.secondary_email ?? '',
    phone: user.phone ?? '',
    email_notifications: user.email_notifications,
  }
}

/** Only what changed; empty text clears the field (null). */
function changesOf(values: ProfileForm, user: UserDetail): MeUpdate {
  const changes: MeUpdate = {}
  for (const key of ['secondary_email', 'phone'] as const) {
    const value = values[key].trim() || null
    if (value !== user[key]) changes[key] = value
  }
  if (values.email_notifications !== user.email_notifications) {
    changes.email_notifications = values.email_notifications
  }
  return changes
}

const changes = computed(() =>
  form.value && profile.value ? changesOf(form.value, profile.value) : {},
)
const dirty = computed(() => Object.keys(changes.value).length > 0)

/** Rows that name a record: English over Khmer, always both. */
const namedRows = computed(() => {
  const user = profile.value
  if (!user) return []
  const roles = user.roles.length
    ? {
        name_en: user.roles.map((role) => role.name_en).join(', '),
        name_kh: user.roles.map((role) => role.name_kh).join(', '),
      }
    : null
  return [
    { label: 'Position', name: user.position },
    { label: 'Division', name: user.division },
    { label: 'Department', name: user.department },
    { label: 'Province', name: user.province },
    { label: 'Roles', name: roles },
  ]
})
const summary = computed(() =>
  Object.keys(errors.value)
    .filter((key) => key in LABELS)
    .map((key) => ({ id: key, label: LABELS[key] ?? key })),
)

watch(
  form,
  () => {
    if (!form.value || !profile.value) return
    if (dirty.value) drafts.set(draftKey(profile.value), form.value)
    else drafts.clear(draftKey(profile.value))
  },
  { deep: true },
)

function show(user: UserDetail) {
  profile.value = user
  session.user = user
}

async function load() {
  loadError.value = ''
  try {
    const user = await getMe(api)
    show(user)
    const draft = drafts.get<ProfileForm>(draftKey(user))
    form.value = draft ? { ...draft } : formOf(user)
  } catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  }
}

async function save() {
  if (!profile.value || !form.value || !dirty.value) return
  clear()
  saving.value = true
  try {
    const user = await updateMe(api, changes.value)
    show(user)
    form.value = formOf(user)
    drafts.clear(draftKey(user))
    toast.show('Profile saved', user.staff_id)
  } catch (err) {
    apply(err)
    if (summary.value.length) formMessage.value = ''
  } finally {
    saving.value = false
  }
}

function undo() {
  if (!profile.value) return
  clear()
  form.value = formOf(profile.value)
}

function onSignature(signatureUrl: string | null) {
  if (profile.value) show({ ...profile.value, signature_url: signatureUrl })
}

function onAvatarRemoved() {
  if (profile.value) show({ ...profile.value, avatar_url: null })
}

onMounted(load)
</script>

<template>
  <div class="head">
    <h1>My profile</h1>
    <span v-if="profile" class="mono serial">{{ profile.staff_id }}</span>
  </div>

  <div v-if="loadError" class="summary load-error" role="alert">
    <CircleAlert aria-hidden="true" />
    <div>
      <b>{{ loadError }}</b>
      <BaseButton variant="quiet" @click="load">Try again</BaseButton>
    </div>
  </div>

  <div v-else-if="!profile || !form" data-skeleton class="layout">
    <p class="sr-only" role="status">Loading your profile</p>
    <section v-for="n in 2" :key="n" class="block" aria-hidden="true">
      <div class="skeleton-bar" style="width: 30%" />
      <div v-for="row in 5" :key="row" class="skeleton-row">
        <div class="skeleton-bar" style="width: 28%" />
        <div class="skeleton-bar" :style="{ width: `${40 + ((row * 13) % 35)}%` }" />
      </div>
    </section>
  </div>

  <div v-else class="layout">
    <section class="block" aria-labelledby="details-title">
      <h2 id="details-title">Details</h2>
      <dl class="details">
        <div>
          <dt>Name</dt>
          <dd>
            <span class="name-en">{{ profile.name_en }}</span>
            <span class="kh name-kh">{{ profile.name_kh }}</span>
          </dd>
        </div>
        <div>
          <dt>Staff ID</dt>
          <dd class="mono">{{ profile.staff_id }}</dd>
        </div>
        <div>
          <dt>Email</dt>
          <dd class="wrap">{{ profile.email }}</dd>
        </div>
        <div v-for="row in namedRows" :key="row.label">
          <dt>{{ row.label }}</dt>
          <dd v-if="row.name">
            <span class="name-en">{{ row.name.name_en }}</span>
            <span class="kh name-kh">{{ row.name.name_kh }}</span>
          </dd>
          <dd v-else class="off">None</dd>
        </div>
        <div>
          <dt>Last sign-in</dt>
          <dd class="mono" :class="{ off: !profile.last_login_at }">
            {{ profile.last_login_at ? formatPhnomPenh(profile.last_login_at) : 'Never' }}
          </dd>
        </div>
      </dl>
      <RouterLink :to="{ name: 'change-password' }" class="btn change-password">
        <KeyRound aria-hidden="true" />
        Change password
      </RouterLink>
    </section>

    <div class="side">
      <section class="block" aria-labelledby="contact-title">
        <h2 id="contact-title">Contact</h2>
        <form class="form" novalidate @submit.prevent="save">
          <FormErrorSummary :errors="summary" />
          <div v-if="formMessage" class="summary" role="alert">
            <CircleAlert aria-hidden="true" />
            <b>{{ formMessage }}</b>
          </div>

          <div class="row2">
            <BaseField id="secondary_email" label="Second email" hint="optional" :error="errors.secondary_email">
              <template #default="{ describedBy, invalid }">
                <input
                  id="secondary_email"
                  v-model="form.secondary_email"
                  class="input"
                  type="email"
                  inputmode="email"
                  autocomplete="email"
                  spellcheck="false"
                  :aria-describedby="describedBy"
                  :aria-invalid="invalid || undefined"
                />
              </template>
            </BaseField>
            <BaseField id="phone" label="Phone" hint="optional" :error="errors.phone">
              <template #default="{ describedBy, invalid }">
                <input
                  id="phone"
                  v-model="form.phone"
                  class="input mono"
                  type="tel"
                  autocomplete="tel"
                  :aria-describedby="describedBy"
                  :aria-invalid="invalid || undefined"
                />
              </template>
            </BaseField>
          </div>

          <div class="switch-row">
            <div>
              <label for="email_notifications">Email notifications</label>
              <p>Booking updates are also sent to your email.</p>
            </div>
            <BaseSwitch id="email_notifications" v-model="form.email_notifications" />
          </div>

          <div class="foot">
            <BaseButton v-if="dirty" variant="quiet" @click="undo">Undo changes</BaseButton>
            <BaseButton variant="primary" type="submit" :busy="saving" :disabled="!dirty">
              {{ saving ? 'Saving' : 'Save changes' }}
            </BaseButton>
          </div>
        </form>
      </section>

      <section class="block" aria-labelledby="photo-title">
        <h2 id="photo-title">Photo</h2>
        <AvatarField
          :avatar-url="profile.avatar_url"
          :version="profile.updated_at"
          @uploaded="show"
          @removed="onAvatarRemoved"
        />
      </section>

      <section class="block" aria-labelledby="signature-title">
        <h2 id="signature-title">Signature</h2>
        <SignatureField :signature-url="profile.signature_url" @change="onSignature" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.serial {
  font-size: 12px;
  color: var(--color-intaglio);
}
.load-error {
  margin-top: 20px;
  align-items: center;
}
.load-error > div {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
  gap: 40px;
  margin-top: 20px;
  max-width: 1120px;
}
.side {
  display: grid;
  gap: 32px;
  align-content: start;
}
.block {
  display: grid;
  gap: 12px;
  align-content: start;
  padding-top: 12px;
  border-top: 1px solid var(--color-rule-strong);
}
h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}

.details {
  margin: 0;
}
.details > div {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px solid var(--color-rule);
}
.details dt {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.details dd {
  margin: 0;
  font-size: 13.5px;
}
.details .wrap {
  overflow-wrap: anywhere;
}
.details .off {
  color: var(--color-ink-off);
}
.name-en {
  display: block;
  font-weight: 500;
}
.name-kh {
  display: block;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--color-intaglio);
}
.change-password {
  justify-self: start;
  margin-top: 8px;
  text-decoration: none;
}

.form {
  display: grid;
  gap: 12px;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.switch-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 0;
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
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--color-rule);
}

.skeleton-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid var(--color-rule);
}

@media (max-width: 1100px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
    gap: 32px;
    max-width: 720px;
  }
}
@media (max-width: 560px) {
  .row2 {
    grid-template-columns: minmax(0, 1fr);
  }
  .details > div {
    grid-template-columns: minmax(0, 1fr);
    gap: 2px;
  }
}
</style>
