<script setup lang="ts">
// One booking waiting for the Pitika (spec 2026-11-05-pitika-review-design, "The side panel"):
// the room's photo, the full process bar, what is special about it, the meeting, the food and
// the IT help, then Reject and Approve. Decisions happen in the page's confirm pop-up.
import { Check, TriangleAlert } from 'lucide-vue-next'
import { computed } from 'vue'

import type { BookingDetail } from '../../api/types'
import BaseButton from '../../components/base/BaseButton.vue'
import SidePanel from '../../components/base/SidePanel.vue'
import ProcessBar from '../../components/ProcessBar.vue'
import RoomPhoto from '../../components/RoomPhoto.vue'
import { MEETING_TYPE_LABELS, ROUTE_LABELS } from '../../utils/bookingLabels'
import { buildHistory } from '../../utils/bookingHistory'
import { formatDay } from '../../utils/time'

const props = defineProps<{
  booking: BookingDetail
  /** The room's cover photo (full size), or null. */
  photoPath: string | null
  /** "Starts in …" for a booking starting today, else null. */
  startsIn: string | null
}>()
const emit = defineEmits<{ close: []; approve: []; reject: [] }>()

const steps = computed(() => buildHistory(props.booking).steps)
const hhmm = (time: string) => time.slice(0, 5)
const names = (list: Array<Record<string, unknown>>) => list.map((x) => String(x.name)).join(', ')
const info = (key: string) => (props.booking.requester_info[key] as string | null | undefined) || null
const first = computed(() => props.booking.sessions[0] ?? props.booking.first_session)
</script>

<template>
  <SidePanel
    :open="true"
    :title="booking.meeting_title"
    subtitle="Waiting for Pitika"
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

      <p v-if="startsIn" class="note">
        <TriangleAlert aria-hidden="true" />
        <span>{{ startsIn }}. If nobody decides before it starts, it is rejected by the system.</span>
      </p>
      <p v-if="booking.route === 'R4'" class="note">
        <TriangleAlert aria-hidden="true" />
        <span>The owner books their own room: you check the food and IT only.</span>
      </p>

      <h3>Meeting</h3>
      <dl class="details">
        <div>
          <dt>When</dt>
          <dd>
            {{ formatDay(first.date) }} · <span class="mono">{{ hhmm(first.start_time) }}–{{ hhmm(first.end_time) }}</span>
            <template v-if="booking.session_count > 1"> +{{ booking.session_count - 1 }} more sessions</template>
          </dd>
        </div>
        <div><dt>Meeting type</dt><dd>{{ MEETING_TYPE_LABELS[booking.meeting_type] ?? booking.meeting_type }}</dd></div>
        <div><dt>Attendees</dt><dd class="mono">{{ booking.attendees }}</dd></div>
        <div><dt>Purpose</dt><dd class="wrap" :class="{ none: !booking.meeting_purpose }">{{ booking.meeting_purpose || 'None' }}</dd></div>
        <div><dt>Route</dt><dd>{{ ROUTE_LABELS[booking.route] ?? booking.route }}</dd></div>
        <div v-if="booking.route === 'R2'">
          <dt>Why private</dt>
          <dd class="wrap" :class="{ none: !booking.private_justification }">{{ booking.private_justification || 'No reason given' }}</dd>
        </div>
        <div>
          <dt>Booker</dt>
          <dd>
            {{ info('name_en') ?? booking.requester.name_en }}
            <span v-if="info('division')" class="sub">{{ info('division') }}</span>
          </dd>
        </div>
      </dl>

      <h3>Food</h3>
      <p v-if="!booking.catering" class="none">No food ordered.</p>
      <dl v-else class="details">
        <div><dt>Packages</dt><dd>{{ names(booking.catering.packages) }}</dd></div>
        <div><dt>Servings</dt><dd class="mono">{{ booking.catering.servings }}</dd></div>
        <div>
          <dt>Delivery</dt>
          <dd>{{ formatDay(booking.catering.delivery_date) }} · <span class="mono">{{ hhmm(booking.catering.delivery_time) }}</span></dd>
        </div>
        <div><dt>Remarks</dt><dd class="wrap" :class="{ none: !booking.catering.remarks }">{{ booking.catering.remarks || 'None' }}</dd></div>
      </dl>

      <h3>IT help</h3>
      <p v-if="!booking.it" class="none">No IT help asked.</p>
      <dl v-else class="details">
        <div><dt>Items</dt><dd>{{ names(booking.it.items) }}</dd></div>
        <div>
          <dt>Special needs</dt>
          <dd class="wrap" :class="{ none: !booking.it.special_requirements }">{{ booking.it.special_requirements || 'None' }}</dd>
        </div>
      </dl>
    </div>

    <template #foot>
      <div class="foot">
        <BaseButton variant="quiet" @click="emit('close')">Close</BaseButton>
        <span class="spacer" />
        <BaseButton variant="danger" @click="emit('reject')">Reject</BaseButton>
        <BaseButton variant="primary" @click="emit('approve')"><Check aria-hidden="true" />Approve</BaseButton>
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
.details {
  margin: 0;
}
.details > div {
  display: grid;
  grid-template-columns: 116px minmax(0, 1fr);
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-rule);
}
.details dt {
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.details dd {
  margin: 0;
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
.wrap {
  white-space: pre-line;
}
.none {
  margin: 0;
  color: var(--color-ink-off);
  font-size: 13px;
}
.sub {
  display: block;
  font-size: 12.5px;
  color: var(--color-intaglio);
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
