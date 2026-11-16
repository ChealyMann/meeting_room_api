<script setup lang="ts">
// One IT setup in the side panel (spec Part B, "Panel"): the room photo, the booking's full
// process bar, then the same tabs as the other booking pop-ups (owner pick, 16 Nov 2026):
// Details, Food & IT, Files, Approvals. It opens on Food & IT, where IT's work is. The IT card
// takes the ticket from the list, so a new assign shows at once. The times are the meeting's
// only. The foot has Close and the row's buttons.
import { Check } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import type { BookingDetail, ITTicketItem } from '../../api/types'
import ApprovedBy from '../../components/ApprovedBy.vue'
import BaseButton from '../../components/base/BaseButton.vue'
import BookingDetails from '../../components/BookingDetails.vue'
import BookingFiles from '../../components/BookingFiles.vue'
import BookingServices from '../../components/BookingServices.vue'
import BookingTabs from '../../components/BookingTabs.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ProcessBar from '../../components/ProcessBar.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { approvedBy } from '../../utils/approvals'
import { buildHistory } from '../../utils/bookingHistory'
import { hasSessionAhead } from '../../utils/itQueue'

const props = defineProps<{
  ticket: ITTicketItem
  /** The full booking (process bar, food, approvals, files), or null while it loads or when it failed. */
  detail: BookingDetail | null
  photo: string | null
  place: string | null
  actions: boolean
}>()
const emit = defineEmits<{ close: []; assign: []; ready: [] }>()

const b = computed(() => props.ticket.booking)
const steps = computed(() => (props.detail ? buildHistory(props.detail).steps : []))
const isOpen = computed(() => !props.ticket.missed && props.ticket.status !== 'READY')
/** Staff can be assigned or changed while sessions remain, even on a confirmed booking. */
const canStaff = computed(() => isOpen.value || hasSessionAhead(props.ticket, new Date()))
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

type Tab = 'details' | 'services' | 'files' | 'approvals'
const tab = ref<Tab>('services')
const count = (n: number) => (n ? ` ${n}` : '')
const files = computed(() => props.detail?.attachments ?? [])
const tabs = computed(() => {
  const list: Array<{ id: Tab; label: string }> = [
    { id: 'details', label: 'Details' },
    { id: 'services', label: `Food & IT${count((props.detail?.catering?.packages.length ?? 0) + props.ticket.items.length)}` },
  ]
  if (files.value.length) list.push({ id: 'files', label: `Files${count(files.value.length)}` })
  list.push({ id: 'approvals', label: `Approvals${count(props.detail ? approvedBy(props.detail).length : 0)}` })
  return list
})
</script>

<template>
  <SidePanel :open="true" :title="b.meeting_title" :subtitle="subtitle" :serial="b.reference_code" @close="emit('close')">
    <div class="it-panel">
      <figure class="hero">
        <RoomPhoto class="photo" :path="photo" :alt="b.room.name_en" />
        <figcaption>
          <span class="kh">{{ b.room.name_kh }}</span>
          <span>{{ b.room.name_en }}<template v-if="place"> · {{ place }}</template></span>
        </figcaption>
      </figure>

      <ProcessBar v-if="steps.length" :steps="steps" size="large" />

      <BookingTabs v-model="tab" :tabs="tabs" class="tab-bar" />

      <section v-show="tab === 'details'" id="tabpanel-details" role="tabpanel" aria-labelledby="tab-details">
        <BookingDetails v-if="detail" :booking="detail" />
        <p v-else class="none">Loading…</p>
      </section>

      <section v-show="tab === 'services'" id="tabpanel-services" role="tabpanel" aria-labelledby="tab-services">
        <BookingServices :booking="services" viewer="staff" :food="!!detail" />
      </section>

      <section v-if="files.length && detail" v-show="tab === 'files'" id="tabpanel-files" role="tabpanel" aria-labelledby="tab-files">
        <BookingFiles :booking-id="detail.id" :files="files" />
      </section>

      <section v-show="tab === 'approvals'" id="tabpanel-approvals" role="tabpanel" aria-labelledby="tab-approvals">
        <ApprovedBy v-if="detail" :booking="detail" />
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
.tab-bar {
  margin-block: 16px 14px;
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
