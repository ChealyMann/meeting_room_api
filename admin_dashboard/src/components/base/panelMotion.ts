// The side panel's slide (DESIGN.md "Motion"), done in script so it stays smooth when a page
// swaps one panel for another (the loading panel → the form, a room's detail → its edit form)
// or removes it with v-if (closing after a save): a CSS transition dies with its component.
//
// - A panel that replaces another one in the same Vue update carries on the old one's slide
//   (or stays put when the old one was already open).
// - A panel removed by its page is put back for one slide out, then dropped.

const EASE = 'cubic-bezier(0.32, 0.72, 0, 1)' // --ease-drawer, the same as the sidebar fold
const OPEN_MS = 340
const CLOSE_MS = 240

/** Where an animation was, so a new element can carry it on from the same point. */
interface Progress {
  keyframes: Keyframe[]
  duration: number
  currentTime: number
}

interface Handoff {
  panel: Progress | null
  scrim: Progress | null
  taken: boolean
  /** Removes the slide-out copy, if one was put back. */
  drop: () => void
}

// Lives for one Vue update only: the patch (old panel unmounts, new one mounts) and its
// post-flush (where enter runs) finish before the next microtask, however long they take.
let handoff: Handoff | null = null

function canAnimate(el: Element): boolean {
  if (typeof el.animate !== 'function') return false
  return !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

/** The element's running slide or fade, if any (null when it is at rest). */
function progressOf(el: Element | null): Progress | null {
  if (!el || typeof el.getAnimations !== 'function') return null
  const running = el.getAnimations().find((a) => a.playState === 'running')
  const effect = running?.effect as KeyframeEffect | undefined
  if (!running || !effect) return null
  return {
    keyframes: effect.getKeyframes(),
    duration: Number(effect.getTiming().duration),
    currentTime: Number(running.currentTime ?? 0),
  }
}

/** Starts `keyframes` on `el`, or carries on `from` at the point where it was. */
function play(el: Element, keyframes: Keyframe[], duration: number, from: Progress | null, done: () => void) {
  const animation = from
    ? el.animate(from.keyframes, { duration: from.duration, easing: EASE })
    : el.animate(keyframes, { duration, easing: EASE })
  if (from) animation.currentTime = from.currentTime
  animation.onfinish = () => done()
}

function takeHandoff(): Handoff | null {
  if (!handoff || handoff.taken) return null
  return handoff
}

export function scrimIn(el: Element, done: () => void) {
  if (!canAnimate(el)) return done()
  const from = takeHandoff()
  if (from && !from.scrim) return done() // the old scrim was already fully shown
  play(el, [{ opacity: 0 }, { opacity: 1 }], OPEN_MS, from?.scrim ?? null, done)
}

export function panelIn(el: Element, done: () => void) {
  if (!canAnimate(el)) return done()
  const from = takeHandoff()
  if (from) {
    from.taken = true
    from.drop()
    if (!from.panel) return done() // the old panel was already open: stay put
  }
  play(el, [{ transform: 'translateX(100%)' }, { transform: 'translateX(0)' }], OPEN_MS, from?.panel ?? null, done)
}

/** How far right of its open place the panel is now, in px. */
function offsetX(el: HTMLElement): number {
  const transform = getComputedStyle(el).transform
  return !transform || transform === 'none' ? 0 : new DOMMatrixReadOnly(transform).m41
}

function slideOut(panel: HTMLElement, scrim: HTMLElement | null, onEnd: () => void) {
  const width = panel.offsetWidth || 1
  const x = offsetX(panel)
  const duration = Math.max(120, CLOSE_MS * (1 - x / width))
  const options: KeyframeAnimationOptions = { duration, easing: EASE, fill: 'forwards' }
  panel.animate([{ transform: `translateX(${x}px)` }, { transform: 'translateX(100%)' }], options).onfinish = onEnd
  scrim?.animate([{ opacity: getComputedStyle(scrim).opacity }, { opacity: 0 }], options)
}

/** open → false while the panel stays mounted. */
export function panelOut(el: Element, done: () => void) {
  if (!canAnimate(el)) return done()
  slideOut(el as HTMLElement, null, done)
}

export function scrimOut(el: Element, done: () => void) {
  if (!canAnimate(el)) return done()
  el.animate([{ opacity: getComputedStyle(el).opacity }, { opacity: 0 }], {
    duration: CLOSE_MS,
    easing: EASE,
  }).onfinish = () => done()
}

/** Before the page removes an open panel: note its slide, for a panel that replaces it. */
export function noteLeaving(panel: HTMLElement | null, scrim: HTMLElement | null) {
  if (!panel) return
  const note: Handoff = { panel: progressOf(panel), scrim: progressOf(scrim), taken: false, drop: () => {} }
  handoff = note
  queueMicrotask(() => {
    if (handoff === note) handoff = null
  })
}

/**
 * After the page removed an open panel: put its last frame back and slide it out, unless a new
 * panel takes its place in this same update (that one calls `drop`).
 */
export function slideOutRemoved(panel: HTMLElement | null, scrim: HTMLElement | null) {
  const left = handoff
  if (!panel || !left || left.taken || panel.isConnected || !canAnimate(panel)) return
  const copies = [scrim, panel].filter((el): el is HTMLElement => !!el)
  for (const el of copies) {
    el.removeAttribute('role')
    el.setAttribute('inert', '')
    el.setAttribute('aria-hidden', 'true')
    el.style.pointerEvents = 'none'
    document.body.append(el)
  }
  const drop = () => copies.forEach((el) => el.remove())
  left.drop = drop
  slideOut(panel, scrim, drop)
}
