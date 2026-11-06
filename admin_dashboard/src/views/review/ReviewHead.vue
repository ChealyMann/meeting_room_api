<script setup lang="ts">
// The To review head (spec 2026-11-05-pitika-decided-design, "Head"): today's ring, the title,
// one calm line, and the Waiting / Approved / Rejected switch with today's numbers. Drawn by
// QueueHead, like the IT setup head.
import { computed } from 'vue'

import type { PitikaSummary } from '../../api/types'
import QueueHead, { type HeadRing, type HeadTab } from '../../components/QueueHead.vue'
import { ringArcs, summaryLine, type Tab } from '../../utils/decided'

const props = withDefaults(defineProps<{ summary: PitikaSummary | null; tab: Tab; title?: string }>(), { title: 'To review' })
const emit = defineEmits<{ select: [Tab] }>()

const ring = computed<HeadRing | null>(() => {
  if (!props.summary) return null
  const arcs = ringArcs(props.summary)
  const [decided, whole] = arcs.label.split('/')
  return {
    parts: [
      { value: arcs.approved, tone: 'ok' },
      { value: arcs.rejected, tone: 'no' },
    ],
    label: arcs.label,
    spoken: `${decided} of ${whole} decided today`,
  }
})
const tabs = computed<HeadTab[]>(() => {
  const s = props.summary
  return [
    { key: 'waiting', label: 'Waiting', count: s ? s.waiting : null },
    { key: 'approved', label: 'Approved', count: s ? s.approved_today : null },
    { key: 'rejected', label: 'Rejected', count: s ? s.rejected_today : null },
  ]
})
</script>

<template>
  <QueueHead
    :title="title"
    :line="summary ? summaryLine(summary) : null"
    :ring="ring"
    :tabs="tabs"
    :tab="tab"
    @select="emit('select', $event as Tab)"
  />
</template>
