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

export interface ServiceForm {
  name: string
  description: string
  sort_order: string
}

export function emptyServiceForm(): ServiceForm {
  return { name: '', description: '', sort_order: '' }
}

export function serviceFormOf(service: ServiceOut): ServiceForm {
  return { name: service.name, description: service.description ?? '', sort_order: String(service.sort_order) }
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
  }
}

/** PATCH: only what changed, with the version that was read; `{}` when nothing changed. */
export function serviceChanges(form: ServiceForm, service: ServiceOut): Partial<ServiceUpdate> {
  const changes: Partial<ServiceUpdate> = {}
  const description = form.description.trim() || null
  if (form.name.trim() !== service.name) changes.name = form.name.trim()
  if (description !== (service.description ?? null)) changes.description = description
  if (orderValue(form.sort_order) !== service.sort_order) changes.sort_order = orderValue(form.sort_order)
  return Object.keys(changes).length ? { ...changes, version: service.version } : {}
}
