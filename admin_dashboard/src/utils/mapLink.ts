/** A Google Maps search for an office's map text (a place name or "lat,lng"), or null when the
 * office has none. Opens in a new tab from the Room section of the booking pop-ups. */
export function mapSearchUrl(query: string | null | undefined): string | null {
  const text = query?.trim()
  return text ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(text)}` : null
}
