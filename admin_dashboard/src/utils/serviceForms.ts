// The catering package and IT service forms (the API gives both the same fields and limits).
import type { ServiceCreate, ServiceKind, ServiceOut, ServiceUpdate } from '../api/services'
import { checkOrder, length } from './formChecks'
import { orderValue } from './sortOrder'

/** The words each page uses. */
export const SERVICE_KINDS: Record<
  ServiceKind,
  { title: string; one: string; many: string; serial: 'CP' | 'IS'; newLabel: string; empty: string; kind: 'catering package' | 'IT service' }
> = {
  catering: {
    title: 'Catering packages',
    one: 'package',
    many: 'packages',
    serial: 'CP',
    newLabel: 'New package',
    empty: 'No catering packages yet',
    kind: 'catering package',
  },
  it: {
    title: 'IT services',
    one: 'service',
    many: 'services',
    serial: 'IS',
    newLabel: 'New service',
    empty: 'No IT services yet',
    kind: 'IT service',
  },
}

/** The groups Staff see food and IT help under (owner decision, 12 Nov 2026). No group = "Other". */
export const SERVICE_GROUPS: Record<ServiceKind, { value: string; label: string }[]> = {
  catering: [
    { value: 'BREAKFAST', label: 'Breakfast' },
    { value: 'MEALS', label: 'Meals' },
    { value: 'BREAKS', label: 'Breaks & drinks' },
  ],
  it: [
    { value: 'SCREENS', label: 'Screens & video' },
    { value: 'SOUND', label: 'Sound & language' },
    { value: 'DEVICES', label: 'Devices & network' },
    { value: 'SUPPORT', label: 'Support' },
  ],
}

/** A group's words; an unknown code shows as it is, no group as null. */
export function groupLabel(kind: ServiceKind, group: string | null | undefined): string | null {
  if (!group) return null
  return SERVICE_GROUPS[kind].find((g) => g.value === group)?.label ?? group
}

export interface ServiceForm {
  name: string
  description: string
  sort_order: string
  group: string | null
  icon: string | null
}

export function emptyServiceForm(): ServiceForm {
  return { name: '', description: '', sort_order: '', group: null, icon: null }
}

export function serviceFormOf(service: ServiceOut): ServiceForm {
  return {
    name: service.name,
    description: service.description ?? '',
    sort_order: String(service.sort_order),
    group: service.group ?? null,
    icon: service.icon ?? null,
  }
}

/** Problems to show before sending, by field. Empty when the form can be sent. */
export function serviceProblems(form: ServiceForm): Record<string, string> {
  const problems: Record<string, string> = {}
  const name = form.name.trim()
  if (!name) problems.name = 'Enter the name.'
  else if (length(name) < 2 || length(name) > 200) problems.name = 'Use 2 to 200 characters.'
  if (length(form.description.trim()) > 1000) problems.description = 'Max 1000 characters.'
  checkOrder(form.sort_order, problems)
  return problems
}

/** POST: trimmed; an empty description is left out; an empty order is sent as 0; new ones are active. */
export function serviceCreateBody(form: ServiceForm): ServiceCreate {
  const description = form.description.trim()
  return {
    name: form.name.trim(),
    ...(description ? { description } : {}),
    sort_order: orderValue(form.sort_order),
    is_active: true,
    ...(form.group ? { group: form.group } : {}),
    ...(form.icon ? { icon: form.icon } : {}),
  } as ServiceCreate
}

/** PATCH: only what changed, with the version that was read; `{}` when nothing changed. */
export function serviceChanges(form: ServiceForm, service: ServiceOut): Partial<ServiceUpdate> {
  const changes: Partial<ServiceUpdate> = {}
  const description = form.description.trim() || null
  if (form.name.trim() !== service.name) changes.name = form.name.trim()
  if (description !== (service.description ?? null)) changes.description = description
  if (orderValue(form.sort_order) !== service.sort_order) changes.sort_order = orderValue(form.sort_order)
  if (form.group !== (service.group ?? null)) (changes as Record<string, unknown>).group = form.group
  if (form.icon !== (service.icon ?? null)) changes.icon = form.icon
  return Object.keys(changes).length ? { ...changes, version: service.version } : {}
}
