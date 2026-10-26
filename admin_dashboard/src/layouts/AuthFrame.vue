<script setup lang="ts">
// Pages outside the shell (sign-in, new password, no access): the crimson rail
// carries the name, the work happens on the paper beside it.
defineProps<{ title: string }>()

const LOGO = '/nbc-logo.png'
</script>

<template>
  <div class="frame">
    <aside class="band">
      <img :src="LOGO" alt="National Bank of Cambodia" width="48" height="48" />
      <div>
        <b>Meeting Rooms</b>
        <span>Admin · National Bank of Cambodia</span>
      </div>
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
  grid-template-columns: minmax(280px, 34%) minmax(0, 1fr);
  min-height: 100vh;
  min-height: 100dvh;
}
.band {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 32px;
  background: var(--color-rail);
  color: var(--color-rail-ink);
  border-right: 1px solid var(--color-rail-line);
}
.band img {
  width: 48px;
  height: 48px;
}
.band b {
  display: block;
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.band span {
  display: block;
  margin-top: 4px;
  font-size: 13px;
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
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 12px;
    padding: 16px;
    border-right: 0;
    border-bottom: 1px solid var(--color-rail-line);
  }
  .band img {
    width: 36px;
    height: 36px;
  }
  .band b {
    font-size: 15px;
  }
  .band span {
    margin-top: 0;
    font-size: 12px;
  }
  .paper {
    place-items: start center;
    padding: 32px 16px;
  }
}
</style>
