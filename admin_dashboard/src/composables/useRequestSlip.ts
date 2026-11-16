// The request slip (ប័ណ្ណស្នើ) of a confirmed booking, as a Word file. Only a CONFIRMED booking
// has one (a completed meeting is still CONFIRMED); the booker, the Admin and the Pitika of the
// room's province may download it.
import { computed, ref, toValue, type MaybeRefOrGetter } from 'vue'

import { api } from '../api'
import { getRequestSlip } from '../api/bookings'
import { ApiError } from '../api/errors'
import { downloadBlob } from '../utils/download'

export const SLIP_LABEL = 'ប័ណ្ណស្នើ (Word)'

interface SlipBooking {
  id: number
  reference_code: string
  status: string
}

export function useRequestSlip(booking: MaybeRefOrGetter<SlipBooking | null | undefined>) {
  const busy = ref(false)
  const error = ref('')
  const hasSlip = computed(() => toValue(booking)?.status === 'CONFIRMED')

  async function download() {
    const b = toValue(booking)
    if (!b || busy.value) return
    busy.value = true
    error.value = ''
    try {
      downloadBlob(await getRequestSlip(api, b.id), `request-slip-${b.reference_code}.docx`)
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'The slip could not load.'
    } finally {
      busy.value = false
    }
  }

  return { hasSlip, busy, error, download }
}
