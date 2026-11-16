<script setup lang="ts">
// One group in a booking pop-up tab (owner pick, 16 Nov 2026, look B): a light card with a small
// heading (and something on its right, like a status pill), then its rows. Every tab is made of
// these, so Details, Food & IT, Files and History all look alike.
defineProps<{ title: string }>()
</script>

<template>
  <section class="panel-section">
    <h3>
      <span>{{ title }}</span>
      <slot name="extra" />
    </h3>
    <slot />
  </section>
</template>

<style scoped>
.panel-section {
  padding: 10px 14px 8px;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
}
.panel-section + .panel-section {
  margin-top: 12px;
}
h3 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 0 0 4px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-ink-off);
}
</style>
