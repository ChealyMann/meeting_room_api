<script setup lang="ts">
// One IT setup in the side panel (spec Part B, "Panel"): a small room photo by the title and the
// booking's thin step bar (look B), then the same tabs as the other booking pop-ups (16 Nov 2026):
// Details, Food & IT, Files, History. It opens on Food & IT, where IT's work is. The IT card
// takes the ticket from the list, so a new assign shows at once. The times are the meeting's
// only. The foot has Close and the row's buttons.
import { Check } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import type { BookingDetail, ITTicketItem } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import BookingDetails from '../../components/BookingDetails.vue'
import BookingFiles from '../../components/BookingFiles.vue'
import BookingHistory from '../../components/BookingHistory.vue'
import BookingServices from '../../components/BookingServices.vue'
import BookingTabs from '../../components/BookingTabs.vue'
import PanelSection from '../../components/PanelSection.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import StepProgress from '../../components/StepProgress.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { buildHistory } from '../../utils/bookingHistory'
import { hasSessionAhead } from '../../utils/itQueue'

const props = defineProps<{
  ticket: ITTicketItem
  /** The full booking (process bar, details, food, history, files), or null while it loads or when it failed. */
  detail: BookingDetail | null
  photo: string | null
  place: string | null
  actions: boolean
}>()
const emit = defineEmits<{ close: []; assign: []; ready: [] }>()

const b = computed(() => props.ticket.booking)
const steps = computed(() => (live.value ? buildHistory(live.value).steps : []))
const isOpen = computed(() => !props.ticket.missed && props.ticket.status !== 'READY')
/** Staff can be assigned or changed while sessions remain, even on a confirmed booking. */
/** The room line by the photo: Khmer name, name, and where it is. */
const room = computed(() => [b.value.room.name_kh, b.value.room.name_en, props.place].filter(Boolean).join(' · '))
const canStaff = computed(() => isOpen.value || hasSessionAhead(props.ticket, new Date()))
/** Where the setup is, beside the step bar. */
const subtitle = computed(() => {
  if (props.ticket.missed) return 'Missed · not marked ready'
  if (props.ticket.status === 'READY') return 'Ready'
  return props.ticket.staff.length ? 'Staff set · not ready' : 'Needs staff'
})

/** The booking for the Food & IT cards, with IT from the ticket (the list is the freshest). */
const services = computed(() => {
  const t = props.ticket
  const it = {
    ticket_id: t.id,
    items: t.items,
    special_requirements: t.special_requirements,
    status: t.status,
    technician_notes: t.technician_notes,
    staff: t.staff,
    setup_date: t.setup_date,
    setup_time: t.setup_time,
    forwarded_at: t.forwarded_at,
    assigned_at: t.assigned_at,
    ready_at: t.ready_at,
  }
  const d = props.detail
  return d ? { ...d, it } : { display_status: b.value.display_status, sessions: [], catering: null, it }
})
/** The full booking with IT from the ticket, for the History timeline. */
const live = computed(() => (props.detail ? { ...props.detail, it: services.value.it } : null))

type Tab = 'details' | 'services' | 'files' | 'history'
const tab = ref<Tab>('services')
const count = (n: number) => (n ? ` ${n}` : '')
const files = computed(() => props.detail?.attachments ?? [])
const tabs = computed(() => {
  const list: Array<{ id: Tab; label: string }> = [
    { id: 'details', label: 'Details' },
    { id: 'services', label: `Food & IT${count((props.detail?.catering?.packages.length ?? 0) + props.ticket.items.length)}` },
  ]
  if (files.value.length) list.push({ id: 'files', label: `Files${count(files.value.length)}` })
  list.push({ id: 'history', label: 'History' })
  return list
})
</script>

<template>
  <SidePanel :open="true" :title="b.meeting_title" :subtitle="room" :serial="b.reference_code" @close="emit('close')">
    <template #lead><RoomPhoto class="room-thumb" :path="photo" :alt="b.room.name_en" /></template>
    <div class="it-panel">
      <StepProgress v-if="steps.length" :steps="steps" :label="subtitle" />

      <BookingTabs v-model="tab" :tabs="tabs" class="tab-bar" />

      <section v-show="tab === 'details'" id="tabpanel-details" role="tabpanel" aria-labelledby="tab-details">
        <BookingDetails v-if="detail" :booking="detail" />
        <p v-else class="none">Loading…</p>
      </section>

      <section v-show="tab === 'services'" id="tabpanel-services" role="tabpanel" aria-labelledby="tab-services">
        <BookingServices :booking="services" viewer="staff" :food="!!detail" />
      </section>

      <section v-if="files.length && detail" v-show="tab === 'files'" id="tabpanel-files" role="tabpanel" aria-labelledby="tab-files">
        <PanelSection title="Files"><BookingFiles :booking-id="detail.id" :files="files" /></PanelSection>
      </section>

      <section v-show="tab === 'history'" id="tabpanel-history" role="tabpanel" aria-labelledby="tab-history">
        <PanelSection v-if="live" title="History"><BookingHistory :booking="live" :bar="false" /></PanelSection>
        <p v-else class="none">Loading…</p>
      </section>
    </div>

    <template #foot>
      <div class="foot">
        <BaseButton variant="quiet" @click="emit('close')">Close</BaseButton>
        <template v-if="actions && canStaff">
          <span class="spacer" />
          <BaseButton v-if="ticket.status === 'RECEIVED'" variant="primary" @click="emit('assign')">Assign staff</BaseButton>
          <template v-else>
            <BaseButton variant="quiet" @click="emit('assign')">Change staff</BaseButton>
            <BaseButton v-if="isOpen" variant="primary" @click="emit('ready')"><Check aria-hidden="true" />Mark ready</BaseButton>
          </template>
        </template>
      </div>
    </template>
  </SidePanel>
</template>

<style scoped>
/* Look B (owner pick, 16 Nov 2026): a small photo by the title. */
.room-thumb {
  flex: none;
  width: 56px;
  height: 56px;
  border-radius: 12px;
}
.tab-bar {
  margin-block: 0 14px;
}
.none {
  color: var(--color-ink-off);
}
.foot {
  display: flex;
  flex: 1;
  gap: 8px;
}
.spacer {
  flex: 1;
}
</style>
