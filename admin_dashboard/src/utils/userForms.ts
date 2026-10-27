// The user form: its values, the checks before sending (the API limits, DSH-G06, R5, R18), and
// the bodies it sends — all fields on create (with the temporary password, never trimmed), only
// what changed on edit.
import type { UserCreate, UserDetail, UserUpdate } from '../api/types'
import { length, nameProblems, optional, tooLong } from './formChecks'
import { temporaryPasswordProblem } from './password'

export interface UserForm {
  staff_id: string
  /** Mr., Ms., Mrs., Dr. or none. */
  title: string | null
  name_kh: string
  name_en: string
  email: string
  secondary_email: string
  phone: string
  division_id: number | null
  position_id: number | null
  email_notifications: boolean
  /** Create only; never kept in a draft. */
  temporary_password: string
}

export const TITLES = ['Mr.', 'Ms.', 'Mrs.', 'Dr.'] as const

// The API's practical check: one @, no spaces, a dot in the domain.
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

export function emptyUserForm(): UserForm {
  return {
    staff_id: '',
    title: null,
    name_kh: '',
    name_en: '',
    email: '',
    secondary_email: '',
    phone: '',
    division_id: null,
    position_id: null,
    email_notifications: true,
    temporary_password: '',
  }
}

export function userFormOf(user: UserDetail): UserForm {
  return {
    staff_id: user.staff_id,
    title: user.title ?? null,
    name_kh: user.name_kh,
    name_en: user.name_en,
    email: user.email,
    secondary_email: user.secondary_email ?? '',
    phone: user.phone ?? '',
    division_id: user.division?.id ?? null,
    position_id: user.position.id,
    email_notifications: user.email_notifications,
    temporary_password: '',
  }
}

function emailProblem(text: string, key: string, problems: Record<string, string>) {
  if (!EMAIL.test(text)) problems[key] = 'Enter a valid email.'
  else if (length(text) > 254) problems[key] = 'Max 254 characters.'
}

/** Problems to show before sending, by field. `creating` adds the temporary password. */
export function userProblems(form: UserForm, creating: boolean): Record<string, string> {
  const problems: Record<string, string> = {}
  const staffId = form.staff_id.trim()
  if (!staffId) problems.staff_id = 'Enter the staff ID.'
  else if (length(staffId) > 20) problems.staff_id = 'Max 20 characters.'
  nameProblems(form, problems)
  const email = form.email.trim()
  if (!email) problems.email = 'Enter the email.'
  else emailProblem(email, 'email', problems)
  const second = form.secondary_email.trim()
  if (second) {
    emailProblem(second, 'secondary_email', problems)
    if (!problems.secondary_email && second.toLowerCase() === email.toLowerCase()) {
      problems.secondary_email = 'Use a different email from the main one.'
    }
  }
  tooLong(form.phone, 20, 'phone', problems)
  if (form.position_id === null) problems.position_id = 'Choose a position.'
  if (creating) {
    const problem = temporaryPasswordProblem(form.temporary_password)
    if (problem) problems.temporary_password = problem
  }
  return problems
}

/** POST /users. Empty optional fields are left out; the password goes exactly as typed. */
export function userCreateBody(form: UserForm): UserCreate {
  const body: UserCreate = {
    staff_id: form.staff_id.trim(),
    name_en: form.name_en.trim(),
    name_kh: form.name_kh.trim(),
    email: form.email.trim(),
    position_id: form.position_id!,
    email_notifications: form.email_notifications,
    temporary_password: form.temporary_password,
  }
  if (form.title) body.title = form.title
  if (optional(form.secondary_email)) body.secondary_email = optional(form.secondary_email)
  if (optional(form.phone)) body.phone = optional(form.phone)
  if (form.division_id !== null) body.division_id = form.division_id
  return body
}

/** PATCH /users/{id}: only what changed; a cleared optional field is null. Emails compare without case. */
export function userChanges(form: UserForm, user: UserDetail): UserUpdate {
  const before = userFormOf(user)
  const changes: UserUpdate = {}
  if (form.staff_id.trim() !== before.staff_id) changes.staff_id = form.staff_id.trim()
  if (form.title !== before.title) changes.title = form.title
  if (form.name_kh.trim() !== before.name_kh) changes.name_kh = form.name_kh.trim()
  if (form.name_en.trim() !== before.name_en) changes.name_en = form.name_en.trim()
  if (form.email.trim().toLowerCase() !== before.email.toLowerCase()) changes.email = form.email.trim()
  if (optional(form.secondary_email)?.toLowerCase() !== optional(before.secondary_email)?.toLowerCase()) {
    changes.secondary_email = optional(form.secondary_email)
  }
  if (optional(form.phone) !== optional(before.phone)) changes.phone = optional(form.phone)
  if (form.division_id !== before.division_id) changes.division_id = form.division_id
  if (form.position_id !== null && form.position_id !== before.position_id) changes.position_id = form.position_id
  if (form.email_notifications !== before.email_notifications) changes.email_notifications = form.email_notifications
  return changes
}
