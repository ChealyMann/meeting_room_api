<script setup lang="ts">
// A user's roles (DSH-U04): six boxes in seed order. Pitika, IT Lead and IT Staff need a division,
// and the signed-in Admin cannot drop their own Admin role. The API's 409s show at the top.
import { CircleAlert } from 'lucide-vue-next'
import { computed, ref, useId, watch } from 'vue'

import { api } from '../../api'
import { ApiError } from '../../api/errors'
import type { RoleOut, UserChanged, UserDetail } from '../../api/types'
import { setUserRoles } from '../../api/users'
import BaseButton from '../../components/base/BaseButton.vue'
import { useToast } from '../../composables/useToast'

const props = defineProps<{ user: UserDetail; roles: RoleOut[]; self: boolean }>()
const emit = defineEmits<{ saved: [user: UserChanged] }>()

const ORDER = ['ADMIN', 'ROOM_OWNER', 'STAFF', 'PITIKA', 'IT_LEAD', 'IT_STAFF']
const NEED_DIVISION = new Set(['PITIKA', 'IT_LEAD', 'IT_STAFF'])

const toast = useToast()
const ownId = useId()
const warningId = useId()

const codesOf = (user: UserDetail) => new Set(user.roles.map((r) => r.code))
const checked = ref(codesOf(props.user))
// Other saves in the panel (details, the Active switch) answer with a new user object: keep the
// Admin's unsaved ticks unless the saved roles themselves changed.
watch(
  () => ORDER.filter((code) => codesOf(props.user).has(code)).join(','),
  () => (checked.value = codesOf(props.user)),
)
const saving = ref(false)
const error = ref('')

const ordered = computed(() =>
  [...props.roles].sort((a, b) => ORDER.indexOf(a.code) - ORDER.indexOf(b.code)),
)
const picked = computed(() => ORDER.filter((code) => checked.value.has(code)))
const dirty = computed(() => picked.value.join(',') !== ORDER.filter((code) => codesOf(props.user).has(code)).join(','))
const needsDivision = computed(() => !props.user.division && picked.value.some((code) => NEED_DIVISION.has(code)))
const ownAdmin = (code: string) => props.self && code === 'ADMIN' && codesOf(props.user).has('ADMIN')

function toggle(code: string, on: boolean) {
  const next = new Set(checked.value)
  if (on) next.add(code)
  else next.delete(code)
  checked.value = next
}

async function save() {
  error.value = ''
  saving.value = true
  try {
    const user = await setUserRoles(api, props.user.id, picked.value)
    toast.show('Roles saved', `${user.name_en} · ${user.roles.length ? user.roles.map((r) => r.name_en).join(', ') : 'no roles'}`)
    emit('saved', user)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'Something went wrong.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="roles">
    <div v-if="error" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <b>{{ error }}</b>
    </div>
    <fieldset :aria-describedby="needsDivision ? warningId : undefined">
      <legend class="sr-only">Roles</legend>
      <div v-for="role in ordered" :key="role.code" class="role">
        <label class="check">
          <input
            type="checkbox"
            :checked="checked.has(role.code)"
            :disabled="ownAdmin(role.code)"
            :aria-describedby="ownAdmin(role.code) ? ownId : undefined"
            @change="toggle(role.code, ($event.target as HTMLInputElement).checked)"
          />
          <span class="names">
            <span>{{ role.name_en }}</span>
            <span class="kh">{{ role.name_kh }}</span>
          </span>
        </label>
        <p v-if="NEED_DIVISION.has(role.code)" class="note">Needs a division</p>
        <p v-if="ownAdmin(role.code)" :id="ownId" class="note">You cannot remove your own Admin role.</p>
      </div>
    </fieldset>
    <p v-if="needsDivision" :id="warningId" class="warning" role="status">
      <CircleAlert aria-hidden="true" />
      Pitika, IT Lead and IT Staff need a division. Choose one on the Details tab first.
    </p>
    <div class="foot">
      <BaseButton variant="primary" :busy="saving" :disabled="!dirty || needsDivision" @click="save">
        {{ saving ? 'Saving' : 'Save roles' }}
      </BaseButton>
    </div>
  </div>
</template>

<style scoped>
.roles {
  display: grid;
  gap: 12px;
}
fieldset {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 0;
  border: 0;
}
.role {
  padding: 8px 0;
  border-bottom: 1px solid var(--color-rule);
}
.check {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13.5px;
}
.check input {
  margin-top: 3px;
  accent-color: var(--color-crimson-fill);
}
.names {
  display: grid;
}
.names .kh {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.note {
  margin: 2px 0 0 23px;
  font-size: 12px;
  color: var(--color-intaglio);
}
.warning {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0;
  font-size: 13px;
  color: var(--color-crimson);
}
.warning svg {
  flex: none;
  width: 16px;
  height: 16px;
  margin-top: 1px;
}
.foot {
  display: flex;
  justify-content: flex-end;
}
</style>
