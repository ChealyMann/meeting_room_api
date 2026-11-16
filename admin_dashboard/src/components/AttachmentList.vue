<script setup lang="ts">
// The files on a booking (spec: booking attachments, 16 Nov 2026): a name to click (download)
// and its size. Editable (the booker, until the booking is confirmed): Add file and a remove
// button per row. It only reports what was asked; the parent does the network work.
import { FileSpreadsheet, FileText, Paperclip, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import { ACCEPT, MAX_FILES, fileProblem, isSheet, sizeText } from '../utils/attachments'

export interface AttachmentItem {
  name: string
  size: number
  id?: number
  url?: string
}

const props = defineProps<{ files: AttachmentItem[]; editable?: boolean; busy?: boolean }>()
const emit = defineEmits<{ add: [file: File]; remove: [index: number]; open: [index: number] }>()

const input = ref<HTMLInputElement | null>(null)
const problem = ref('')
const full = computed(() => props.files.length >= MAX_FILES)

function chosen(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = '' // the same file can be picked again after a remove
  if (!file) return
  problem.value = fileProblem(file, props.files.length) ?? ''
  if (!problem.value) emit('add', file)
}
</script>

<template>
  <div v-if="files.length || editable" class="att">
    <ul v-if="files.length" class="att-list">
      <li v-for="(f, i) in files" :key="f.id ?? `${f.name}-${i}`" class="att-row">
        <component :is="isSheet(f.name) ? FileSpreadsheet : FileText" :size="16" class="att-icon" aria-hidden="true" />
        <button type="button" class="att-name" :title="`Download ${f.name}`" @click="emit('open', i)">{{ f.name }}</button>
        <span class="att-size">{{ sizeText(f.size) }}</span>
        <button v-if="editable" type="button" class="att-remove" :aria-label="`Remove ${f.name}`" :disabled="busy" @click="emit('remove', i)">
          <X :size="14" aria-hidden="true" />
        </button>
      </li>
    </ul>
    <template v-if="editable">
      <p v-if="full" class="att-note">Up to {{ MAX_FILES }} files.</p>
      <button v-else type="button" class="att-add" :disabled="busy" @click="input?.click()">
        <Paperclip :size="14" aria-hidden="true" />{{ busy ? 'Uploading…' : 'Add file' }}
      </button>
      <input ref="input" type="file" class="att-input" :accept="ACCEPT" tabindex="-1" aria-hidden="true" @change="chosen" />
      <p v-if="problem" class="att-problem" role="alert">{{ problem }}</p>
      <p v-else-if="!files.length" class="att-note">PDF, Word or Excel, up to {{ MAX_FILES }} files, 10 MB each.</p>
    </template>
  </div>
</template>

<style scoped>
.att {
  display: grid;
  gap: 8px;
}
.att-list {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
}
.att-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 8px 0 12px;
}
.att-row + .att-row {
  border-top: 1px solid var(--color-rule);
}
.att-icon {
  flex: none;
  color: var(--color-intaglio);
}
.att-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-ink);
  font: inherit;
  font-size: 13.5px;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.att-name:hover {
  text-decoration: underline;
}
.att-size {
  flex: none;
  color: var(--color-ink-off);
  font-size: 12px;
}
.att-remove {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--color-ink-off);
  cursor: pointer;
}
.att-remove:hover:not(:disabled) {
  background: var(--color-row-hover);
  color: var(--color-crimson);
}
.att-add {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border: 1px dashed var(--color-rule-strong);
  border-radius: 10px;
  background: var(--color-sheet);
  color: var(--color-ink);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.att-add:disabled,
.att-remove:disabled {
  cursor: default;
  opacity: 0.55;
}
.att-input {
  display: none;
}
.att-note,
.att-problem {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-ink-off);
}
.att-problem {
  color: var(--color-crimson);
}
</style>
