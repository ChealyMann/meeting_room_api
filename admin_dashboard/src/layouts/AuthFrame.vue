<script setup lang="ts">
// Pages outside the shell (sign-in, new password, no access): a cream card on the
// rail's dark ground, the form on the left and the Bakong temple in halftone on the right.
import TempleHalftone from '../components/TempleHalftone.vue'

defineProps<{ title: string }>()

const LOGO = '/nbc-logo.png'
</script>

<template>
  <div class="backdrop">
    <div class="dots" aria-hidden="true" />
    <div class="bezel">
      <div class="card">
        <div class="left">
          <div class="brand">
            <span class="seal"><img :src="LOGO" alt="" width="36" height="36" /></span>
            <div>
              <b>Meeting Rooms</b>
              <span>Admin</span>
            </div>
          </div>

          <main class="main">
            <h1>{{ title }}</h1>
            <slot />
          </main>

          <p class="foot">National Bank of Cambodia</p>
        </div>

        <div class="art">
          <TempleHalftone />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100vh;
  min-height: 100dvh;
  padding: 40px 24px;
  overflow-x: hidden;
  background-color: var(--color-rail);
  background-image:
    radial-gradient(circle at 18% 22%, rgba(153, 27, 27, 0.22) 0%, transparent 50%),
    radial-gradient(circle at 85% 80%, rgba(226, 179, 60, 0.08) 0%, transparent 55%),
    linear-gradient(135deg, #2e0b09 0%, var(--color-rail) 55%, #170404 100%);
}
.dots {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.15;
  background-image: radial-gradient(var(--color-thread) 0.75px, transparent 0.75px);
  background-size: 28px 28px;
}
.bezel {
  position: relative;
  width: 100%;
  max-width: 1000px;
  padding: 8px;
  border-radius: 22px;
  border: 1px solid rgba(226, 179, 60, 0.28);
  background: rgba(249, 247, 245, 0.12);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  box-shadow:
    0 35px 70px -15px rgba(0, 0, 0, 0.65),
    0 0 1px 1px rgba(226, 179, 60, 0.12);
}
.card {
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
  min-height: 650px;
  overflow: hidden;
  border-radius: 15px;
  background: var(--color-paper);
}

.left {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 24px;
  padding: 36px 24px 36px 56px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.seal {
  flex: none;
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid rgba(226, 179, 60, 0.5);
  background: var(--color-rail);
  box-shadow: 0 4px 10px rgba(38, 7, 7, 0.25);
}
.seal img {
  width: 36px;
  height: 36px;
}
.brand b {
  display: block;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.brand span {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.main {
  width: 100%;
  max-width: 320px;
}
h1 {
  margin: 0 0 24px;
  font-size: 26px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.foot {
  margin: 0;
  padding-top: 16px;
  border-top: 1px solid var(--color-rule);
  font-size: 12px;
  color: var(--color-intaglio);
}

/* Roomier controls on these single-task pages. */
.main :deep(.input),
.main :deep(.btn) {
  height: 44px;
}
.main :deep(.field) {
  gap: 8px;
}
.main :deep(.field > label) {
  font-size: 13px;
}

.art {
  position: relative;
  min-height: 100%;
}
.art :deep(.halftone) {
  position: absolute;
  inset: 0;
}

@media (max-width: 900px) {
  .left {
    padding: 32px 24px 32px 40px;
  }
}
@media (max-width: 760px) {
  .backdrop {
    place-items: start center;
    padding: 16px;
  }
  .card {
    grid-template-columns: minmax(0, 1fr);
    min-height: 0;
  }
  .left {
    gap: 32px;
    padding: 28px 24px;
  }
  .main {
    max-width: none;
  }
  .art {
    height: 260px;
  }
}
</style>
