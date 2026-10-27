<script setup lang="ts">
// The Bakong temple as a diamond halftone: ink dots on the paper, in the current theme.
// Decorative only: hidden from assistive tech, and drawn only once the photo loads.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import templeUrl from '../assets/bakong-temple.jpg'
import { useUiStore } from '../stores/ui'

const CELL = 5 // px between dot centres
const RIPPLE_RADIUS = 90

const canvas = ref<HTMLCanvasElement | null>(null)

let photo: HTMLImageElement | null = null
let shades: Uint8ClampedArray | null = null // brightness under each pixel, sampled per resize
let width = 0
let height = 0
let pointer = { x: -1000, y: -1000 }
let frame = 0
let observer: ResizeObserver | null = null
const reducedMotion =
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * Where the photo sits: the tower just right of centre, near the top, and the base running
 * past the bottom edge. The photo's last 5% (a ragged, light cut-out edge) falls below the
 * panel, so the stone reaches the bottom with no white strip.
 */
function placePhoto(ctx: CanvasRenderingContext2D, image: HTMLImageElement) {
  const drawH = height * 1.04
  const drawW = drawH * (image.width / image.height)
  const x = width * 0.52 - drawW * 0.51 // the tower is at 51% of the photo's width
  const y = height - drawH * 0.95
  ctx.drawImage(image, x, y, drawW, drawH)
}

function sample() {
  if (!photo || !width || !height) return
  const source = document.createElement('canvas')
  source.width = width
  source.height = height
  const ctx = source.getContext('2d', { willReadFrequently: true })
  if (!ctx) return
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, width, height)
  placePhoto(ctx, photo)
  shades = ctx.getImageData(0, 0, width, height).data
}

/** 0 at the wavy left edge, 1 well inside it: the dots fade in like ink soaking paper. */
function edge(x: number, y: number): number {
  const nx = x / width
  const ny = y / height
  const wave = 0.12 + 0.18 * Math.sin(ny * 4.2 - 0.6) + 0.08 * Math.cos(ny * 9.5) + (1 - ny) * 0.08
  return Math.max(0, Math.min(1, (nx - wave) / 0.18))
}

function draw() {
  frame = 0
  const el = canvas.value
  if (!el || !shades) return
  const ctx = el.getContext('2d')
  if (!ctx) return
  const ratio = window.devicePixelRatio || 1
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
  // Read the theme's colours at draw time, so day and night both look printed.
  const root = getComputedStyle(document.documentElement)
  ctx.fillStyle = root.getPropertyValue('--color-paper').trim() || '#f9f7f5'
  ctx.fillRect(0, 0, width, height)
  ctx.fillStyle = root.getPropertyValue('--color-halftone').trim() || '#2a1c13'

  for (let y = CELL / 2; y < height; y += CELL) {
    for (let x = CELL / 2; x < width; x += CELL) {
      const fade = edge(x, y)
      if (fade <= 0.02) continue
      const i = (Math.floor(y) * width + Math.floor(x)) * 4
      const light = (0.25 * shades[i]! + 0.5 * shades[i + 1]! + 0.25 * shades[i + 2]!) / 255
      let dark = Math.pow(Math.max(0, 1 - light - 0.05) / 0.95, 1.1) * fade

      const distance = Math.hypot(x - pointer.x, y - pointer.y)
      if (distance < RIPPLE_RADIUS) {
        dark += Math.sin(distance * 0.15) * (1 - distance / RIPPLE_RADIUS) * 0.22
        dark = Math.max(0, Math.min(1, dark))
      }
      if (dark < 0.08) continue

      const r = CELL * 0.72 * dark
      ctx.beginPath()
      ctx.moveTo(x, y - r)
      ctx.lineTo(x + r, y)
      ctx.lineTo(x, y + r)
      ctx.lineTo(x - r, y)
      ctx.closePath()
      ctx.fill()
    }
  }
}

function schedule() {
  if (!frame) frame = requestAnimationFrame(draw)
}

function resize() {
  const el = canvas.value
  if (!el) return
  const box = el.getBoundingClientRect()
  width = Math.floor(box.width)
  height = Math.floor(box.height)
  const ratio = window.devicePixelRatio || 1
  el.width = Math.floor(width * ratio)
  el.height = Math.floor(height * ratio)
  sample()
  draw()
}

function onPointer(event: PointerEvent) {
  if (reducedMotion || !canvas.value) return
  const box = canvas.value.getBoundingClientRect()
  pointer = { x: event.clientX - box.left, y: event.clientY - box.top }
  schedule()
}

function onLeave() {
  pointer = { x: -1000, y: -1000 }
  schedule()
}

// Redraw in the new colours when day/night changes.
const ui = useUiStore()
watch(
  () => ui.theme,
  () => schedule(),
  { flush: 'post' },
)

onMounted(() => {
  const image = new Image()
  image.onload = () => {
    photo = image
    resize()
    if (typeof ResizeObserver === 'function' && canvas.value) {
      observer = new ResizeObserver(resize)
      observer.observe(canvas.value)
    }
  }
  image.src = templeUrl
})

onBeforeUnmount(() => {
  observer?.disconnect()
  if (frame) cancelAnimationFrame(frame)
})
</script>

<template>
  <canvas
    ref="canvas"
    class="halftone"
    aria-hidden="true"
    @pointermove="onPointer"
    @pointerleave="onLeave"
  />
</template>

<style scoped>
.halftone {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
