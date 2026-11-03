<script setup lang="ts">
// Pages outside the shell (sign-in, new password, no access): one card in the middle of the
// paper, with the logo on top, and the Bakong temple in faint halftone behind it
// (owner decision, 30 Oct 2026; replaces the two-panel layout).
import TempleHalftone from '../components/TempleHalftone.vue'

defineProps<{ title: string; subtitle?: string }>()

const LOGO = '/nbc-logo.png'
</script>

<template>
  <div class="frame">
    <div class="backdrop">
      <TempleHalftone />
    </div>

    <main class="card">
      <img class="logo" :src="LOGO" alt="" width="56" height="56" />
      <h1>{{ title }}</h1>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
      <div class="column">
        <slot />
      </div>

      <div class="foot">
        <span>National Bank of Cambodia</span>
        <span>Authorised NBC personnel only</span>
      </div>
    </main>
  </div>
</template>

<style scoped>
.frame {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100vh;
  min-height: 100dvh;
  padding: 32px 24px;
  overflow: hidden;
  background: var(--color-paper);
}

/* The temple fills the window, faint, so it reads as a watermark behind the card. */
.backdrop {
  position: absolute;
  inset: 0;
  opacity: 0.16;
}
.backdrop :deep(.halftone) {
  position: absolute;
  inset: 0;
}

.card {
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: 34px 34px 22px;
  border: 1px solid var(--color-rule);
  border-radius: 16px;
  background: var(--color-sheet);
  box-shadow: 0 18px 50px rgba(38, 7, 7, 0.14);
}
.logo {
  display: block;
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
}
h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.02em;
  text-align: center;
}
.subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--color-intaglio);
  text-align: center;
}
.column > :slotted(*:first-child) {
  margin-top: 28px;
}
.foot {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px 24px;
  margin-top: 24px;
  padding-top: 14px;
  border-top: 1px solid var(--color-rule);
  font-size: 12px;
  color: var(--color-intaglio);
  text-align: center;
}

/* Roomier controls on these single-task pages. */
.column :deep(.input) {
  height: 46px;
  padding: 0 14px;
  border-color: var(--color-rule);
  box-shadow: 0 1px 2px rgba(42, 28, 19, 0.03);
}
.column :deep(.input:hover) {
  border-color: var(--color-rule-strong);
}
.column :deep(.input:focus) {
  border-color: var(--color-crimson);
}
.column :deep(.btn) {
  height: 46px;
}
.column :deep(.btn.primary) {
  box-shadow: 0 10px 24px -8px rgba(153, 27, 27, 0.55);
}
.column :deep(.field) {
  gap: 8px;
}
.column :deep(.field > label) {
  font-size: 13.5px;
}

:root[data-theme='dark'] .card {
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.5);
}

/* Phone: the card sits near the top, flat, with less padding. */
@media (max-width: 680px) {
  .frame {
    place-items: start center;
    padding: 40px 16px 24px;
  }
  .card {
    padding: 26px 20px 18px;
    box-shadow: none;
  }
}
</style>
