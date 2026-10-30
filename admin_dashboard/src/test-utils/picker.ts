// Use a SearchPicker the way a person does: open it with its button, read or click an option.
import { flushPromises } from '@vue/test-utils'

function trigger(id: string): HTMLButtonElement {
  const button = document.getElementById(id)
  if (!(button instanceof HTMLButtonElement)) throw new Error(`no picker #${id}`)
  return button
}

async function openList(id: string): Promise<HTMLElement> {
  const button = trigger(id)
  if (button.getAttribute('aria-expanded') !== 'true') {
    button.click()
    await flushPromises()
  }
  const list = document.getElementById(button.getAttribute('aria-controls') ?? '')
  if (!list) throw new Error(`picker #${id} did not open`)
  return list
}

const texts = (list: HTMLElement) =>
  [...list.querySelectorAll<HTMLElement>('[role="option"]')].map((o) => o.textContent?.trim() ?? '')

/** Opens the picker and clicks the option with this text. */
export async function choosePicker(id: string, label: string): Promise<void> {
  const list = await openList(id)
  const option = [...list.querySelectorAll<HTMLElement>('[role="option"]')].find((o) => o.textContent?.trim() === label)
  if (!option) throw new Error(`no option "${label}" in #${id}: ${texts(list).join(', ')}`)
  option.click()
  await flushPromises()
}

/** The option texts, read by opening the picker and closing it again. */
export async function pickerOptions(id: string): Promise<string[]> {
  const list = await openList(id)
  const found = texts(list)
  trigger(id).click()
  await flushPromises()
  return found
}

/** What the picker's button shows. */
export const pickerLabel = (id: string) => trigger(id).querySelector('.label')?.textContent?.trim()

/** Opens a TimePicker and picks this "HH:MM": the hour, then the minute. */
export async function chooseTime(id: string, value: string): Promise<void> {
  const button = trigger(id)
  if (button.getAttribute('aria-expanded') !== 'true') {
    button.click()
    await flushPromises()
  }
  const [hour, minute] = value.split(':')
  for (const [column, text] of [['Hour', hour], ['Minute', minute]] as const) {
    const list = document.querySelector<HTMLElement>(`[role="listbox"][aria-label="${column}"]`)
    const option = [...(list?.querySelectorAll<HTMLElement>('[role="option"]') ?? [])].find((o) => o.textContent?.trim() === text)
    if (!option) throw new Error(`no ${column.toLowerCase()} "${text}" in #${id}`)
    option.click()
    await flushPromises()
  }
}
