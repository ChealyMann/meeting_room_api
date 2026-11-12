<script setup lang="ts">
// One list of step 3 (food, or IT help): a flat header with the count, a search that matches the
// start of words, items under small sticky group headings, a tick circle on what is picked.
import { Check, Search, X } from 'lucide-vue-next'
import { computed, ref, type Component } from 'vue'

import type { ServiceOut } from '../../../api/services'
import { iconFor } from '../../../utils/equipmentIcons'
import { groupServices } from '../rules'

const props = defineProps<{
  kind: 'food' | 'it'
  title: string
  items: ServiceOut[]
  groupOrder: string[]
  groupLabels: Record<string, string>
  picked: number[]
  searchLabel: string
  fallbackIcon: Component
  /** Shown under a picked item, like "× 8 · served at 09:00". */
  pickedLine?: string
}>()
const emit = defineEmits<{ toggle: [number] }>()

const q = ref('')
const groups = computed(() => groupServices(props.items, props.groupOrder, q.value))
const isOn = (id: number) => props.picked.includes(id)
</script>

<template>
  <section class="svc" :data-kind="kind">
    <header class="svc-h">
      <h3>{{ title }}</h3>
      <span :class="{ some: picked.length }">{{ picked.length ? `${picked.length} picked` : 'None' }}</span>
    </header>
    <label class="find">
      <Search :size="15" aria-hidden="true" />
      <input v-model="q" type="search" :placeholder="`Search ${searchLabel}`" :aria-label="`Search ${searchLabel}`" />
      <button v-if="q" type="button" class="x" aria-label="Clear search" @click="q = ''"><X :size="14" aria-hidden="true" /></button>
    </label>
    <div class="svc-scroll">
      <template v-for="g in groups" :key="g.group">
        <h4 class="grp-h">{{ groupLabels[g.group] ?? g.group }}</h4>
        <button
          v-for="item in g.items"
          :key="item.id"
          type="button"
          class="row"
          :class="{ on: isOn(item.id) }"
          :aria-pressed="isOn(item.id)"
          @click="emit('toggle', item.id)"
        >
          <span class="ic"><component :is="iconFor(item.icon) ?? fallbackIcon" :size="17" aria-hidden="true" /></span>
          <span class="txt">
            <span class="name">{{ item.name }}</span>
            <small v-if="isOn(item.id) && pickedLine" class="line">{{ pickedLine }}</small>
            <small v-else-if="item.description">{{ item.description }}</small>
          </span>
          <span class="tick" aria-hidden="true"><Check :size="12" :stroke-width="3" /></span>
        </button>
      </template>
      <p v-if="!groups.length && q" class="none">
        No {{ searchLabel }} matches “{{ q }}”.
        <button type="button" @click="q = ''">Clear search</button>
      </p>
      <p v-else-if="!items.length" class="none">Nothing to pick yet.</p>
    </div>
    <slot />
  </section>
</template>

<style scoped>
.svc {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.svc-h {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}
.svc-h h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.svc-h span {
  color: var(--color-ink-off);
  font-size: 13px;
}
.svc-h span.some {
  color: var(--color-crimson);
  font-weight: 500;
}
.find {
  display: flex;
  flex: none;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 8px 0 14px;
  border-radius: 12px;
  background: var(--color-field-disabled);
  color: var(--color-ink-off);
  transition: background-color 160ms ease, box-shadow 160ms ease;
}
.find:focus-within {
  background: var(--color-sheet);
  box-shadow: 0 0 0 1.5px var(--color-ink);
}
.find input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-ink);
  font: inherit;
  font-size: 14px;
}
.find input::-webkit-search-cancel-button {
  display: none;
}
.x {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--color-ink-off);
  cursor: pointer;
}
.svc-scroll {
  flex: 1;
  min-height: 0;
  margin-top: 6px;
  overflow: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-rule-strong) transparent;
}
.grp-h {
  position: sticky;
  top: 0;
  z-index: 1;
  margin: 0;
  padding: 12px 4px 6px;
  background: var(--color-sheet);
  color: var(--color-ink-off);
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 52px;
  padding: 8px 10px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--color-ink);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color 160ms ease, transform 160ms var(--ease-out-quint);
}
.row:active {
  transform: scale(0.99);
}
.row.on {
  background: var(--color-crimson-wash);
}
.ic {
  display: grid;
  flex: none;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--color-field-disabled);
  color: var(--color-intaglio);
}
.row.on .ic {
  background: var(--color-sheet);
  color: var(--color-crimson);
}
.txt {
  display: grid;
  flex: 1;
  min-width: 0;
}
.name {
  font-size: 14px;
  font-weight: 500;
}
.txt small {
  overflow: hidden;
  color: var(--color-intaglio);
  font-size: 12.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.txt small.line {
  color: var(--color-crimson);
}
.tick {
  display: grid;
  flex: none;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1.5px var(--color-rule-strong);
  color: transparent;
  transition: background-color 160ms ease, box-shadow 160ms ease, color 160ms ease;
}
.row.on .tick {
  background: var(--color-crimson-fill);
  box-shadow: none;
  color: #fff;
}
.none {
  display: grid;
  justify-items: center;
  gap: 8px;
  margin: 0;
  padding: 28px 12px;
  color: var(--color-intaglio);
  font-size: 13.5px;
  text-align: center;
}
.none button {
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-crimson);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}
@media (hover: hover) and (pointer: fine) {
  .row:not(.on):hover {
    background: var(--color-paper);
  }
  .x:hover {
    color: var(--color-ink);
  }
}
@media (prefers-reduced-motion: reduce) {
  .row,
  .tick,
  .find {
    transition: none;
  }
}
</style>
