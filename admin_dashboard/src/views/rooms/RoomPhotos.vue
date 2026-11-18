<script setup lang="ts">
// A room's photos (DSH-R06): upload (JPEG, PNG or WebP, up to 5 MB, at most 20), reorder by
// drag or with buttons, make one the cover, delete with a confirm. The first photo is the cover.
// Look C "Ordered list" (owner pick, 18 Nov 2026): one photo per row with its number.
import { ChevronDown, ChevronUp, CircleAlert, GripVertical, ImagePlus, Star, Trash2 } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import { api, apiBaseUrl } from '../../api'
import { ApiError } from '../../api/errors'
import { deleteRoomPhoto, getRoom, reorderRoomPhotos, uploadRoomPhoto } from '../../api/rooms'
import type { PhotoOut } from '../../api/types'
import { useConfirm } from '../../composables/useConfirm'
import { formatPhnomPenh } from '../../utils/time'

const LIMIT = 20
const ACCEPT = 'image/jpeg,image/png,image/webp'

const props = defineProps<{ roomId: number; photos: PhotoOut[] }>()
const emit = defineEmits<{ change: [photos: PhotoOut[]] }>()

const list = ref<PhotoOut[]>([...props.photos])
watch(
  () => props.photos,
  (photos) => (list.value = [...photos]),
)

const uploading = ref(false)
const problems = ref<string[]>([])
const deleting = ref(false)
const full = computed(() => list.value.length >= LIMIT)
const reordering = ref(false)
// One action at a time: an upload, a reorder and a delete must not overlap.
const busy = computed(() => uploading.value || reordering.value || deleting.value)
const messageOf = (err: unknown) => (err instanceof ApiError ? err.message : 'Something went wrong.')

function publish() {
  emit('change', [...list.value])
}

/** Files go up one after another; a refused file is named, the others still upload. */
async function onFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = [...(input.files ?? [])]
  problems.value = []
  uploading.value = true
  let added = false
  for (const file of files) {
    if (list.value.length >= LIMIT) {
      problems.value.push(`${file.name}: 20 photos is the limit.`)
      continue
    }
    try {
      list.value.push(await uploadRoomPhoto(api, props.roomId, file))
      added = true
    } catch (err) {
      problems.value.push(`${file.name}: ${messageOf(err)}`)
    }
  }
  uploading.value = false
  input.value = ''
  if (added) publish()
}

/**
 * Send the new order. If the server refuses it (someone else added or deleted a photo), show
 * the server's photos instead, so the grid never stays out of step with the room.
 */
async function reorder(next: PhotoOut[]) {
  const before = list.value
  list.value = next
  problems.value = []
  reordering.value = true
  try {
    list.value = (await reorderRoomPhotos(api, props.roomId, next.map((p) => p.id))).items
    publish()
  } catch (err) {
    try {
      list.value = [...(await getRoom(api, props.roomId)).photos].sort((a, b) => a.sort_order - b.sort_order)
      publish()
      problems.value = [
        err instanceof ApiError && err.status === 422 ? 'The photos changed. This is the current order.' : messageOf(err),
      ]
    } catch {
      list.value = before
      problems.value = [messageOf(err)]
    }
  } finally {
    reordering.value = false
  }
}

function move(from: number, to: number) {
  if (busy.value) return
  if (to < 0 || to >= list.value.length || from === to) return
  const next = [...list.value]
  const [photo] = next.splice(from, 1)
  next.splice(to, 0, photo!)
  void reorder(next)
}

/** "Added 23 Oct" ("Added 23 Oct 2025" from another year): the API has no file size, so the row
 *  says when the photo came. */
const thisYear = String(new Date().getFullYear())
function addedOn(p: PhotoOut): string {
  const day = formatPhnomPenh(p.created_at).split(',')[0]!
  return `Added ${day.endsWith(` ${thisYear}`) ? day.slice(0, -5) : day}`
}

const dragging = ref<number | null>(null)
function onDrop(to: number) {
  if (dragging.value !== null) move(dragging.value, to)
  dragging.value = null
}

const { confirm } = useConfirm()

async function askRemove(photo: PhotoOut, index: number) {
  const ok = await confirm({
    title: `Delete photo ${index + 1}?`,
    text: `It is removed from the room${index === 0 ? ', and the next photo becomes the cover' : ''}.`,
    confirmLabel: 'Delete photo',
    icon: 'trash',
  })
  if (ok) await remove(photo)
}

async function remove(photo: PhotoOut) {
  deleting.value = true
  problems.value = []
  try {
    await deleteRoomPhoto(api, props.roomId, photo.id)
    list.value = list.value.filter((p) => p.id !== photo.id)
    publish()
  } catch (err) {
    problems.value = [messageOf(err)]
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="photos">
    <input
      id="room-photos"
      type="file"
      class="sr-only file"
      :accept="ACCEPT"
      multiple
      :disabled="full || busy"
      aria-describedby="room-photos-hint"
      @change="onFiles"
    />
    <label for="room-photos" class="add" :class="{ busy: uploading }" :aria-disabled="full || undefined">
      <span v-if="uploading" class="spin" aria-hidden="true" />
      <ImagePlus v-else aria-hidden="true" />
      <template v-if="uploading">Uploading</template>
      <template v-else-if="full">20 photos is the limit</template>
      <template v-else>Add photos <span class="more">· {{ LIMIT - list.length }} more allowed</span></template>
    </label>

    <div v-if="problems.length" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <ul>
        <li v-for="problem in problems" :key="problem">{{ problem }}</li>
      </ul>
    </div>

    <div class="head" aria-hidden="true">Photos <span class="mono">{{ list.length }} of {{ LIMIT }}</span></div>
    <p v-if="!list.length && !uploading" class="none">No photos yet. The first one you add is the cover.</p>
    <ol v-else class="list">
      <li
        v-for="(p, i) in list"
        :key="p.id"
        class="photo"
        :class="{ dragging: dragging === i, cover: i === 0 }"
        :data-id="p.id"
        :draggable="!busy"
        @dragstart="dragging = busy ? null : i"
        @dragover.prevent
        @drop.prevent="onDrop(i)"
        @dragend="dragging = null"
      >
        <GripVertical class="grip" aria-hidden="true" />
        <span class="num mono">{{ i + 1 }}</span>
        <img :src="`${apiBaseUrl}${p.thumbnail_url}`" :alt="`Photo ${i + 1}`" loading="lazy" />
        <span class="meta">
          <b class="caption"><Star v-if="i === 0" class="star" aria-hidden="true" />{{ i === 0 ? 'Cover' : `Photo ${i + 1}` }}</b>
          <small>{{ addedOn(p) }}</small>
        </span>
        <span class="acts">
          <button type="button" class="icon-btn" aria-label="Move earlier" title="Move earlier" :disabled="busy || i === 0" @click="move(i, i - 1)">
            <ChevronUp aria-hidden="true" />
          </button>
          <button type="button" class="icon-btn" aria-label="Move later" title="Move later" :disabled="busy || i === list.length - 1" @click="move(i, i + 1)">
            <ChevronDown aria-hidden="true" />
          </button>
          <button type="button" class="icon-btn" aria-label="Make cover" title="Make cover" :disabled="busy || i === 0" @click="move(i, 0)">
            <Star aria-hidden="true" />
          </button>
          <button type="button" class="icon-btn red" aria-label="Delete photo" title="Delete photo" :disabled="busy" @click="askRemove(p, i)">
            <Trash2 aria-hidden="true" />
          </button>
        </span>
      </li>
      <li v-if="uploading" class="photo ghost" aria-hidden="true">
        <span class="num" />
        <span class="shine" />
        <span class="meta"><b>Uploading…</b></span>
      </li>
    </ol>
    <p id="room-photos-hint" class="hint">JPEG, PNG or WebP, up to 5 MB each. The first photo is the cover. Drag to reorder.</p>
  </div>
</template>

<style scoped>
.photos {
  display: grid;
  gap: 12px;
}
.add {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  border: 1.5px dashed var(--color-rule-strong);
  border-radius: 12px;
  background: var(--color-paper);
  color: var(--color-intaglio);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition:
    border-color 140ms ease,
    color 140ms ease,
    transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.add:active {
  transform: scale(0.99);
}
@media (hover: hover) and (pointer: fine) {
  .add:hover {
    border-color: var(--color-crimson);
    color: var(--color-crimson);
  }
}
.add svg {
  width: 18px;
  height: 18px;
}
.add .more {
  color: var(--color-ink-off);
  font-weight: 400;
}
.add[aria-disabled='true'] {
  opacity: 0.5;
  cursor: not-allowed;
}
.add.busy {
  cursor: progress;
}
.add .spin {
  width: 14px;
  height: 14px;
  border: 1.5px solid rgba(42, 28, 19, 0.2);
  border-top-color: var(--color-ink);
  border-radius: 50%;
  animation: spin 700ms linear infinite;
}
.file:focus-visible + .add {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
.head {
  display: flex;
  justify-content: space-between;
  margin-bottom: -4px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-ink-off);
}
.head .mono {
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
}
.hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-ink-off);
}
.summary ul {
  margin: 0;
  padding-left: 16px;
}
.none {
  margin: 0;
  color: var(--color-ink-off);
}
.list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.photo {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 6px 6px 6px 4px;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
  background: var(--color-sheet);
  cursor: grab;
  transition:
    border-color 140ms ease,
    opacity 140ms ease;
}
.photo.cover {
  border-color: var(--color-danger-line);
  background: var(--color-crimson-wash);
}
.photo.dragging {
  opacity: 0.4;
}
.grip {
  flex: none;
  width: 16px;
  height: 16px;
  color: var(--color-rule-strong);
}
.num {
  flex: none;
  width: 18px;
  font-size: 12px;
  color: var(--color-ink-off);
  text-align: center;
}
.photo img,
.shine {
  flex: none;
  width: 84px;
  height: 56px;
  border-radius: 8px;
  object-fit: cover;
  background: var(--color-skeleton);
}
.meta {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  font-size: 13px;
}
.caption {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 600;
}
.photo.cover .caption {
  color: var(--color-crimson);
}
.star {
  width: 14px;
  height: 14px;
  fill: currentColor;
}
.meta small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11.5px;
  color: var(--color-ink-off);
}
.acts {
  display: flex;
  flex: none;
  gap: 2px;
}
.acts .icon-btn {
  width: 30px;
  height: 30px;
}
.acts .icon-btn svg {
  width: 17px;
  height: 17px;
}
.acts .icon-btn.red:not([disabled]):hover {
  background: var(--color-crimson-wash);
  color: var(--color-crimson);
}
.acts .icon-btn[disabled] {
  opacity: 0.3;
  cursor: not-allowed;
}
/* A photo on its way up: a soft shine where the picture will be. */
.ghost {
  cursor: default;
}
.ghost .num {
  width: 34px;
}
.shine {
  position: relative;
  overflow: hidden;
}
.shine::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, transparent 20%, rgba(255, 255, 255, 0.6) 50%, transparent 80%);
  transform: translateX(-100%);
  animation: shine 1.1s linear infinite;
}
@keyframes shine {
  to {
    transform: translateX(100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .add,
  .photo {
    transition-duration: 1ms;
  }
  .shine::after {
    animation: none;
  }
}
</style>
