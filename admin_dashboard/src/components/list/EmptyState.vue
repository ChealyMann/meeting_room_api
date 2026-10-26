<script setup lang="ts">
// An empty list: what is missing, what to do, and the one ornament the design allows on
// the paper — a guilloche rosette watermark (DESIGN.md "Empty State").
defineProps<{ title: string; text: string }>()

/** Two layered hypotrochoids, as on a banknote seal. */
function rosette(scale: number): string[] {
  const rings = [
    { R: 1, r: 0.36, d: 0.52, turns: 9, phase: 0 },
    { R: 1, r: 0.24, d: 0.3, turns: 6, phase: 0.2 },
  ]
  return rings.map(({ R, r, d, turns, phase }) => {
    const steps = 720 * turns
    const points: string[] = []
    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * Math.PI * 2 * turns + phase
      const x = (R - r) * Math.cos(t) + d * Math.cos(((R - r) / r) * t)
      const y = (R - r) * Math.sin(t) - d * Math.sin(((R - r) / r) * t)
      points.push(`${(x * scale).toFixed(2)} ${(y * scale).toFixed(2)}`)
    }
    return `M${points.join('L')}`
  })
}

const PATHS = rosette(46)
</script>

<template>
  <div class="empty">
    <svg class="watermark" viewBox="-50 -50 100 100" aria-hidden="true">
      <path v-for="(d, i) in PATHS" :key="i" :d="d" />
    </svg>
    <h2>{{ title }}</h2>
    <p>{{ text }}</p>
    <div class="actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
  padding: 40px 16px;
  border-bottom: 1px solid var(--color-rule);
  text-align: center;
}
.watermark {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 240px;
  height: 240px;
  color: var(--color-crimson);
  opacity: 0.07;
  transform: translate(-50%, -50%);
}
.watermark path {
  fill: none;
  stroke: currentColor;
  stroke-width: 0.5;
}
h2 {
  position: relative;
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
}
p {
  position: relative;
  max-width: 40ch;
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--color-intaglio);
}
.actions {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}
</style>
