<script setup lang="ts">
// One booking waiting for the Pitika (spec 2026-11-05-pitika-review-design, "The side panel"):
// the room's photo, the full process bar, what is special about it, the meeting, the food and
// the IT help, then Reject and Approve. Decisions happen in the page's confirm pop-up.
import { Check, FileText, TriangleAlert } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import type { BookingDetail } from '../../api/types'
import ApprovedBy from '../../components/ApprovedBy.vue'
import BaseButton from '../../components/base/BaseButton.vue'
import BookingDetails from '../../components/BookingDetails.vue'
import BookingFiles from '../../components/BookingFiles.vue'
import BookingServices from '../../components/BookingServices.vue'
import BookingTabs from '../../components/BookingTabs.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ProcessBar from '../../components/ProcessBar.vue'
import { SLIP_LABEL, useRequestSlip } from '../../composables/useRequestSlip'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { statusLabel } from '../../utils/bookingLabels'
import { buildHistory } from '../../utils/bookingHistory'
import { approvedBy } from '../../utils/approvals'

const props = defineProps<{
  booking: BookingDetail
  /** The room's cover photo (full size), or null. */
  photoPath: string | null
  /** "Starts in …" for a booking starting today, else null. */
  startsIn: string | null
  /** A booking already decided: where it is now, and only Close (spec 2026-11-05-pitika-decided). */
  readOnly?: boolean
  /** The subtitle while it waits ("Waiting for Pitika", "Waiting for room owner"). */
  waitingLabel?: string
  /** One note for the reviewer on amber wash (the R4 note, the Pitika's notes), or null. */
  note?: string | null
}>()
const emit = defineEmits<{ close: []; approve: []; reject: [] }>()

// The request slip (ប័ណ្ណស្នើ): only on a decided, confirmed booking.
const slip = useRequestSlip(() => (props.readOnly ? props.booking : null))

const steps = computed(() => buildHistory(props.booking).steps)

const approvals = computed(() => approvedBy(props.booking))

// Tabs (owner pick, 16 Nov 2026): the photo, the steps and the buttons stay; the rest is split.
// A count on Food & IT says there is something to check; Files shows only when there are files.
type Tab = 'details' | 'services' | 'files' | 'approvals'
const tab = ref<Tab>('details')
watch(
  () => props.booking.id,
  () => (tab.value = 'details'),
)
const count = (n: number) => (n ? ` ${n}` : '')
const tabs = computed(() => {
  const services = (props.booking.catering?.packages.length ?? 0) + (props.booking.it?.items.length ?? 0)
  const files = props.booking.attachments?.length ?? 0
  const list: Array<{ id: Tab; label: string }> = [
    { id: 'details', label: 'Details' },
    { id: 'services', label: `Food & IT${count(services)}` },
  ]
  if (files) list.push({ id: 'files', label: `Files${count(files)}` })
  list.push({ id: 'approvals', label: `Approvals${count(approvals.value.length)}` })
  return list
})
</script>

<template>
  <SidePanel
    :open="true"
    :title="booking.meeting_title"
    :subtitle="readOnly ? statusLabel(booking.display_status) : (waitingLabel ?? 'Waiting for Pitika')"
    :serial="booking.reference_code"
    @close="emit('close')"
  >
    <div class="review-panel">
      <figure class="hero">
        <RoomPhoto class="photo" :path="photoPath" :alt="booking.room.name_en" />
        <figcaption>
          <span class="kh">{{ booking.room.name_kh }}</span>
          <span>{{ booking.room.name_en }} · {{ booking.room.location.name_en }}</span>
        </figcaption>
      </figure>

      <ProcessBar :steps="steps" size="large" />

      <p v-if="startsIn && !readOnly" class="note">
        <TriangleAlert aria-hidden="true" />
        <span>{{ startsIn }}. If nobody decides before it starts, it is rejected by the system.</span>
      </p>
      <p v-if="note" class="note">
        <TriangleAlert aria-hidden="true" />
        <span>{{ note }}</span>
      </p>

      <BookingTabs v-model="tab" :tabs="tabs" class="tab-bar" />

      <section v-show="tab === 'details'" id="tabpanel-details" role="tabpanel" aria-labelledby="tab-details">
        <BookingDetails :booking="booking" />
      </section>

      <section v-show="tab === 'approvals'" id="tabpanel-approvals" role="tabpanel" aria-labelledby="tab-approvals">
        <h3>Approved by</h3>
        <ApprovedBy :booking="booking" />
      </section>

      <section v-show="tab === 'services'" id="tabpanel-services" role="tabpanel" aria-labelledby="tab-services">
        <BookingServices :booking="booking" viewer="staff" />
      </section>

      <section
        v-if="booking.attachments?.length"
        v-show="tab === 'files'"
        id="tabpanel-files"
        role="tabpanel"
        aria-labelledby="tab-files"
      >
        <h3>Files</h3>
        <BookingFiles :booking-id="booking.id" :files="booking.attachments" />
      </section>
    </div>

    <template #foot>
      <div class="foot">
        <BaseButton variant="quiet" @click="emit('close')">Close</BaseButton>
        <template v-if="slip.hasSlip.value">
          <span class="spacer" />
          <span v-if="slip.error.value" class="slip-error" role="alert">{{ slip.error.value }}</span>
          <BaseButton class="kh" :busy="slip.busy.value" @click="slip.download"><FileText aria-hidden="true" />{{ SLIP_LABEL }}</BaseButton>
        </template>
        <template v-if="!readOnly">
          <span class="spacer" />
          <BaseButton variant="danger" @click="emit('reject')">Reject</BaseButton>
          <BaseButton variant="primary" @click="emit('approve')"><Check aria-hidden="true" />Approve</BaseButton>
        </template>
      </div>
    </template>
  </SidePanel>
</template>

<style scoped>
.hero {
  position: relative;
  margin: -16px -20px 16px;
}
.hero .photo {
  height: 188px;
}
.hero figcaption {
  position: absolute;
  inset: auto 0 0;
  display: grid;
  gap: 1px;
  padding: 28px 20px 12px;
  background: linear-gradient(to top, rgba(26, 6, 6, 0.74), rgba(26, 6, 6, 0));
  color: #fff;
  font-size: 12.5px;
}
.hero .kh {
  font-family: var(--font-kh);
  font-size: 15px;
  font-weight: 500;
}
.note {
  display: flex;
  gap: 8px;
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-warn) 10%, var(--color-sheet));
  color: var(--color-warn);
  font-size: 12.5px;
  font-weight: 500;
}
.note :deep(svg.lucide) {
  flex: none;
  width: 16px;
  height: 16px;
  margin-top: 1px;
}
h3 {
  margin: 20px 0 4px;
  font-size: 13px;
  font-weight: 600;
}
.tab-bar {
  margin-block: 16px 14px;
}
[role='tabpanel'] > h3:first-child {
  margin-top: 0;
}
.foot {
  display: flex;
  flex: 1;
  gap: 8px;
}
.spacer {
  flex: 1;
}
.slip-error {
  align-self: center;
  font-size: 13px;
  color: var(--color-crimson);
}
</style>
