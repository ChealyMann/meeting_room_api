<script setup lang="ts">
import { CircleAlert, Trash2, Upload } from 'lucide-vue-next'
import { ref } from 'vue'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { deleteMyAvatar, uploadMyAvatar } from '../api/me'
import type { UserDetail } from '../api/types'
import { usePrivateImage } from '../composables/usePrivateImage'
import BaseButton from './base/BaseButton.vue'

// `version` changes when the photo is replaced (its address stays the same): use updated_at.
const props = defineProps<{ avatarUrl: string | null; version: string }>()
const emit = defineEmits<{ uploaded: [user: UserDetail]; removed: [] }>()

const ACCEPT = 'image/jpeg,image/png,image/webp'

const { imageUrl, loading, error: loadError } = usePrivateImage(
  () => props.avatarUrl,
  () => props.version,
)
const uploading = ref(false)
const removing = ref(false)
const confirming = ref(false)
const error = ref('')

function messageOf(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Something went wrong.'
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  error.value = ''
  confirming.value = false
  uploading.value = true
  try {
    emit('uploaded', await uploadMyAvatar(api, file))
  } catch (err) {
    // The old photo stays; only the message changes.
    error.value = messageOf(err)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function remove() {
  error.value = ''
  removing.value = true
  try {
    await deleteMyAvatar(api)
    confirming.value = false
    emit('removed')
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    removing.value = false
  }
}
</script>

<template>
  <div class="field avatar" :class="{ 'has-error': error || loadError }">
    <div class="row">
      <div class="disc" :aria-busy="loading || undefined">
        <img v-if="imageUrl" :src="imageUrl" alt="Your photo" />
        <span v-else-if="!loading" class="empty">No photo yet</span>
      </div>
      <div class="side">
        <p class="hint">A clear photo of your face. It is cropped to a square. JPEG, PNG or WebP.</p>

        <div v-if="confirming" class="confirm">
          <p>
            <b>Remove your photo?</b>
            Your initials show instead.
          </p>
          <div class="actions">
            <BaseButton variant="quiet" @click="confirming = false">Keep it</BaseButton>
            <BaseButton variant="danger" class="confirm-remove" :busy="removing" @click="remove">
              {{ removing ? 'Removing' : 'Remove photo' }}
            </BaseButton>
          </div>
        </div>

        <div v-else class="actions">
          <input
            id="avatar"
            type="file"
            class="sr-only file"
            :accept="ACCEPT"
            :disabled="uploading"
            :aria-describedby="error || loadError ? 'avatar-error' : undefined"
            @change="onFile"
          />
          <label for="avatar" class="btn" :class="{ busy: uploading }">
            <span v-if="uploading" class="spin" aria-hidden="true" />
            <Upload v-else aria-hidden="true" />
            {{ uploading ? 'Uploading' : imageUrl ? 'Replace photo' : 'Upload photo' }}
          </label>
          <BaseButton v-if="imageUrl" variant="quiet" class="remove" @click="confirming = true">
            <Trash2 aria-hidden="true" />
            Remove
          </BaseButton>
        </div>
      </div>
    </div>

    <p v-if="error || loadError" id="avatar-error" class="error">
      <CircleAlert aria-hidden="true" />
      <span>{{ error || loadError }}</span>
    </p>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.disc {
  flex: none;
  display: grid;
  place-items: center;
  width: 96px;
  height: 96px;
  overflow: hidden;
  border: 1px solid var(--color-rule-strong);
  border-radius: 50%;
  background: var(--color-sheet);
}
.disc img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.empty {
  padding: 0 12px;
  font-size: 12px;
  line-height: 1.3;
  text-align: center;
  color: var(--color-ink-off);
}
.side {
  display: grid;
  gap: 8px;
  min-width: 0;
}
.hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-intaglio);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.file:focus-visible + label {
  outline: 2px solid var(--color-crimson);
  outline-offset: 2px;
}
@media (max-width: 480px) {
  .row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
