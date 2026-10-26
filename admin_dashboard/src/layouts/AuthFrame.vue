<script setup lang="ts">
// Pages outside the shell (sign-in, new password, no access), full screen in three panels:
// left, the brand on the rail's dark ground; middle, the form; right, the Bakong temple in halftone.
import { onBeforeUnmount, onMounted, ref } from 'vue'

import TempleHalftone from '../components/TempleHalftone.vue'
import { phnomPenhClock } from '../utils/time'

defineProps<{ title: string; subtitle?: string }>()

const LOGO = '/nbc-logo.png'

const now = ref(phnomPenhClock(new Date()))
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => (now.value = phnomPenhClock(new Date())), 30_000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="frame">
    <aside class="brand-panel">
      <span class="mono clock">PNH · {{ now }}</span>

      <div class="brand">
        <span class="tile"><img :src="LOGO" alt="" width="56" height="56" /></span>
        <b>Meeting Rooms</b>
        <span class="role">Admin</span>
        <p>Rooms, places and people for the meeting-room booking system.</p>
      </div>

      <p class="foot">National Bank of Cambodia</p>
    </aside>

    <main class="form-panel">
      <div class="column">
        <h1>{{ title }}</h1>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
        <slot />
      </div>
      <p class="notice">Authorised NBC personnel only</p>
    </main>

    <div class="art">
      <TempleHalftone />
    </div>
  </div>
</template>

<style scoped>
.frame {
  display: grid;
  grid-template-columns: minmax(260px, 25fr) minmax(0, 42fr) minmax(0, 33fr);
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--color-paper);
}

/* Brand panel: the rail, carried onto the page. */
.brand-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 32px;
  padding: 40px;
  color: var(--color-rail-ink);
  background:
    radial-gradient(circle at 20% 0%, rgba(153, 27, 27, 0.25), transparent 60%),
    linear-gradient(160deg, #2e0b09 0%, var(--color-rail) 60%, #1e0505 100%);
}
.clock {
  align-self: flex-start;
  white-space: nowrap;
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--color-rail-muted);
}
.brand {
  display: grid;
  justify-items: start;
}
.tile {
  display: grid;
  place-items: center;
  width: 80px;
  height: 80px;
  margin-bottom: 28px;
  border: 1px solid rgba(226, 179, 60, 0.3);
  border-radius: 16px;
  background: linear-gradient(160deg, var(--color-rail-raised), #1e0505);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
}
.tile img {
  width: 56px;
  height: 56px;
}
.brand b {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.015em;
  color: #fff7f2;
}
.role {
  margin-top: 6px;
  font-size: 14px;
  color: var(--color-rail-muted);
}
.brand p {
  margin: 24px 0 0;
  max-width: 30ch;
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-rail-muted);
}
.foot {
  margin: 0;
  padding-top: 16px;
  border-top: 1px solid var(--color-rail-line);
  font-size: 12.5px;
}

/* Form panel */
.form-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 32px;
  padding: 56px 48px 40px 72px;
}
.column {
  width: 100%;
  max-width: 360px;
  margin: auto 0;
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
.notice {
  max-width: 360px;
  margin: 0;
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

/* Art */
.art {
  position: relative;
  min-height: 100%;
}
.art :deep(.halftone) {
  position: absolute;
  inset: 0;
}

/* Narrower: the temple goes first, the form keeps its room. */
@media (max-width: 1100px) {
  .frame {
    grid-template-columns: minmax(240px, 36fr) minmax(0, 64fr);
  }
  .art {
    display: none;
  }
  .brand-panel {
    padding: 32px;
  }
  .form-panel {
    padding: 48px 40px 32px;
  }
}
/* Phone: the brand panel becomes a short header above the form. */
@media (max-width: 680px) {
  .frame {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto 1fr;
  }
  .brand-panel {
    gap: 16px;
    padding: 20px;
  }
  .clock {
    align-self: flex-end;
  }
  .brand {
    grid-template-columns: auto 1fr;
    column-gap: 14px;
    align-items: center;
  }
  .tile {
    grid-row: span 2;
    width: 52px;
    height: 52px;
    margin: 0;
    border-radius: 12px;
  }
  .tile img {
    width: 38px;
    height: 38px;
  }
  .brand b {
    font-size: 20px;
  }
  .role {
    margin: 0;
  }
  .brand p,
  .foot {
    display: none;
  }
  .form-panel {
    padding: 32px 20px 24px;
  }
  .column {
    max-width: none;
  }
  h1 {
    font-size: 26px;
  }
}
</style>
