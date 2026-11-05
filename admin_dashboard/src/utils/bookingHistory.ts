// A booking's History tab (owner decision, 5 Nov 2026): a process bar of the route's steps on
// top, and a timeline of what happened under it, each step with who did it and their role.
// Everything here is read from the booking the API sends; nothing is stored.
import type { BookingDetail } from '../api/types'
import { formatDay, formatPhnomPenh } from './time'

export type StepState = 'done' | 'stop' | 'now' | 'todo'
export interface ProcessStep {
  label: string
  state: StepState
}

export type RoleKey = 'booker' | 'pitika' | 'owner' | 'it' | 'system' | 'admin'
export const ROLE_LABELS: Record<RoleKey, string> = {
  booker: 'Booker',
  pitika: 'Pitika',
  owner: 'Room owner',
  it: 'IT Lead',
  system: 'System',
  admin: 'Admin',
}

export type EventKind =
  | 'sent'
  | 'approved'
  | 'rejected'
  | 'expired'
  | 'cancelled'
  | 'skipped'
  | 'toIT'
  | 'assigned'
  | 'ready'
  | 'confirmed'
  | 'ended'
  | 'waiting'

export interface HistoryEvent {
  kind: EventKind
  label: string
  /** Phnom Penh time, "4 Nov 2026, 08:36"; null for a step that has not happened. */
  at: string | null
  /** Who acted; null when the API does not say (the IT Lead) or nobody did (the system). */
  name: string | null
  role: RoleKey | null
  /** The Admin standing in: the role whose step they took. */
  forRole?: RoleKey
  note?: string | null
}

export interface BookingHistory {
  steps: ProcessStep[]
  events: HistoryEvent[]
}

type Stage = 'PITIKA' | 'OWNER'
const STAGE_ROLE: Record<Stage, RoleKey> = { PITIKA: 'pitika', OWNER: 'owner' }
const STAGE_LABEL: Record<Stage, string> = { PITIKA: 'Pitika', OWNER: 'Room owner' }

/** Pitika only (R1, R4), Pitika then the owner (R2), nobody (R3: the owner's own room). */
function stagesOf(route: string): Stage[] {
  if (route === 'R2') return ['PITIKA', 'OWNER']
  if (route === 'R3') return []
  return ['PITIKA']
}

export function buildHistory(b: BookingDetail): BookingHistory {
  const stages = stagesOf(b.route)
  const hasIt = b.has_it && b.route !== 'R3'
  const rejection = b.rejection
  const approved = (stage: Stage) => b.reviews.find((r) => r.stage === stage && r.decision === 'APPROVED')
  // An expired booking stopped at the first review nobody made.
  const expiredAt = rejection?.rejected_by === 'SYSTEM' ? stages.find((s) => !approved(s)) : undefined

  function stageState(stage: Stage): StepState {
    if (approved(stage)) return 'done'
    if (rejection?.rejected_by === stage || expiredAt === stage) return 'stop'
    if (b.status === `PENDING_${stage}`) return 'now'
    return 'todo'
  }
  const reviewsDone = stages.every((s) => approved(s))
  const itDone = !hasIt || !!b.it?.ready_at || b.status === 'CONFIRMED'
  const confirmed =
    b.status === 'CONFIRMED' || (b.status === 'CANCELLED' && reviewsDone && (!hasIt || !!b.it?.ready_at))

  // --- The bar ----------------------------------------------------------------------------
  let steps: ProcessStep[] = [{ label: 'Sent', state: 'done' }]
  for (const stage of stages) steps.push({ label: STAGE_LABEL[stage], state: stageState(stage) })
  if (hasIt) {
    const state: StepState = b.status === 'SETUP_IN_PROGRESS' ? 'now' : itDone && reviewsDone ? 'done' : 'todo'
    steps.push({ label: 'IT setup', state })
  }
  steps.push({ label: 'Confirmed', state: confirmed ? 'done' : 'todo' })
  if (b.status === 'CANCELLED') {
    // What never happened is dropped; the cancel ends the line.
    steps = steps.filter((s) => s.state === 'done')
    steps.push({ label: 'Cancelled', state: 'stop' })
  }
  if (b.display_status === 'COMPLETED') steps.push({ label: 'Ended', state: 'done' })

  // --- The timeline -----------------------------------------------------------------------
  const timed: Array<{ ms: number; event: HistoryEvent }> = []
  const add = (iso: string | null | undefined, event: Omit<HistoryEvent, 'at'>) => {
    if (iso) timed.push({ ms: Date.parse(iso), event: { ...event, at: formatPhnomPenh(iso) } })
  }

  add(b.created_at, { kind: 'sent', label: 'Sent', name: b.requester.name_en, role: 'booker' })

  for (const r of b.reviews) {
    const stageRole = STAGE_ROLE[r.stage as Stage]
    const who = r.by_admin
      ? { name: r.reviewer?.name_en ?? null, role: 'admin' as const, forRole: stageRole }
      : { name: r.reviewer?.name_en ?? null, role: stageRole }
    if (r.decision === 'APPROVED') {
      add(r.reviewed_at, { kind: 'approved', label: 'Approved', ...who, note: r.notes })
    } else if (r.decision === 'NOT_REQUIRED') {
      add(r.reviewed_at, {
        kind: 'skipped',
        label: `${STAGE_LABEL[r.stage as Stage]} not needed`,
        name: null,
        role: 'system',
        note: r.notes,
      })
    } else if (!rejection) {
      // The API writes a rejection twice (as a review and as `rejection`): show it once.
      add(r.reviewed_at, { kind: 'rejected', label: 'Rejected', ...who, note: r.notes })
    }
  }

  if (b.it) {
    add(b.it.forwarded_at, { kind: 'toIT', label: 'Sent to IT', name: null, role: 'system' })
    const staff = b.it.staff.map((s) => s.name_en).join(', ')
    add(b.it.assigned_at, {
      kind: 'assigned',
      label: 'Staff assigned',
      name: null,
      role: 'it',
      note: staff ? `Staff: ${staff}` : null,
    })
    add(b.it.ready_at, { kind: 'ready', label: 'IT ready', name: null, role: 'it' })
  }

  if (confirmed) {
    // Confirmed when the last step before it finished. When IT was not ready in time the
    // system confirms at the meeting start, which the API does not record: no row then.
    const lastReview = stages.length ? approved(stages[stages.length - 1]!)?.reviewed_at : b.created_at
    const at = hasIt ? b.it?.ready_at : lastReview
    add(at, { kind: 'confirmed', label: 'Confirmed · door pass ready', name: null, role: 'system' })
  }

  if (rejection) {
    if (rejection.rejected_by === 'SYSTEM') {
      add(rejection.decided_at, { kind: 'expired', label: 'Expired', name: null, role: 'system', note: rejection.reason })
    } else {
      const stageRole = STAGE_ROLE[rejection.rejected_by as Stage]
      add(rejection.decided_at, {
        kind: 'rejected',
        label: 'Rejected',
        name: rejection.actor?.name_en ?? null,
        ...(rejection.by_admin ? { role: 'admin' as const, forRole: stageRole } : { role: stageRole }),
        note: rejection.reason,
      })
    }
  }

  if (b.cancelled_at) {
    const by = b.cancelled_by
    // Only the booker or the Admin cancels; nobody named means the system did (B-27).
    const role: RoleKey = !by ? 'system' : by.id === b.requester.id ? 'booker' : 'admin'
    add(b.cancelled_at, { kind: 'cancelled', label: 'Cancelled', name: by?.name_en ?? null, role, note: b.cancel_reason })
  }

  if (b.display_status === 'COMPLETED') {
    const time = b.last_end.time.slice(0, 5)
    timed.push({
      ms: Date.parse(`${b.last_end.date}T${time}:00+07:00`),
      event: {
        kind: 'ended',
        label: 'Meeting ended',
        at: `${formatDay(b.last_end.date).slice(4)}, ${time}`,
        name: null,
        role: null,
      },
    })
  }

  // Oldest first; steps at the same minute keep the order above (sort is stable).
  const events = timed.sort((x, y) => x.ms - y.ms).map((t) => t.event)

  const waiting: Partial<Record<string, Omit<HistoryEvent, 'at' | 'kind' | 'name'>>> = {
    PENDING_PITIKA: { label: 'Waiting for Pitika', role: 'pitika' },
    PENDING_OWNER: { label: 'Waiting for the room owner', role: 'owner' },
    SETUP_IN_PROGRESS: { label: 'Waiting for IT to be ready', role: 'it' },
  }
  const now = waiting[b.status]
  if (now) events.push({ kind: 'waiting', at: null, name: null, ...now })

  return { steps, events }
}
