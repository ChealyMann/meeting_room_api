// Use a DatePicker the way a person does: open it, move to the month, click the day.
import { flushPromises } from '@vue/test-utils'

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
] // prettier-ignore

function parts(root: HTMLElement) {
  const button = root.querySelector<HTMLButtonElement>('.trigger')
  const pop = root.querySelector<HTMLElement>('.pop')
  return { button, pop }
}

function rootOf(id: string): HTMLElement {
  const root = document.getElementById(id)?.closest<HTMLElement>('.date-picker')
  if (!root) throw new Error(`no date picker #${id}`)
  return root
}

/** Opens the picker, moves to the month of `day` ("YYYY-MM-DD") and clicks it. */
export async function pickDate(id: string, day: string): Promise<void> {
  const root = rootOf(id)
  if (!parts(root).pop) {
    parts(root).button!.click()
    await flushPromises()
  }
  const [y, m, d] = day.split('-').map(Number) as [number, number, number]
  const want = y * 12 + (m - 1)
  for (let step = 0; step < 600; step++) {
    const title = parts(root).pop?.querySelector('.title')?.textContent?.trim() ?? ''
    const [name, year] = title.split(' ')
    const shown = Number(year) * 12 + MONTHS.indexOf(name ?? '')
    if (shown === want) break
    const move = shown < want ? 'Next month' : 'Previous month'
    parts(root).pop!.querySelector<HTMLButtonElement>(`button[aria-label="${move}"]`)!.click()
    await flushPromises()
  }
  const cell = [...parts(root).pop!.querySelectorAll<HTMLButtonElement>('.day:not(.other)')].find(
    (b) => Number(b.textContent?.trim()) === d,
  )
  if (!cell) throw new Error(`no day ${day} in #${id}`)
  if (cell.disabled) throw new Error(`day ${day} cannot be picked in #${id}`)
  cell.click()
  await flushPromises()
}

/** Opens the picker and clicks Clear. */
export async function clearDate(id: string): Promise<void> {
  const root = rootOf(id)
  if (!parts(root).pop) {
    parts(root).button!.click()
    await flushPromises()
  }
  const clear = [...parts(root).pop!.querySelectorAll<HTMLButtonElement>('.foot button')].find((b) => b.textContent?.trim() === 'Clear')
  if (!clear) throw new Error(`no Clear in #${id}`)
  clear.click()
  await flushPromises()
}

/** The text the field shows ("Thu 5 Nov 2026", or its placeholder). */
export function dateLabel(id: string): string {
  return parts(rootOf(id)).button?.textContent?.trim() ?? ''
}
