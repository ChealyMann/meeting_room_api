<script setup lang="ts">
// Step 2, Meeting details in soft fields: grey fields with the label inside, an icon on the left;
// the field being typed in turns white with a dark outline. Red only for a real error.
import { FileText, Lock, Mail, Minus, Plus, Type, Users, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import UserAvatar from '../../../components/UserAvatar.vue'
import type { RoomDetail } from '../../../api/types'
import { useSessionStore } from '../../../stores/session'
import { EMAIL, type MeetingErrors } from './meetingErrors'
import type { BookingDraft } from './useBookingDraft'

const props = defineProps<{ room: RoomDetail; errors: MeetingErrors }>()
const draft = defineModel<BookingDraft>('draft', { required: true })
const session = useSessionStore()

const QUICK = [2, 4, 6, 8, 10, 15, 20]
const quick = computed(() => QUICK.filter((n) => n <= props.room.capacity))
const people = computed(() => Number(draft.value.people) || 0)
function bump(by: number) {
  draft.value.people = Math.min(props.room.capacity, Math.max(1, people.value + by))
}

const titleFocus = ref(false)

// Emails: Enter or a comma turns the typed text into a chip; Backspace on empty takes the last back.
const email = ref('')
const emailError = ref('')
function addEmails(text: string): boolean {
  const parts = text
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  const bad = parts.find((p) => !EMAIL.test(p))
  if (bad) {
    emailError.value = 'Write a full email address.'
    email.value = bad
    return false
  }
  for (const p of parts) if (!draft.value.emails.includes(p.toLowerCase())) draft.value.emails.push(p.toLowerCase())
  emailError.value = ''
  email.value = ''
  return true
}
function typed(e: Event) {
  const value = (e.target as HTMLInputElement).value
  email.value = value
  emailError.value = ''
  if (value.includes(',')) addEmails(value)
}
function emailKey(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    if (email.value.trim()) addEmails(email.value)
  } else if (e.key === 'Backspace' && !email.value && draft.value.emails.length) {
    draft.value.emails.pop()
  }
}
function emailBlur() {
  if (email.value.trim()) addEmails(email.value)
}
const removeEmail = (e: string) => (draft.value.emails = draft.value.emails.filter((x) => x !== e))
</script>

<template>
  <div class="ms">
    <div class="sf" :class="{ bad: errors.title }">
      <Type class="ic" :size="17" aria-hidden="true" />
      <input
        id="bf-title"
        v-model="draft.title"
        name="title"
        maxlength="80"
        placeholder=" "
        autocomplete="off"
        :aria-invalid="!!errors.title"
        @focus="titleFocus = true"
        @blur="titleFocus = false"
      />
      <label for="bf-title">Meeting title</label>
      <span v-if="titleFocus || draft.title" class="count mono">{{ draft.title.length }}/80</span>
    </div>
    <p v-if="errors.title" class="err" role="alert">{{ errors.title }}</p>

    <div class="type-row">
      <div class="st-seg" role="radiogroup" aria-label="Meeting type">
        <button type="button" role="radio" :aria-checked="!draft.external" :class="{ on: !draft.external }" @click="draft.external = false">
          Internal
        </button>
        <button type="button" role="radio" :aria-checked="draft.external" :class="{ on: draft.external }" @click="draft.external = true">
          External
        </button>
      </div>
      <label class="gov">
        <button
          type="button"
          role="switch"
          class="sw"
          :aria-checked="draft.governor"
          aria-label="The Governor attends"
          @click="draft.governor = !draft.governor"
        ><i /></button>
        <span>The Governor attends</span>
      </label>
    </div>

    <div class="people">
      <div class="sf num" :class="{ bad: errors.people }">
        <Users class="ic" :size="17" aria-hidden="true" />
        <input id="bf-people" v-model.number="draft.people" name="people" type="number" min="1" :max="room.capacity" placeholder=" " />
        <label for="bf-people">People coming</label>
        <span class="steps">
          <button type="button" aria-label="One less" @click="bump(-1)"><Minus :size="15" aria-hidden="true" /></button>
          <button type="button" aria-label="One more" @click="bump(1)"><Plus :size="15" aria-hidden="true" /></button>
        </span>
      </div>
      <div class="quick" aria-label="Quick people">
        <button v-for="n in quick" :key="n" type="button" :class="{ on: people === n }" @click="draft.people = n">{{ n }}</button>
      </div>
      <span class="hint">Up to {{ room.capacity }}</span>
    </div>
    <p v-if="errors.people" class="err" role="alert">{{ errors.people }}</p>

    <div class="sf mails" :class="{ bad: emailError, filled: draft.emails.length || email }">
      <Mail class="ic" :size="17" aria-hidden="true" />
      <span v-for="e in draft.emails" :key="e" class="chip">
        <b aria-hidden="true">{{ e[0]!.toUpperCase() }}</b>{{ e }}
        <button type="button" :aria-label="`Remove ${e}`" @click="removeEmail(e)"><X :size="12" aria-hidden="true" /></button>
      </span>
      <input
        id="bf-email"
        :value="email"
        name="email"
        type="email"
        placeholder=" "
        autocomplete="off"
        @input="typed"
        @keydown="emailKey"
        @blur="emailBlur"
      />
      <label for="bf-email">Invite by email</label>
    </div>
    <p v-if="emailError" class="err" role="alert">{{ emailError }}</p>

    <template v-if="room.is_private">
      <div class="sf area" :class="{ bad: errors.justification }">
        <Lock class="ic" :size="17" aria-hidden="true" />
        <textarea id="bf-why" v-model="draft.justification" name="justification" rows="3" placeholder=" " />
        <label for="bf-why">Why this private room</label>
      </div>
      <p v-if="errors.justification" class="err" role="alert">{{ errors.justification }}</p>
      <p v-else class="hint below">Only Pitika and the room owner read this.</p>
    </template>

    <div class="sf area">
      <FileText class="ic" :size="17" aria-hidden="true" />
      <textarea id="bf-notes" v-model="draft.notes" name="notes" rows="3" placeholder=" " />
      <label for="bf-notes">Agenda or notes</label>
    </div>

    <div v-if="session.user" class="by">
      <UserAvatar :path="session.user.avatar_url" :name="session.user.name_en" />
      <span><small>Booked by</small>{{ session.user.name_en }}</span>
      <span class="mail">{{ session.user.email }}</span>
    </div>
  </div>
</template>

<style scoped>
.ms {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 640px;
  min-height: 0;
  overflow: auto;
  padding: 4px 2px 8px;
  scrollbar-width: thin;
}
.sf {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: 56px;
  padding: 0 14px 0 44px;
  border-radius: 14px;
  background: var(--color-field-disabled);
  transition: background-color 160ms ease, box-shadow 160ms ease;
}
.sf:focus-within {
  background: var(--color-sheet);
  box-shadow: 0 0 0 1.5px var(--color-ink);
}
.sf.bad {
  box-shadow: 0 0 0 1.5px var(--color-crimson);
}
.ic {
  position: absolute;
  top: 19px;
  left: 15px;
  color: var(--color-ink-off);
}
.sf input,
.sf textarea {
  flex: 1;
  min-width: 120px;
  padding: 24px 0 8px;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--color-ink);
  font: inherit;
  font-size: 15px;
}
.sf textarea {
  padding-top: 26px;
  resize: vertical;
}
.sf label {
  position: absolute;
  top: 18px;
  left: 44px;
  color: var(--color-intaglio);
  font-size: 15px;
  pointer-events: none;
  transform-origin: left top;
  transition: transform 160ms var(--ease-out-quint), color 160ms ease;
}
.sf input:focus + label,
.sf input:not(:placeholder-shown) + label,
.sf textarea:focus + label,
.sf textarea:not(:placeholder-shown) + label,
.sf.filled label {
  color: var(--color-ink-off);
  transform: translateY(-9px) scale(0.78);
}
.count {
  color: var(--color-ink-off);
  font-size: 11.5px;
}
.err {
  margin: -6px 0 0 14px;
  color: var(--color-crimson);
  font-size: 12.5px;
}
.hint {
  color: var(--color-ink-off);
  font-size: 12.5px;
}
.hint.below {
  margin: -6px 0 0 14px;
}
.type-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 20px;
}
.gov {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
}
.sw {
  position: relative;
  width: 38px;
  height: 22px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: var(--color-rule-strong);
  cursor: pointer;
  transition: background-color 160ms ease;
}
.sw i {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  transition: transform 200ms var(--ease-out-quint);
}
.sw[aria-checked='true'] {
  background: var(--color-crimson-fill);
}
.sw[aria-checked='true'] i {
  transform: translateX(16px);
}
.people {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}
.sf.num {
  width: 230px;
  flex-wrap: nowrap;
}
.sf.num input {
  min-width: 0;
  -moz-appearance: textfield;
}
.sf.num input::-webkit-inner-spin-button,
.sf.num input::-webkit-outer-spin-button {
  margin: 0;
  -webkit-appearance: none;
}
.steps {
  display: flex;
  gap: 4px;
  user-select: none;
}
.steps button,
.quick button {
  display: grid;
  place-items: center;
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  border: 0;
  border-radius: 10px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font: inherit;
  font-size: 13.5px;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
.sf:focus-within .steps button {
  background: var(--color-field-disabled);
}
.quick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.quick button {
  background: var(--color-field-disabled);
}
.quick button.on {
  background: var(--color-ink);
  color: var(--color-sheet);
}
.steps button:active,
.quick button:active {
  transform: scale(0.97);
}
.mails {
  padding-top: 26px;
  padding-bottom: 8px;
}
.mails input {
  padding: 0;
  min-height: 24px;
}
.mails label {
  top: 18px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 4px 0 4px;
  border-radius: 999px;
  background: var(--color-sheet);
  font-size: 13px;
}
.chip b {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
  font-size: 11px;
}
.chip button {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--color-ink-off);
  cursor: pointer;
}
.sf.area {
  align-items: flex-start;
}
.by {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  padding-top: 14px;
  border-top: 1px solid var(--color-rule);
  font-size: 14px;
}
.by :deep(.avatar),
.by > :first-child {
  width: 32px;
  height: 32px;
}
.by small {
  display: block;
  color: var(--color-ink-off);
  font-size: 11.5px;
}
.by .mail {
  margin-left: auto;
  color: var(--color-intaglio);
  font-size: 13px;
}
@media (hover: hover) and (pointer: fine) {
  .quick button:not(.on):hover,
  .steps button:hover {
    background: var(--color-rule);
  }
  .chip button:hover {
    color: var(--color-ink);
  }
}
@media (prefers-reduced-motion: reduce) {
  .sf,
  .sf label,
  .sw,
  .sw i {
    transition: none;
  }
}
</style>
