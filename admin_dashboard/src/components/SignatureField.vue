<script setup lang="ts">
import { CircleAlert, Trash2, Upload } from 'lucide-vue-next'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { api } from '../api'
import { ApiError } from '../api/errors'
import { deleteMySignature, getImageBlob, uploadMySignature } from '../api/me'
import BaseButton from './base/BaseButton.vue'

const props = defineProps<{ signatureUrl: string | null }>()
const emit = defineEmits<{ change: [signatureUrl: string | null] }>()

const ACCEPT = 'image/jpeg,image/png,image/webp'

const current = ref(props.signatureUrl)
// An object URL for the image: the file needs the bearer token, so <img> cannot load it directly.
const imageUrl = ref<string | null>(null)
const loading = ref(false)
const uploading = ref(false)
const removing = ref(false)
const confirming = ref(false)
const error = ref('')

function messageOf(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Something went wrong.'
}

function setImage(url: string | null) {
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
  imageUrl.value = url
}

async function load() {
  if (!current.value) {
    setImage(null)
    return
  }
  loading.value = true
  try {
    setImage(URL.createObjectURL(await getImageBlob(api, current.value)))
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    loading.value = false
  }
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  error.value = ''
  confirming.value = false
  uploading.value = true
  try {
    const user = await uploadMySignature(api, file)
    current.value = user.signature_url
    await load()
    emit('change', user.signature_url)
  } catch (err) {
    // The old image stays; only the message changes.
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
    await deleteMySignature(api)
    current.value = null
    setImage(null)
    confirming.value = false
    emit('change', null)
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    removing.value = false
  }
}

watch(
  () => props.signatureUrl,
  (url) => {
    if (url === current.value) return
    current.value = url
    void load()
  },
)

onMounted(load)
onBeforeUnmount(() => setImage(null))
</script>

<template>
  <div class="field signature" :class="{ 'has-error': error }">
    <div class="sheet" :aria-busy="loading || undefined">
      <div v-if="loading" class="skeleton-bar" aria-hidden="true" />
      <img v-else-if="imageUrl" :key="imageUrl" :src="imageUrl" alt="Your signature" />
      <p v-else class="empty">No signature yet</p>
    </div>

    <p class="hint">Sign with a dark pen on blank white paper. JPEG, PNG or WebP.</p>

    <p v-if="error" id="signature-error" class="error">
      <CircleAlert aria-hidden="true" />
      <span>{{ error }}</span>
    </p>

    <div v-if="confirming" class="confirm">
      <p>
        <b>Remove your signature?</b>
        It will no longer appear on booking approval forms.
      </p>
      <div class="actions">
        <BaseButton variant="quiet" @click="confirming = false">Keep it</BaseButton>
        <BaseButton variant="danger" class="confirm-remove" :busy="removing" @click="remove">
          {{ removing ? 'Removing' : 'Remove signature' }}
        </BaseButton>
      </div>
    </div>

    <div v-else class="actions">
      <input
        id="signature"
        type="file"
        class="sr-only file"
        :accept="ACCEPT"
        :disabled="uploading"
        :aria-describedby="error ? 'signature-error' : undefined"
        @change="onFile"
      />
      <label for="signature" class="btn" :class="{ busy: uploading }">
        <span v-if="uploading" class="spin" aria-hidden="true" />
        <Upload v-else aria-hidden="true" />
        {{ uploading ? 'Uploading' : imageUrl ? 'Replace signature' : 'Upload signature' }}
      </label>
      <BaseButton v-if="imageUrl" variant="quiet" class="remove" @click="confirming = true">
        <Trash2 aria-hidden="true" />
        Remove
      </BaseButton>
    </div>
  </div>
</template>

<style scoped>
.signature {
  gap: 8px;
}
/* Flex, not grid: a grid row grows to the image, so max-height had nothing to fit into. */
.sheet {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 128px;
  padding: 12px;
  overflow: hidden;
  border: 1px solid var(--color-rule-strong);
  border-radius: 8px;
  /* Always white paper, also at night: the signature is black ink on a transparent ground. */
  background: #ffffff;
}
.sheet img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  /* Fades in on load and on every replace (a new key = a new element). */
  opacity: 1;
  transition: opacity 200ms var(--ease-out-quint);

  @starting-style {
    opacity: 0;
  }
}
.sheet .skeleton-bar {
  width: 60%;
  height: 22px;
}
.empty {
  margin: 0;
  font-size: 13px;
  color: #7a6355; /* day off-ink: the sheet is white in both themes */
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
</style>
