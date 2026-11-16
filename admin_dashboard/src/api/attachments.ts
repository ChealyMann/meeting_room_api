// The files on a booking (GET/POST /bookings/{id}/attachments, GET/DELETE …/{attachmentId}).
import type { ApiClient } from './client'
import type { AttachmentOut, ItemList } from './types'

const path = (bookingId: number) => `/api/v1/bookings/${bookingId}/attachments`

export function listAttachments(client: ApiClient, bookingId: number): Promise<ItemList<AttachmentOut>> {
  return client.request<ItemList<AttachmentOut>>('GET', path(bookingId))
}

/** Only the booker, while the booking is not confirmed, rejected or cancelled. */
export function uploadAttachment(client: ApiClient, bookingId: number, file: File): Promise<AttachmentOut> {
  const form = new FormData()
  form.append('file', file)
  return client.request<AttachmentOut>('POST', path(bookingId), { form })
}

/** `url` is the file's `url` from the API. */
export function getAttachment(client: ApiClient, url: string): Promise<Blob> {
  return client.requestBlob(url)
}

export function removeAttachment(client: ApiClient, bookingId: number, id: number): Promise<void> {
  return client.request<void>('DELETE', `${path(bookingId)}/${id}`)
}
