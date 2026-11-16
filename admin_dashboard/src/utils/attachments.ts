// Booking files (spec: booking attachments, 16 Nov 2026): PDF, Word or Excel, at most 10 MB each,
// 3 per booking. The browser checks first so nobody waits for an upload that will fail; the
// server still checks the content. The messages are the server's own.

export const MAX_FILES = 3
export const MAX_MB = 10
export const ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx'
const EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx']

/** Why this file can't be added (with `count` files already there), or null. */
export function fileProblem(file: { name: string; size: number }, count: number): string | null {
  if (count >= MAX_FILES) return `Up to ${MAX_FILES} files.`
  const dot = file.name.lastIndexOf('.')
  if (dot < 0 || !EXTENSIONS.includes(file.name.slice(dot + 1).toLowerCase())) return 'Only PDF, Word or Excel files.'
  if (file.size === 0) return 'The file is empty.'
  if (file.size > MAX_MB * 1024 * 1024) return `File too big (max ${MAX_MB} MB).`
  return null
}

/** "820 KB" under 1 MB, "1.2 MB" above. */
export function sizeText(bytes: number): string {
  const mb = bytes / (1024 * 1024)
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

/** A spreadsheet gets the sheet icon; everything else the page icon. */
export const isSheet = (name: string) => /\.xlsx?$/i.test(name)
