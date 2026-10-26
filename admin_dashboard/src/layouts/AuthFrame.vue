<script setup lang="ts">
// Pages outside the shell (sign-in, new password, no access): the crimson rail
// carries the name, the work happens on the paper beside it.
defineProps<{ title: string }>()

const LOGO = '/nbc-logo.png'
</script>

<template>
  <div class="frame">
    <aside class="band">
      <div class="brand">
        <img :src="LOGO" alt="" width="64" height="64" />
        <b>Meeting Rooms</b>
        <span>Admin</span>
      </div>
      <p class="bank">National Bank of Cambodia</p>
    </aside>
    <main class="paper">
      <div class="column">
        <h1>{{ title }}</h1>
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.frame {
  display: grid;
  grid-template-columns: clamp(300px, 28vw, 420px) minmax(0, 1fr);
  min-height: 100vh;
  min-height: 100dvh;
}
.band {
  display: grid;
  grid-template-rows: 1fr auto;
  padding: 32px;
  background: var(--color-rail);
  color: var(--color-rail-ink);
  border-right: 1px solid var(--color-rail-line);
}
/* Centred, so the name sits level with the form beside it. */
.brand {
  align-self: center;
  display: grid;
  justify-items: start;
}
.brand img {
  width: 64px;
  height: 64px;
  margin-bottom: 20px;
}
.brand b {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.brand span {
  margin-top: 4px;
  font-size: 13px;
  color: var(--color-rail-muted);
}
.bank {
  margin: 0;
  padding-top: 16px;
  border-top: 1px solid var(--color-rail-line);
  font-size: 12px;
  color: var(--color-rail-muted);
}
.paper {
  display: grid;
  place-items: center;
  padding: 40px 24px;
}
.column {
  width: 100%;
  max-width: 360px;
}
h1 {
  margin: 0 0 24px;
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
@media (max-width: 760px) {
  .frame {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto 1fr;
  }
  .band {
    grid-template-rows: auto;
    padding: 16px;
    border-right: 0;
    border-bottom: 1px solid var(--color-rail-line);
  }
  .brand {
    grid-template-columns: auto 1fr;
    column-gap: 12px;
    align-items: center;
  }
  .brand img {
    grid-row: span 2;
    width: 36px;
    height: 36px;
    margin-bottom: 0;
  }
  .brand b {
    font-size: 15px;
  }
  .brand span {
    margin-top: 0;
    font-size: 12px;
  }
  .bank {
    display: none;
  }
  .paper {
    place-items: start center;
    padding: 32px 16px;
  }
}
</style>
