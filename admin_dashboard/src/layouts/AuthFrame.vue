<script setup lang="ts">
// Pages outside the shell (sign-in, new password, no access), full screen in two panels:
// the form on the paper, with the brand above it, and the Bakong temple in halftone beside it.
import TempleHalftone from '../components/TempleHalftone.vue'

defineProps<{ title: string; subtitle?: string }>()

const LOGO = '/nbc-logo.png'
</script>

<template>
  <div class="frame">
    <main class="form-panel">
      <div class="brand">
        <span class="seal"><img :src="LOGO" alt="" width="34" height="34" /></span>
        <div class="name">
          <b>Meeting Rooms</b>
          <span>Admin</span>
        </div>
      </div>

      <div class="column">
        <h1>{{ title }}</h1>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
        <slot />
      </div>

      <div class="foot">
        <span>National Bank of Cambodia</span>
        <span>Authorised NBC personnel only</span>
      </div>
    </main>

    <div class="art">
      <TempleHalftone />
    </div>
  </div>
</template>

<style scoped>
.frame {
  display: grid;
  grid-template-columns: minmax(440px, 46fr) minmax(0, 54fr);
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--color-paper);
}

.form-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 40px;
  padding: 40px clamp(32px, 7vw, 112px);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.seal {
  flex: none;
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border: 1px solid rgba(226, 179, 60, 0.5);
  border-radius: 50%;
  background: var(--color-rail);
  box-shadow: 0 4px 10px rgba(38, 7, 7, 0.22);
}
.seal img {
  width: 34px;
  height: 34px;
}
.name b {
  display: block;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.name span {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
}

.column {
  width: 100%;
  max-width: 380px;
}
h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.02em;
}
.subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--color-intaglio);
}
.column > :slotted(*:first-of-type) {
  margin-top: 32px;
}
.foot {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 4px 24px;
  max-width: 380px;
  padding-top: 16px;
  border-top: 1px solid var(--color-rule);
  font-size: 12px;
  color: var(--color-intaglio);
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

.art {
  position: relative;
  min-height: 100%;
}
.art :deep(.halftone) {
  position: absolute;
  inset: 0;
}

/* Narrow: the temple goes, the form stays centred. */
@media (max-width: 900px) {
  .frame {
    grid-template-columns: minmax(0, 1fr);
  }
  .art {
    display: none;
  }
  .form-panel {
    align-items: center;
  }
  .brand,
  .column,
  .foot {
    width: 100%;
    max-width: 420px;
  }
}
@media (max-width: 680px) {
  .form-panel {
    gap: 32px;
    padding: 24px 20px;
  }
  h1 {
    font-size: 26px;
  }
}
</style>
