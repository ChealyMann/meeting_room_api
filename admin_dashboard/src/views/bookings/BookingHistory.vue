<script setup lang="ts">
// The History tab of a booking (owner decisions, 5 Nov 2026): the route's steps as a process
// bar, then a timeline of what happened. Each step shows its action in its colour (green
// approved, crimson rejected or cancelled, amber waiting), who did it, and their role as plain
// text with a small icon; the Admin's role is crimson so a stand-in shows.
import {
  CalendarCheck,
  CalendarX2,
  Check,
  CircleCheck,
  CircleMinus,
  CircleX,
  ClipboardCheck,
  Clock,
  DoorOpen,
  Flag,
  Hourglass,
  Mail,
  Monitor,
  RefreshCw,
  UserCog,
  UserRound,
  Users,
  Wrench,
  X,
} from 'lucide-vue-next'
import { computed, type Component } from 'vue'

import type { BookingDetail } from '../../api/types'
import { buildHistory, ROLE_LABELS, type EventKind, type RoleKey } from '../../utils/bookingHistory'

const props = defineProps<{ booking: BookingDetail }>()
const history = computed(() => buildHistory(props.booking))

const KIND: Record<EventKind, { icon: Component; tone: 'neutral' | 'ok' | 'stop' | 'wait' }> = {
  sent: { icon: Mail, tone: 'neutral' },
  approved: { icon: CircleCheck, tone: 'ok' },
  rejected: { icon: CircleX, tone: 'stop' },
  expired: { icon: Hourglass, tone: 'stop' },
  cancelled: { icon: CalendarX2, tone: 'stop' },
  skipped: { icon: CircleMinus, tone: 'neutral' },
  toIT: { icon: Monitor, tone: 'neutral' },
  assigned: { icon: Users, tone: 'neutral' },
  ready: { icon: CircleCheck, tone: 'ok' },
  confirmed: { icon: CalendarCheck, tone: 'ok' },
  ended: { icon: Flag, tone: 'neutral' },
  waiting: { icon: Clock, tone: 'wait' },
}
// Role icons chosen by the owner, 5 Nov 2026.
const ROLE_ICON: Record<RoleKey, Component> = {
  booker: UserRound,
  pitika: ClipboardCheck,
  owner: DoorOpen,
  it: Wrench,
  system: RefreshCw,
  admin: UserCog,
}
</script>

<template>
  <div class="history">
    <ol class="steps" aria-label="Steps">
      <li v-for="(s, i) in history.steps" :key="i" class="step" :class="s.state">
        <span class="c" aria-hidden="true">
          <Check v-if="s.state === 'done'" />
          <X v-else-if="s.state === 'stop'" />
          <Clock v-else-if="s.state === 'now'" />
        </span>
        <span class="n">{{ s.label }}</span>
        <span class="sr-only">{{ { done: ', done', stop: ', stopped here', now: ', now', todo: ', not yet' }[s.state] }}</span>
      </li>
    </ol>

    <ol class="timeline">
      <li v-for="(e, i) in history.events" :key="i" :class="`t-${KIND[e.kind].tone}`">
        <span class="dot" aria-hidden="true"><component :is="KIND[e.kind].icon" /></span>
        <div class="body">
          <div class="line1">
            <b class="label">{{ e.label }}</b>
            <span v-if="e.at" class="time">{{ e.at }}</span>
          </div>
          <div v-if="e.name || e.role" class="who">
            <template v-if="e.name">
              <span class="name">{{ e.name }}</span>
              <span v-if="e.role" class="sep" aria-hidden="true">·</span>
            </template>
            <span v-if="e.role" class="role" :class="{ admin: e.role === 'admin' }">
              <component :is="ROLE_ICON[e.role]" aria-hidden="true" />{{ ROLE_LABELS[e.role] }}
            </span>
            <template v-if="e.forRole">
              <span class="for">for</span>
              <span class="role"><component :is="ROLE_ICON[e.forRole]" aria-hidden="true" />{{ ROLE_LABELS[e.forRole] }}</span>
            </template>
          </div>
          <p v-if="e.note" class="note">{{ e.note }}</p>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.history {
  --wash-ok: color-mix(in srgb, var(--color-ok) 10%, var(--color-sheet));
  --wash-warn: color-mix(in srgb, var(--color-warn) 10%, var(--color-sheet));
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

/* The process bar: where the booking is, at a glance. */
.steps {
  display: flex;
  margin: 0 0 20px;
  padding: 14px 8px 12px;
  list-style: none;
  border-radius: 10px;
  background: var(--color-paper);
}
.step {
  position: relative;
  flex: 1;
  min-width: 0;
  display: grid;
  justify-items: center;
  gap: 6px;
  text-align: center;
}
.step:not(:first-child)::before {
  content: '';
  position: absolute;
  top: 13px;
  right: 50%;
  width: 100%;
  height: 2px;
  background: var(--color-rule-strong);
}
.step:is(.done, .stop, .now):not(:first-child)::before {
  background: var(--color-ok);
}
.step .c {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 2px solid var(--color-rule-strong);
  border-radius: 50%;
  background: var(--color-sheet);
  color: var(--color-ink-off);
}
.step.done .c {
  border-color: var(--color-ok);
  background: var(--color-ok);
  color: var(--color-sheet);
}
.step.stop .c {
  border-color: var(--color-crimson);
  background: var(--color-crimson);
  color: var(--color-sheet);
}
.step.now .c {
  border-color: var(--color-warn);
  border-style: dashed;
  background: var(--wash-warn);
  color: var(--color-warn);
}
.step .c :deep(svg.lucide) {
  width: 14px;
  height: 14px;
  stroke-width: 2.25;
}
.step .n {
  font-size: 11px;
  line-height: 1.25;
  color: var(--color-intaglio);
  overflow-wrap: anywhere;
}
.step.done .n {
  color: var(--color-ink);
}
.step.stop .n {
  color: var(--color-crimson);
  font-weight: 500;
}
.step.now .n {
  color: var(--color-warn);
  font-weight: 500;
}

/* The timeline: every step, who did it, their role, and when. */
.t-neutral {
  --tone: var(--color-intaglio);
  --wash: var(--color-paper);
  --edge: var(--color-rule-strong);
}
.t-ok {
  --tone: var(--color-ok);
  --wash: var(--wash-ok);
  --edge: color-mix(in srgb, var(--color-ok) 25%, transparent);
}
.t-stop {
  --tone: var(--color-crimson);
  --wash: var(--color-crimson-wash);
  --edge: var(--color-danger-line);
}
.t-wait {
  --tone: var(--color-warn);
  --wash: var(--wash-warn);
  --edge: var(--color-warn);
}
.timeline {
  margin: 0;
  padding: 0;
  list-style: none;
}
.timeline li {
  position: relative;
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 12px;
  padding-bottom: 16px;
}
.timeline li:last-child {
  padding-bottom: 0;
}
.timeline li:not(:last-child)::before {
  content: '';
  position: absolute;
  top: 34px;
  bottom: 2px;
  left: 15.5px;
  width: 1px;
  background: var(--color-rule-strong);
}
.dot {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--edge);
  border-radius: 50%;
  background: var(--wash);
  color: var(--tone);
}
.t-wait .dot {
  border-style: dashed;
}
.dot :deep(svg.lucide) {
  width: 16px;
  height: 16px;
  stroke-width: 1.75;
}
.line1 {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  padding-top: 5px;
}
.label {
  font-weight: 600;
  color: var(--tone);
}
.t-neutral .label {
  color: var(--color-ink);
}
.time {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-intaglio);
  white-space: nowrap;
}
.who {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 2px;
  font-size: 13px;
  line-height: 1.6;
}
.sep {
  margin: 0 7px;
  color: var(--color-rule-strong);
}
.role {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--color-intaglio);
  white-space: nowrap;
}
.role :deep(svg.lucide) {
  width: 13px;
  height: 13px;
  stroke-width: 1.75;
}
.role.admin {
  color: var(--color-crimson);
}
.for {
  margin: 0 5px;
  font-size: 12.5px;
  color: var(--color-intaglio);
}
.note {
  margin: 6px 0 0;
  padding: 7px 10px;
  border-radius: 8px;
  background: var(--color-paper);
  font-size: 13px;
  white-space: pre-line;
  overflow-wrap: anywhere;
}
</style>
