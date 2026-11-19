// Holiday alert on To review (owner, 19 Nov 2026): the admin's Holidays list, matched to a
// booking's days. The row's tag is the Khmer name, with "1/3" when only some days are holidays.
import type { PublicHolidayOut } from '../api/types'
import { formatDay } from './time'

export type Holiday = Pick<PublicHolidayOut, 'holiday_date' | 'name_km' | 'name_en'>
/** The holidays by day ("2026-11-23"). */
export type HolidayMap = Record<string, Holiday>

export function holidayMap(list: Holiday[]): HolidayMap {
  return Object.fromEntries(list.map((h) => [h.holiday_date, h]))
}

/** "បុណ្យអុំទូក (Water Festival)", or the Khmer name alone when there is no English one. */
export const holidayName = (h: Holiday) => (h.name_en ? `${h.name_km} (${h.name_en})` : h.name_km)

/** The row's tag for a booking on these days: the first holiday's Khmer name, "· 1/3" when the
 *  booking has several days, and the day and name in full for the hover title. Null when none. */
export function holidayTag(dates: string[], map: HolidayMap): { text: string; title: string } | null {
  const on = dates.filter((d) => map[d])
  const first = on[0] ? map[on[0]]! : null
  if (!first) return null
  return {
    text: dates.length > 1 ? `${first.name_km} · ${on.length}/${dates.length}` : first.name_km,
    title: `${formatDay(first.holiday_date)} is a public holiday: ${holidayName(first)}`,
  }
}
