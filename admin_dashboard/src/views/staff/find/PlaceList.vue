<script lang="ts">
export interface PlaceOffice {
  id: number
  en: string
  kh: string
  province: { code: string; name_en: string } | null
}
export interface PlaceBuilding {
  id: number
  office: number
  en: string
  kh: string
}
</script>

<script setup lang="ts">
// Inside the Office chip (look A "One search list", owner pick 20 Nov 2026): a search box, then
// each office as a bold row with its buildings hanging from a tree line under it (English over
// Khmer). The offices in the
// user's province come first. One click picks; a building picks its office too. Typing finds an
// office or a building by its English or Khmer name; a found office keeps all its buildings.
import { Check, Search } from 'lucide-vue-next'
import { computed, ref } from 'vue'

const props = defineProps<{
  offices: PlaceOffice[]
  buildings: PlaceBuilding[]
  office: 'all' | number
  building: 'all' | number
  /** The user's province: its offices come first. */
  mine: { code: string; name_en: string } | null
}>()
const emit = defineEmits<{ pick: [office: 'all' | number, building: 'all' | number] }>()

const query = ref('')
const typed = computed(() => query.value.trim().toLowerCase())
const hit = (...texts: string[]) => !typed.value || texts.some((t) => t.toLowerCase().includes(typed.value))
/** A search box with more than one office, or with a long building list. */
const searchable = computed(() => props.offices.length > 1 || props.buildings.length >= 6)

/** The found offices, the user's province first; no headings over them (owner, 20 Nov 2026). */
const found = computed(() => {
  const list = props.offices
    .map((office) => {
      const own = props.buildings.filter((b) => b.office === office.id)
      const officeHit = hit(office.en, office.kh)
      const buildings = officeHit ? own : own.filter((b) => hit(b.en, b.kh))
      return officeHit || buildings.length ? { office, buildings } : null
    })
    .filter((x) => x !== null)
  const code = props.mine?.code
  if (!code) return list
  return [...list.filter((x) => x.office.province?.code === code), ...list.filter((x) => x.office.province?.code !== code)]
})
const nothing = computed(() => !found.value.length)
const officeOn = (id: number) => props.office === id && props.building === 'all'
</script>

<template>
  <div class="pl">
    <label v-if="searchable" class="pl-search">
      <Search :size="16" aria-hidden="true" />
      <input v-model="query" type="search" placeholder="Search an office or building" aria-label="Search an office or building" />
    </label>
    <div class="pl-list">
      <button
        v-if="!typed"
        type="button"
        class="pl-row"
        data-office="all"
        :class="{ on: office === 'all' && building === 'all' }"
        @click="emit('pick', 'all', 'all')"
      >
        <span class="t"><b>All offices</b></span>
        <Check v-if="office === 'all' && building === 'all'" :size="16" class="ck" aria-hidden="true" />
      </button>
      <template v-for="x in found" :key="x.office.id">
        <button
          type="button"
          class="pl-row office"
          :data-office="x.office.id"
          :class="{ on: officeOn(x.office.id) }"
          @click="emit('pick', x.office.id, 'all')"
        >
          <span class="t"><b>{{ x.office.en }}</b><small v-if="x.office.kh" class="kh">{{ x.office.kh }}</small></span>
          <Check v-if="officeOn(x.office.id)" :size="16" class="ck" aria-hidden="true" />
        </button>
        <div v-if="x.buildings.length" class="pl-tree">
          <button
            v-for="b in x.buildings"
            :key="b.id"
            type="button"
            class="pl-row sub"
            :data-building="b.id"
            :class="{ on: building === b.id }"
            @click="emit('pick', x.office.id, b.id)"
          >
            <span class="t"><b>{{ b.en }}</b><small v-if="b.kh" class="kh">{{ b.kh }}</small></span>
            <Check v-if="building === b.id" :size="16" class="ck" aria-hidden="true" />
          </button>
        </div>
      </template>
      <p v-if="nothing" class="pl-none">No office or building matches "{{ query.trim() }}"</p>
    </div>
  </div>
</template>

<style scoped>
.pl {
  display: grid;
  gap: 10px;
  width: min(340px, 100%);
}
.pl-search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--color-rule-strong);
  border-radius: 10px;
  background: var(--color-sheet);
  color: var(--color-ink-off);
}
.pl-search:focus-within {
  border-color: var(--color-crimson);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.12);
}
.pl-search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: none;
  color: var(--color-ink);
  font: inherit;
  font-size: 13.5px;
}
.pl-list {
  display: grid;
  max-height: min(380px, 55vh);
  margin: 0 -6px;
  padding: 0 6px;
  overflow: auto;
}
.pl-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 7px 8px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--color-ink);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
/* Tree lines (owner pick, 20 Nov 2026): one line runs down from the office, with a short branch
   to each building; the line stops at the last building. */
.pl-tree {
  position: relative;
  margin: 0 0 4px 17px;
  padding-left: 14px;
  border-left: 1.5px solid var(--color-rule-strong);
}
.pl-tree .pl-row {
  position: relative;
}
.pl-tree .pl-row::before {
  content: '';
  position: absolute;
  top: 50%;
  left: -14px;
  width: 10px;
  border-top: 1.5px solid var(--color-rule-strong);
}
.pl-tree .pl-row:last-child::after {
  content: '';
  position: absolute;
  top: calc(50% + 1px);
  bottom: -6px;
  left: -15.5px;
  width: 3px;
  background: var(--color-sheet);
}
.pl-tree .pl-row.on::before {
  border-color: var(--color-crimson);
}
.pl-row .t {
  display: grid;
  flex: 1;
  min-width: 0;
}
.pl-row b {
  overflow: hidden;
  font-size: 13.5px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pl-row.office b {
  font-weight: 600;
}
.pl-row small {
  overflow: hidden;
  color: var(--color-intaglio);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kh {
  font-family: var(--font-kh);
}
.pl-row.on {
  background: var(--color-crimson-wash);
}
.pl-row.on b,
.ck {
  color: var(--color-crimson);
}
.ck {
  flex: none;
}
.pl-none {
  margin: 0;
  padding: 18px 8px;
  color: var(--color-ink-off);
  font-size: 13px;
  text-align: center;
}
@media (hover: hover) and (pointer: fine) {
  .pl-row:not(.on):hover {
    background: var(--color-field-disabled);
  }
}
</style>
