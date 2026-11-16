<script setup lang="ts">
// One booking waiting for the Pitika (spec 2026-11-05-pitika-review-design, "The side panel"):
// a small room photo by the title, a thin step bar (look B, owner pick 16 Nov 2026), a one-line
// warning, then tabs: the meeting, the food and the IT help, history; then Reject and Approve.
// Decisions happen in the page's confirm pop-up.
import { Check, Clock, FileText, TriangleAlert } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import type { BookingDetail } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import BookingDetails from '../../components/BookingDetails.vue'
import BookingFiles from '../../components/BookingFiles.vue'
import BookingHistory from '../../components/BookingHistory.vue'
import BookingServices from '../../components/BookingServices.vue'
import BookingTabs from '../../components/BookingTabs.vue'
import PanelSection from '../../components/PanelSection.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import StepProgress from '../../components/StepProgress.vue'
import { SLIP_LABEL, useRequestSlip } from '../../composables/useRequestSlip'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { statusLabel } from '../../utils/bookingLabels'
import { buildHistory } from '../../utils/bookingHistory'

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
  /** The Food & IT card this reviewer checks, on a light background (Pitika: food). */
  leadCard?: 'food' | 'it' | null
  /** One note for the reviewer on amber wash (the R4 note, the Pitika's notes), or null. */
  note?: string | null
}>()
const emit = defineEmits<{ close: []; approve: []; reject: [] }>()

// The request slip (ប័ណ្ណស្នើ): only on a decided, confirmed booking.
const slip = useRequestSlip(() => (props.readOnly ? props.booking : null))

const steps = computed(() => buildHistory(props.booking).steps)

// Tabs (owner pick, 16 Nov 2026): the photo, the steps and the buttons stay; the rest is split.
// A count on Food & IT says there is something to check; Files shows only when there are files.
type Tab = 'details' | 'services' | 'files' | 'history'
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
  list.push({ id: 'history', label: 'History' })
  return list
})
</script>

<template>
  <SidePanel
    :open="true"
    :title="booking.meeting_title"
    :subtitle="`${booking.room.name_kh} · ${booking.room.name_en} · ${booking.room.location.name_en}`"
    :serial="booking.reference_code"
    @close="emit('close')"
  >
    <template #lead><RoomPhoto class="room-thumb" :path="photoPath" :alt="booking.room.name_en" /></template>
    <div class="review-panel">
      <StepProgress :steps="steps" :label="readOnly ? statusLabel(booking.display_status) : (waitingLabel ?? 'Waiting for Pitika')" />

      <p v-if="startsIn && !readOnly" class="warn" title="If nobody decides before it starts, the system rejects it.">
        <Clock aria-hidden="true" />
        <span><b>{{ startsIn }}</b> · decide before, or it is rejected</span>
      </p>
      <p v-if="note" class="warn">
        <TriangleAlert aria-hidden="true" />
        <span>{{ note }}</span>
      </p>

      <BookingTabs v-model="tab" :tabs="tabs" class="tab-bar" />

      <section v-show="tab === 'details'" id="tabpanel-details" role="tabpanel" aria-labelledby="tab-details">
        <BookingDetails :booking="booking" />
      </section>

      <section v-show="tab === 'history'" id="tabpanel-history" role="tabpanel" aria-labelledby="tab-history">
        <PanelSection title="History"><BookingHistory :booking="booking" :bar="false" /></PanelSection>
      </section>

      <section v-show="tab === 'services'" id="tabpanel-services" role="tabpanel" aria-labelledby="tab-services">
        <BookingServices :booking="booking" viewer="staff" :lead="leadCard ?? null" />
      </section>

      <section
        v-if="booking.attachments?.length"
        v-show="tab === 'files'"
        id="tabpanel-files"
        role="tabpanel"
        aria-labelledby="tab-files"
      >
        <PanelSection title="Files">
          <BookingFiles :booking-id="booking.id" :files="booking.attachments" />
        </PanelSection>
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
/* Look B (owner pick, 16 Nov 2026): a small photo by the title, and a one-line warning. */
.room-thumb {
  flex: none;
  width: 56px;
  height: 56px;
  border-radius: 12px;
}
.warn {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 10px 0 0;
  color: var(--color-ink-off);
  font-size: 12px;
  line-height: 1.5;
}
.warn b {
  font-weight: 600;
  color: var(--color-warn);
}
.warn :deep(svg.lucide) {
  flex: none;
  width: 13px;
  height: 13px;
  margin-top: 2px;
  color: var(--color-warn);
}
.tab-bar {
  margin-block: 0 14px;
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
