<script setup lang="ts">
// A booking's files with the network work around AttachmentList: a click downloads; editable
// (My bookings, while `attachments_open`) uploads and removes, one call at a time. It gives the
// new list back (`update`); a 409 means the booking was confirmed or closed meanwhile (`locked`),
// so the parent reloads it.
import { computed, ref } from 'vue'

import { api } from '../api'
import { getAttachment, removeAttachment, uploadAttachment } from '../api/attachments'
import { ApiError } from '../api/errors'
import type { AttachmentOut } from '../api/types'
import { downloadBlob } from '../utils/download'
import AttachmentList from './AttachmentList.vue'

const props = defineProps<{ bookingId: number; files: AttachmentOut[]; editable?: boolean }>()
const emit = defineEmits<{ update: [files: AttachmentOut[]]; locked: [] }>()

const busy = ref(false)
const problem = ref('')
const items = computed(() => props.files.map((f) => ({ id: f.id, name: f.file_name, size: f.size_bytes, url: f.url })))

async function run(work: () => Promise<void>, fallback: string) {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  try {
    await work()
  } catch (error) {
    problem.value = error instanceof ApiError ? error.message : fallback
    if (error instanceof ApiError && error.status === 409 && error.code !== 'ATTACHMENT_LIMIT_REACHED') emit('locked')
  } finally {
    busy.value = false
  }
}

const open = (index: number) => {
  const file = props.files[index]
  if (file) void run(async () => downloadBlob(await getAttachment(api, file.url), file.file_name), 'The file could not load. Try again.')
}
const add = (file: File) =>
  run(async () => {
    const made = await uploadAttachment(api, props.bookingId, file)
    emit('update', [...props.files, made])
  }, 'The file could not be added. Try again.')
const remove = (index: number) => {
  const file = props.files[index]
  if (!file) return
  void run(async () => {
    await removeAttachment(api, props.bookingId, file.id)
    emit('update', props.files.filter((f) => f.id !== file.id))
  }, 'The file could not be removed. Try again.')
}
</script>

<template>
  <div v-if="files.length || editable" class="booking-files">
    <AttachmentList :files="items" :editable="editable" :busy="busy" @open="open" @add="add" @remove="remove" />
    <p v-if="problem" class="bf-problem" role="alert">{{ problem }}</p>
  </div>
</template>

<style scoped>
.booking-files {
  display: grid;
  gap: 6px;
}
.bf-problem {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-crimson);
}
</style>
