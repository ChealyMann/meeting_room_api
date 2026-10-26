<script setup lang="ts">
// A room's photos (DSH-R06): upload (JPEG, PNG or WebP, up to 5 MB, at most 20), reorder by
// drag or with buttons, delete with a confirm. The first photo is the cover.
import { ArrowLeft, ArrowRight, CircleAlert, ImagePlus, Trash2 } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import { api, apiBaseUrl } from '../../api'
import { ApiError } from '../../api/errors'
import { deleteRoomPhoto, reorderRoomPhotos, uploadRoomPhoto } from '../../api/rooms'
import type { PhotoOut } from '../../api/types'
import { useConfirm } from '../../composables/useConfirm'

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

/** Send the new order; if the server refuses, put the old order back and say why. */
async function reorder(next: PhotoOut[]) {
  const before = list.value
  list.value = next
  problems.value = []
  try {
    list.value = (await reorderRoomPhotos(api, props.roomId, next.map((p) => p.id))).items
    publish()
  } catch (err) {
    list.value = before
    problems.value = [messageOf(err)]
  }
}

function move(from: number, to: number) {
  if (to < 0 || to >= list.value.length || from === to) return
  const next = [...list.value]
  const [photo] = next.splice(from, 1)
  next.splice(to, 0, photo!)
  void reorder(next)
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
    <div class="toolbar">
      <input
        id="room-photos"
        type="file"
        class="sr-only file"
        :accept="ACCEPT"
        multiple
        :disabled="full || uploading"
        aria-describedby="room-photos-hint"
        @change="onFiles"
      />
      <label for="room-photos" class="btn" :class="{ busy: uploading }" :aria-disabled="full || undefined">
        <span v-if="uploading" class="spin" aria-hidden="true" />
        <ImagePlus v-else aria-hidden="true" />
        {{ uploading ? 'Uploading' : full ? '20 photos is the limit' : 'Add photos' }}
      </label>
      <span class="mono counter">{{ list.length }}/{{ LIMIT }}</span>
    </div>
    <p id="room-photos-hint" class="hint">
      JPEG, PNG or WebP, up to 5 MB each. The first photo is the cover. Drag to reorder.
    </p>

    <div v-if="problems.length" class="summary" role="alert">
      <CircleAlert aria-hidden="true" />
      <ul>
        <li v-for="problem in problems" :key="problem">{{ problem }}</li>
      </ul>
    </div>

    <p v-if="!list.length" class="none">No photos yet.</p>
    <ol v-else class="grid">
      <li
        v-for="(p, i) in list"
        :key="p.id"
        class="photo"
        :class="{ dragging: dragging === i }"
        :data-id="p.id"
        draggable="true"
        @dragstart="dragging = i"
        @dragover.prevent
        @drop.prevent="onDrop(i)"
        @dragend="dragging = null"
      >
        <img :src="`${apiBaseUrl}${p.thumbnail_url}`" :alt="`Photo ${i + 1}`" loading="lazy" />
        <div class="bar">
          <span class="caption">{{ i === 0 ? 'Cover' : `${i + 1}` }}</span>
          <button type="button" class="icon-btn" aria-label="Move earlier" :disabled="i === 0" @click="move(i, i - 1)">
            <ArrowLeft aria-hidden="true" />
          </button>
          <button type="button" class="icon-btn" aria-label="Move later" :disabled="i === list.length - 1" @click="move(i, i + 1)">
            <ArrowRight aria-hidden="true" />
          </button>
          <button type="button" class="icon-btn" aria-label="Delete photo" :disabled="deleting" @click="askRemove(p, i)">
            <Trash2 aria-hidden="true" />
          </button>
        </div>
      </li>
    </ol>

  </div>
</template>

<style scoped>
.photos {
  display: grid;
  gap: 10px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.toolbar label[aria-disabled='true'] {
  opacity: 0.45;
  cursor: not-allowed;
}
.file:focus-visible + label {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
.counter {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-intaglio);
}
.hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
.summary ul {
  margin: 0;
  padding-left: 16px;
}
.none {
  color: var(--color-ink-off);
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}
/* min-width 0 and a minmax column let the cell shrink to its grid column; without them the
   image's natural width pushes the cell wider and it spills over its neighbour. */
.photo {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 4px;
  min-width: 0;
  cursor: grab;
}
.photo.dragging {
  opacity: 0.5;
}
.photo img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border: 1px solid var(--color-rule);
  border-radius: 8px;
  background: var(--color-skeleton);
}
.bar {
  display: flex;
  align-items: center;
  gap: 2px;
}
.caption {
  margin-right: auto;
  font-size: 12px;
  color: var(--color-intaglio);
}
.photo:first-child .caption {
  color: var(--color-crimson);
  font-weight: 500;
}
.bar .icon-btn {
  width: 28px;
  height: 28px;
}
.bar .icon-btn[disabled] {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
