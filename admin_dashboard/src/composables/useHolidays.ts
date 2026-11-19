// The admin's public holidays, loaded one year at a time and only once per year (owner, 19 Nov
// 2026: the holiday alert on To review). A year that fails to load is tried again next time;
// until then its days are simply not marked.
import { ref } from 'vue'

import { api } from '../api'
import { listHolidays } from '../api/staff'
import { holidayMap, type HolidayMap } from '../utils/holidays'

export function useHolidays() {
  const holidays = ref<HolidayMap>({})
  const asked = new Set<number>()

  /** Loads the years of these days ("2026-11-23") not loaded yet. */
  async function need(dates: string[]) {
    const years = [...new Set(dates.map((d) => Number(d.slice(0, 4))))].filter((y) => !asked.has(y))
    await Promise.all(
      years.map(async (year) => {
        asked.add(year)
        try {
          const list = await listHolidays(api, `${year}-01-01`, `${year}-12-31`)
          holidays.value = { ...holidays.value, ...holidayMap(list) }
        } catch {
          asked.delete(year)
        }
      }),
    )
  }

  return { holidays, need }
}
