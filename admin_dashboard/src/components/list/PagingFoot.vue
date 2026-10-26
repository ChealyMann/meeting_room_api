<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed } from 'vue'

import { PAGE_SIZES } from '../../composables/useListQuery'

const props = defineProps<{ page: number; size: number; total: number }>()
const emit = defineEmits<{ 'update:page': [page: number]; 'update:size': [size: number] }>()

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))

const range = computed(() => {
  if (!props.total) return '0 of 0'
  const from = (props.page - 1) * props.size + 1
  const to = Math.min(props.total, props.page * props.size)
  return `${from}–${to} of ${props.total}`
})

/** First, last, and the pages next to the current one; `…` for a gap of more than one page. */
const items = computed<Array<number | '…'>>(() => {
  const keep = [1, pages.value, props.page - 1, props.page, props.page + 1].filter(
    (n) => n >= 1 && n <= pages.value,
  )
  const sorted = [...new Set(keep)].sort((a, b) => a - b)
  const out: Array<number | '…'> = []
  sorted.forEach((n, i) => {
    const before = sorted[i - 1]
    if (before !== undefined && n - before === 2) out.push(before + 1)
    else if (before !== undefined && n - before > 2) out.push('…')
    out.push(n)
  })
  return out
})

function go(page: number) {
  if (page >= 1 && page <= pages.value && page !== props.page) emit('update:page', page)
}

function onSize(event: Event) {
  emit('update:size', Number((event.target as HTMLSelectElement).value))
}
</script>

<template>
  <div class="foot">
    <span class="mono range">{{ range }}</span>
    <label class="rows">
      Rows
      <select class="input" :value="size" @change="onSize">
        <option v-for="option in PAGE_SIZES" :key="option" :value="option">{{ option }}</option>
      </select>
    </label>
    <nav class="pager" aria-label="Pages">
      <button type="button" aria-label="Previous page" :disabled="page <= 1" @click="go(page - 1)">
        <ChevronLeft aria-hidden="true" />
      </button>
      <template v-for="(item, i) in items" :key="i">
        <span v-if="item === '…'" class="gap" aria-hidden="true">…</span>
        <button
          v-else
          type="button"
          :aria-current="item === page ? 'page' : undefined"
          @click="go(item)"
        >
          {{ item }}
        </button>
      </template>
      <button
        type="button"
        aria-label="Next page"
        :disabled="page >= pages || !total"
        @click="go(page + 1)"
      >
        <ChevronRight aria-hidden="true" />
      </button>
    </nav>
  </div>
</template>

<style scoped>
.foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  padding: 12px 0 4px;
  border-top: 1px solid var(--color-rule-strong);
  font-size: 13px;
  color: var(--color-intaglio);
}
.range {
  font-size: 12px;
}
.rows {
  display: flex;
  align-items: center;
  gap: 8px;
}
.rows .input {
  width: auto;
  height: 32px;
}
.pager {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}
.pager button,
.gap {
  display: inline-grid;
  place-items: center;
  min-width: 32px;
  height: 32px;
}
.pager button {
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--color-ink);
  font-family: var(--font-mono);
  font-size: 12px;
  cursor: pointer;
}
.pager button:hover {
  border-color: var(--color-rule-strong);
}
.pager button[aria-current='page'] {
  border-color: var(--color-crimson);
  background: var(--color-sheet);
  color: var(--color-crimson);
}
.pager button[disabled] {
  border-color: transparent;
  color: var(--color-ink-disabled);
  cursor: not-allowed;
}
.gap {
  font-family: var(--font-mono);
  font-size: 12px;
}
</style>
