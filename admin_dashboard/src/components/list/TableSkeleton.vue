<script setup lang="ts">
// Loading rows that match the table's column grid (DESIGN.md "Loading Skeleton").
withDefaults(defineProps<{ columns: string[]; rows?: number }>(), { rows: 8 })
</script>

<template>
  <div class="skeleton" aria-hidden="true">
    <div
      v-for="row in rows"
      :key="row"
      class="skeleton-row"
      :style="{ gridTemplateColumns: columns.join(' ') }"
    >
      <div
        v-for="(column, i) in columns"
        :key="i"
        class="skeleton-bar"
        :class="{ tall: i === 1 }"
        :style="{ width: `${55 + ((row * 17 + i * 23) % 45)}%` }"
      />
    </div>
  </div>
</template>

<style scoped>
.skeleton-row {
  display: grid;
  gap: 16px;
  align-items: center;
  padding: 14px 12px;
  border-bottom: 1px solid var(--color-rule);
}
.skeleton-bar.tall {
  height: 22px;
}
</style>
