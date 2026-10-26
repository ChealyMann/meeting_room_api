// The side panel's slide (DESIGN.md "Motion"), done in script so it stays smooth when a page
// swaps one panel for another (the loading panel → the form, a room's detail → its edit form)
// or removes it with v-if (closing after a save): a CSS transition dies with its component.
//
// - A panel that replaces another one in the same update starts where the old one was.
// - A panel removed by its page is put back for one slide out, then dropped.

const EASE = 'cubic-bezier(0.32, 0.72, 0, 1)' // --ease-drawer, the same as the sidebar fold
const OPEN_MS = 340
const CLOSE_MS = 240
const SAME_UPDATE_MS = 50

interface Handoff {
  x: number
  scrim: number
  at: number
  taken: boolean
  /** Removes the slide-out copy, if one was put back. */
  drop: () => void
}

let handoff: Handoff | null = null

function canAnimate(el: Element): boolean {
  if (typeof el.animate !== 'function') return false
  return !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

/** How far right of its open place the panel is now, in px. */
function offsetX(el: HTMLElement): number {
  const transform = getComputedStyle(el).transform
  return !transform || transform === 'none' ? 0 : new DOMMatrixReadOnly(transform).m41
}

/** The panel that just left in this same update, if any: the new one continues from it. */
function freshHandoff(): Handoff | null {
  return handoff && !handoff.taken && performance.now() - handoff.at < SAME_UPDATE_MS ? handoff : null
}

export function scrimIn(el: Element, done: () => void) {
  if (!canAnimate(el)) return done()
  const from = freshHandoff()
  el.animate([{ opacity: from ? from.scrim : 0 }, { opacity: 1 }], {
    duration: from ? OPEN_MS * (1 - from.scrim) : OPEN_MS,
    easing: EASE,
  }).onfinish = () => done()
}

export function panelIn(el: Element, done: () => void) {
  const panel = el as HTMLElement
  if (!canAnimate(panel)) return done()
  const from = freshHandoff()
  if (from) {
    from.taken = true
    from.drop()
  }
  const width = panel.offsetWidth || 1
  const x = from ? Math.min(from.x, width) : width
  if (x < 1) return done() // the old panel was fully open: stay put
  panel.animate([{ transform: `translateX(${x}px)` }, { transform: 'translateX(0)' }], {
    duration: Math.max(120, OPEN_MS * (x / width)),
    easing: EASE,
  }).onfinish = () => done()
}

function slideOut(panel: HTMLElement, scrim: HTMLElement | null, onEnd: () => void) {
  const width = panel.offsetWidth || 1
  const x = offsetX(panel)
  const duration = Math.max(120, CLOSE_MS * (1 - x / width))
  panel.animate([{ transform: `translateX(${x}px)` }, { transform: 'translateX(100%)' }], {
    duration,
    easing: EASE,
    fill: 'forwards',
  }).onfinish = onEnd
  scrim?.animate([{ opacity: getComputedStyle(scrim).opacity }, { opacity: 0 }], {
    duration,
    easing: EASE,
    fill: 'forwards',
  })
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

/** Before the page removes an open panel: note where it is, for a panel that replaces it. */
export function noteLeaving(panel: HTMLElement | null, scrim: HTMLElement | null) {
  if (!panel) return
  handoff = {
    x: offsetX(panel),
    scrim: scrim ? Number(getComputedStyle(scrim).opacity) : 1,
    at: performance.now(),
    taken: false,
    drop: () => {},
  }
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
