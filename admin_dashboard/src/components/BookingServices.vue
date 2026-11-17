<script setup lang="ts">
// Food & IT (owner pick, 16 Nov 2026): one card each, with every item, the booker's note, and the
// answer. Food is checked by Pitika when they approve; IT moves from received to the room being
// ready. The same cards in My bookings, To review (Pitika and the room owner) and IT setup.
import { MapPin } from 'lucide-vue-next'
import { computed } from 'vue'

import type { BookingDetail } from '../api/types'
import { formatDay, formatPhnomPenh } from '../utils/time'
import PanelSection from './PanelSection.vue'

const props = withDefaults(
  defineProps<{
    booking: Pick<BookingDetail, 'display_status' | 'sessions' | 'catering' | 'it'>
    /** Who looks: the booker reads "Your note", everyone else "Booker’s note". */
    viewer: 'booker' | 'staff'
    /** False while the food is not known yet (IT's panel before the booking loads). */
    food?: boolean
    /** IT help on top (the IT setup panel, owner pick 16 Nov 2026); food first everywhere else. */
    itFirst?: boolean
    /** The card the reader checks, on a light background: food for Pitika, IT for IT. */
    lead?: 'food' | 'it' | null
    /** Where to set up, on top of the IT card (IT's panel only, owner pick 17 Nov 2026). */
    setupAt?: { place: string; area: string } | null
  }>(),
  { food: true, itFirst: false, lead: null, setupAt: null },
)
/** The cards in the order they show (and are read). */
const order = computed(() => {
  const kinds: Array<'food' | 'it'> = props.itFirst ? ['it', 'food'] : ['food', 'it']
  return kinds.filter((k) => k === 'it' || props.food)
})

const OPEN = ['PENDING_PITIKA', 'PENDING_OWNER', 'SETUP_IN_PROGRESS', 'CONFIRMED']
const open = computed(() => OPEN.includes(props.booking.display_status))
const noteLabel = computed(() => (props.viewer === 'booker' ? 'Your note' : 'Booker’s note'))
const sessionCount = computed(() => props.booking.sessions.length)
const hhmm = (time: string) => time.slice(0, 5)

type Pill = { text: string; tone: 'ok' | 'wait' }
const foodPill = computed<Pill | null>(() => {
  const c = props.booking.catering
  if (!c) return null
  if (c.decided_at) return { text: 'Approved', tone: 'ok' }
  return open.value ? { text: 'Waiting', tone: 'wait' } : null
})
const itPill = computed<Pill | null>(() => {
  const it = props.booking.it
  if (!it) return null
  if (it.status === 'READY') return { text: 'Room ready', tone: 'ok' }
  if (!open.value) return null
  if (it.status === 'ASSIGNED') return { text: 'Setting up', tone: 'wait' }
  return { text: it.forwarded_at ? 'Sent to IT' : 'Waiting', tone: 'wait' }
})
</script>

<template>
  <div class="svc">
    <template v-for="kind in order" :key="kind">
      <template v-if="kind === 'food'">
        <PanelSection v-if="booking.catering" title="Food & drinks" class="svc-card" :class="{ lead: lead === 'food' }" data-kind="food">
          <template v-if="foodPill" #extra><span class="pill" :class="foodPill.tone">{{ foodPill.text }}</span></template>
          <ul class="svc-items">
            <li v-for="p in booking.catering.packages" :key="String(p.id)">{{ p.name }}</li>
          </ul>
          <dl class="svc-rows">
            <div>
              <dt>Bring it at</dt>
              <dd v-if="sessionCount > 1" class="delivery">The start of every session ({{ sessionCount }} times)</dd>
              <dd v-else>{{ formatDay(booking.catering.delivery_date) }} · <span class="mono">{{ hhmm(booking.catering.delivery_time) }}</span></dd>
            </div>
            <div v-if="booking.catering.remarks">
              <dt>{{ noteLabel }}</dt>
              <dd class="quote">“{{ booking.catering.remarks }}”</dd>
            </div>
            <div v-if="booking.catering.decided_by && booking.catering.decided_at">
              <dt>Checked by</dt>
              <dd>
                {{ booking.catering.decided_by.name_en }} · <span class="mono">{{ formatPhnomPenh(booking.catering.decided_at) }}</span>
                <span v-if="booking.catering.approver_notes" class="sub quote">“{{ booking.catering.approver_notes }}”</span>
              </dd>
            </div>
          </dl>
        </PanelSection>
        <PanelSection v-else title="Food & drinks"><p class="none-line">No food ordered.</p></PanelSection>
      </template>
  
      <template v-else>
        <PanelSection v-if="booking.it" title="IT help" class="svc-card" :class="{ lead: lead === 'it' }" data-kind="it">
          <template v-if="itPill" #extra><span class="pill" :class="itPill.tone">{{ itPill.text }}</span></template>
          <p v-if="setupAt" class="setup-at">
            <MapPin :size="16" aria-hidden="true" />
            <span>Set up at {{ setupAt.place }}<span class="area">{{ setupAt.area }}</span></span>
          </p>
          <ul class="svc-items">
            <li v-for="x in booking.it.items" :key="String(x.id)">{{ x.name }}</li>
          </ul>
          <dl class="svc-rows">
            <div v-if="booking.it.special_requirements">
              <dt>{{ noteLabel }}</dt>
              <dd class="quote">“{{ booking.it.special_requirements }}”</dd>
            </div>
            <div v-if="booking.it.staff.length">
              <dt>IT staff</dt>
              <dd>{{ booking.it.staff.map((s) => s.name_en).join(', ') }}</dd>
            </div>
            <div v-if="booking.it.technician_notes">
              <dt>IT note</dt>
              <dd class="quote">“{{ booking.it.technician_notes }}”</dd>
            </div>
            <div v-if="booking.it.ready_at">
              <dt>Ready at</dt>
              <dd class="mono">{{ formatPhnomPenh(booking.it.ready_at) }}</dd>
            </div>
          </dl>
        </PanelSection>
        <PanelSection v-else title="IT help"><p class="none-line">No IT help asked.</p></PanelSection>
      </template>
    </template>
  </div>
</template>

<style scoped>
/* The card the reader works on (IT help for IT): a light wash so it stands out. */
.svc-card.lead {
  border-color: color-mix(in srgb, var(--color-intaglio) 18%, var(--color-rule));
  background: var(--color-paper);
}
.pill {
  letter-spacing: 0;
  text-transform: none;
  flex: none;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
  white-space: nowrap;
}
.pill.ok {
  background: color-mix(in srgb, var(--color-ok) 12%, var(--color-sheet));
  color: var(--color-ok);
}
.pill.wait {
  background: color-mix(in srgb, var(--color-warn) 12%, var(--color-sheet));
  color: var(--color-warn);
}
/* "Set up at": one white line on the light IT card, with a pin. */
.setup-at {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  gap: 10px;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--color-rule);
  border-radius: 10px;
  background: var(--color-sheet);
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
.setup-at svg {
  margin-top: 2px;
  color: var(--color-intaglio);
}
.setup-at .area {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.svc-items {
  margin: 0;
  padding: 0;
  list-style: none;
}
.svc-items li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
.svc-items li + li {
  border-top: 1px solid var(--color-rule);
}
.svc-rows {
  display: grid;
  margin: 0;
}
.svc-rows > div {
  display: grid;
  grid-template-columns: 116px minmax(0, 1fr);
  gap: 12px;
  padding: 8px 0;
  border-top: 1px solid var(--color-rule);
}
.svc-rows dt {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.svc-rows dd {
  margin: 0;
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
.quote {
  color: var(--color-intaglio);
  white-space: pre-line;
}
.sub {
  display: block;
  margin-top: 2px;
  font-size: 12.5px;
}
.none-line {
  margin: 0;
  font-size: 13px;
  color: var(--color-ink-off);
}
@media (max-width: 420px) {
  .svc-rows > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
