// The public holiday form: its values, the checks before sending (the API limits), and the
// bodies it sends — all fields on create, only what changed on edit.
import type { PublicHolidayCreate, PublicHolidayOut, PublicHolidayUpdate } from '../api/types'
import { length, optional, tooLong } from './formChecks'

export interface HolidayForm {
  /** YYYY-MM-DD, as a date input gives it. */
  holiday_date: string
  name_km: string
  name_en: string
  remarks: string
}

export function emptyHolidayForm(): HolidayForm {
  return { holiday_date: '', name_km: '', name_en: '', remarks: '' }
}

export function holidayFormOf(holiday: PublicHolidayOut): HolidayForm {
  return {
    holiday_date: holiday.holiday_date,
    name_km: holiday.name_km,
    name_en: holiday.name_en ?? '',
    remarks: holiday.remarks ?? '',
  }
}

const HTML = /<[A-Za-z/!]/

/** Problems to show before sending, by field. Empty when the form can be sent. */
export function holidayProblems(form: HolidayForm): Record<string, string> {
  const problems: Record<string, string> = {}
  if (!/^\d{4}-\d{2}-\d{2}$/.test(form.holiday_date)) problems.holiday_date = 'Pick the date.'
  const km = form.name_km.trim()
  if (!km) problems.name_km = 'Enter the Khmer name.'
  else if (length(km) > 255) problems.name_km = 'Max 255 characters.'
  tooLong(form.name_en, 255, 'name_en', problems)
  tooLong(form.remarks, 1000, 'remarks', problems)
  for (const key of ['name_km', 'name_en', 'remarks'] as const) {
    if (!problems[key] && HTML.test(form[key])) problems[key] = 'HTML is not allowed.'
  }
  return problems
}

/** POST /public-holidays. Empty optional fields are sent as null. */
export function holidayCreateBody(form: HolidayForm): PublicHolidayCreate {
  return {
    holiday_date: form.holiday_date,
    name_km: form.name_km.trim(),
    name_en: optional(form.name_en),
    remarks: optional(form.remarks),
  }
}

/** PATCH /public-holidays/{id}: only what changed. */
export function holidayChanges(form: HolidayForm, holiday: PublicHolidayOut): PublicHolidayUpdate {
  const changes: PublicHolidayUpdate = {}
  if (form.holiday_date !== holiday.holiday_date) changes.holiday_date = form.holiday_date
  if (form.name_km.trim() !== holiday.name_km) changes.name_km = form.name_km.trim()
  if (optional(form.name_en) !== holiday.name_en) changes.name_en = optional(form.name_en)
  if (optional(form.remarks) !== holiday.remarks) changes.remarks = optional(form.remarks)
  return changes
}

/** "Mon 9 Nov 2026" for a YYYY-MM-DD date, read as a calendar day (no time zone shift). */
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function holidayDateLabel(date: string): string {
  const d = new Date(`${date}T00:00:00Z`)
  return `${DAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}
