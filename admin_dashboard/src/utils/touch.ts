/**
 * A device with a touch screen (iPad, phone, touch laptop). iPadOS answers "hover: hover" when a
 * trackpad or keyboard is attached, so a media query is not enough: touch points tell the truth.
 */
export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false
  return (navigator.maxTouchPoints ?? 0) > 0 || !!window.matchMedia?.('(any-pointer: coarse)').matches
}
