// Checks the record forms share (DSH-G06): text lengths in characters like the API, the two
// required names, and the sort order. Each adds its problem to `problems` under the field key.
import { orderProblem } from './sortOrder'

export const length = (text: string) => [...text].length // characters, like the API
/** Trimmed text, or null when empty (an optional field that is cleared). */
export const optional = (text: string) => text.trim() || null

export function nameProblems(form: { name_kh: string; name_en: string }, problems: Record<string, string>) {
  for (const [key, missing] of [
    ['name_kh', 'Enter the Khmer name.'],
    ['name_en', 'Enter the English name.'],
  ] as const) {
    const text = form[key].trim()
    if (!text) problems[key] = missing
    else if (length(text) > 100) problems[key] = 'Max 100 characters.'
  }
}

export function tooLong(text: string, max: number, key: string, problems: Record<string, string>) {
  if (length(text.trim()) > max) problems[key] = `Max ${max} characters.`
}

export function checkOrder(text: string, problems: Record<string, string>) {
  const problem = orderProblem(text)
  if (problem) problems.sort_order = problem
}
