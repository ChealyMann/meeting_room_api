<script setup lang="ts">
// The files on a booking as chips (owner pick, 16 Nov 2026: "simple"): a small rounded tag per
// file, the name cut with … and the size on hover; a click downloads. Editable (the booker, until
// the booking is confirmed): an × on each chip and an Add file chip. It only reports what was
// asked; the parent does the network work.
import { FileSpreadsheet, FileText, Plus, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import { ACCEPT, MAX_FILES, MAX_MB, fileProblem, isSheet, sizeText } from '../utils/attachments'

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
    <div class="att-chips">
      <span v-for="(f, i) in files" :key="f.id ?? `${f.name}-${i}`" class="att-chip">
        <component :is="isSheet(f.name) ? FileSpreadsheet : FileText" :size="14" class="att-icon" aria-hidden="true" />
        <button type="button" class="att-name" :title="`${f.name} · ${sizeText(f.size)}`" @click="emit('open', i)">{{ f.name }}</button>
        <button v-if="editable" type="button" class="att-remove" :aria-label="`Remove ${f.name}`" :disabled="busy" @click="emit('remove', i)">
          <X :size="12" aria-hidden="true" />
        </button>
      </span>
      <button v-if="editable && !full" type="button" class="att-chip att-add" :disabled="busy" @click="input?.click()">
        <Plus :size="14" aria-hidden="true" />{{ busy ? 'Uploading…' : 'Add file' }}
      </button>
    </div>
    <template v-if="editable">
      <input ref="input" type="file" class="att-input" :accept="ACCEPT" tabindex="-1" aria-hidden="true" @change="chosen" />
      <p v-if="problem" class="att-problem" role="alert">{{ problem }}</p>
      <p v-else-if="full" class="att-note">Up to {{ MAX_FILES }} files.</p>
      <p v-else class="att-note">PDF, Word or Excel · up to {{ MAX_FILES }} · {{ MAX_MB }} MB each</p>
    </template>
  </div>
</template>

<style scoped>
.att {
  display: grid;
  gap: 6px;
}
.att-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.att-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
  height: 30px;
  padding: 0 6px 0 10px;
  border: 1px solid var(--color-rule);
  border-radius: 999px;
  background: var(--color-field-disabled);
}
.att-icon {
  flex: none;
  color: var(--color-intaglio);
}
.att-name {
  min-width: 0;
  max-width: 220px;
  overflow: hidden;
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-ink);
  font: inherit;
  font-size: 13px;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.att-chip:not(:has(.att-remove)) {
  padding-right: 12px;
}
.att-name:hover {
  text-decoration: underline;
}
.att-remove {
  display: inline-grid;
  flex: none;
  place-items: center;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 999px;
  background: none;
  color: var(--color-ink-off);
  cursor: pointer;
}
.att-remove:hover:not(:disabled) {
  background: var(--color-sheet);
  color: var(--color-crimson);
}
.att-add {
  padding-right: 12px;
  border-style: dashed;
  border-color: var(--color-rule-strong);
  background: var(--color-sheet);
  color: var(--color-ink);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.att-add:hover:not(:disabled) {
  border-color: var(--color-ink-off);
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
  font-size: 12px;
  color: var(--color-ink-off);
}
.att-problem {
  color: var(--color-crimson);
}
</style>
