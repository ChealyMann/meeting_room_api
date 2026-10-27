// The department select, grouped by office (the API filters divisions by department only, so
// the office is how an admin finds the right "IT"). G08 rules inside each group.
import type { DepartmentOut, LocationOut } from '../api/types'
import { selectOptions, type SelectOption } from './selectOptions'

export interface OptionGroup {
  label: string
  options: SelectOption[]
}

export function departmentGroups(
  departments: DepartmentOut[],
  offices: LocationOut[],
  chosen: number | null,
): OptionGroup[] {
  const groups: OptionGroup[] = []
  if (chosen !== null && !departments.some((d) => d.id === chosen)) {
    groups.push({ label: '', options: [{ value: chosen, label: 'Unknown department' }] })
  }
  for (const office of offices) {
    const inOffice = departments.filter((d) => d.location_id === office.id)
    // The placeholder for an unknown id is added above, once, not per office.
    const options = selectOptions(inOffice, chosen, (d) => d.name_en, '').filter((o) => o.label !== '')
    if (options.length) groups.push({ label: office.is_active ? office.name_en : `${office.name_en} (off)`, options })
  }
  return groups
}
