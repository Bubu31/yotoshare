<template>
  <div v-if="chapter" class="chapter-editor bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{{ chapter.title || 'Sans titre' }}</h3>
      <button
        @click="$emit('close')"
        class="text-gray-400 hover:text-gray-600"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Audio Waveform -->
    <AudioWaveform
      v-if="chapter.audio_file"
      :archive-id="archiveId"
      :chapter-key="chapter.key"
      ref="waveformRef"
      @split="handleSplit"
      @trim="handleTrim"
    />

    <!-- Chapter Icon -->
    <div class="mt-4 border-t border-gray-200 dark:border-gray-700 pt-4">
      <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Icône du chapitre (16x16)</h4>
      <div class="flex items-center gap-4">
        <div
          :class="[
            'w-16 h-16 rounded-lg flex items-center justify-center overflow-hidden border-2 border-dashed transition-colors cursor-pointer',
            isDraggingIcon ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30' : 'border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700'
          ]"
          @click="$refs.iconInput.click()"
          @dragover.prevent="isDraggingIcon = true"
          @dragleave.prevent="isDraggingIcon = false"
          @drop.prevent="handleIconDrop"
        >
          <img
            v-if="(chapter.icon_file && !iconLoadFailed) || iconPreview"
            :src="iconPreview || getIconUrl()"
            class="w-full h-full object-contain"
            @error="onIconLoadError"
          />
          <svg v-else class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
        <div class="flex-1">
          <input
            type="file"
            accept="image/*"
            @change="handleIconUpload"
            class="hidden"
            ref="iconInput"
          />
          <button
            @click="$refs.iconInput.click()"
            :disabled="uploadingIcon"
            class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
          >
            {{ uploadingIcon ? 'Upload...' : 'Changer l\'icône' }}
          </button>
          <p class="text-xs text-gray-500 mt-1">L'image sera redimensionnée en 16x16 pixels</p>
        </div>
      </div>
    </div>

    <!-- Chapter Info -->
    <div class="mt-4 border-t border-gray-200 dark:border-gray-700 pt-4">
      <dl class="grid grid-cols-2 gap-2 text-sm">
        <div>
          <dt class="text-gray-500 dark:text-gray-400">Durée</dt>
          <dd class="font-medium text-gray-900 dark:text-white">{{ formatDuration(chapter.duration) }}</dd>
        </div>
        <div>
          <dt class="text-gray-500 dark:text-gray-400">Fichier audio</dt>
          <dd class="font-medium text-gray-900 dark:text-white truncate">{{ chapter.audio_file || '-' }}</dd>
        </div>
        <div v-if="chapter.label">
          <dt class="text-gray-500 dark:text-gray-400">Label</dt>
          <dd class="font-medium text-gray-900 dark:text-white">{{ chapter.label }}</dd>
        </div>
      </dl>

      <!-- Replace audio -->
      <div class="mt-3 flex items-center gap-2">
        <input
          type="file"
          accept="audio/*"
          @change="handleReplaceAudio"
          class="hidden"
          ref="replaceAudioInput"
        />
        <button
          @click="$refs.replaceAudioInput.click()"
          :disabled="replacingAudio"
          class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
        >
          <i :class="replacingAudio ? 'fas fa-spinner fa-spin' : 'fas fa-exchange-alt'" class="mr-1"></i>
          {{ replacingAudio ? 'Remplacement...' : 'Remplacer l\'audio' }}
        </button>
      </div>
    </div>

    <!-- Actions -->
    <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
      <button
        @click="handleRefresh"
        :disabled="refreshing"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
      >
        <svg v-if="refreshing" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {{ refreshing ? 'Actualisation...' : 'Actualiser' }}
      </button>
    </div>

    <!-- Loading overlay -->
    <div v-if="processing" class="absolute inset-0 bg-white/80 dark:bg-gray-800/80 flex items-center justify-center rounded-lg">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span class="text-sm text-gray-600 dark:text-gray-300">Traitement en cours...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import AudioWaveform from './AudioWaveform.vue'
import { useArchivesStore } from '../../stores/archives'

const props = defineProps({
  archiveId: { type: Number, required: true },
  chapter: { type: Object, default: null }
})

const emit = defineEmits(['close', 'refresh'])

const store = useArchivesStore()
const waveformRef = ref(null)
const iconInput = ref(null)
const iconPreview = ref(null)
const uploadingIcon = ref(false)
const processing = ref(false)
const isDraggingIcon = ref(false)
const iconCacheBuster = ref(Date.now())
const refreshing = ref(false)
const iconLoadFailed = ref(false)
const replaceAudioInput = ref(null)
const replacingAudio = ref(false)

// Reset preview when chapter changes
watch(() => props.chapter?.key, () => {
  iconPreview.value = null
  iconCacheBuster.value = Date.now()
  iconLoadFailed.value = false
})

function getIconUrl() {
  return `${store.getChapterIconUrl(props.archiveId, props.chapter.key)}?t=${iconCacheBuster.value}`
}

function onIconLoadError() {
  iconLoadFailed.value = true
}

function formatDuration(ms) {
  if (!ms) return '--:--'
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

async function handleIconUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  await uploadIcon(file)
  event.target.value = ''
}

function handleIconDrop(event) {
  isDraggingIcon.value = false
  const file = event.dataTransfer.files?.[0]
  if (file && file.type.startsWith('image/')) {
    uploadIcon(file)
  }
}

async function uploadIcon(file) {
  // Preview
  iconPreview.value = URL.createObjectURL(file)
  iconLoadFailed.value = false

  uploadingIcon.value = true
  try {
    const formData = new FormData()
    formData.append('icon_file', file)
    await store.updateChapterIcon(props.archiveId, props.chapter.key, formData)
    emit('refresh')
  } catch (e) {
    console.error('Icon upload failed:', e)
    alert('Erreur lors de l\'upload: ' + (e.response?.data?.detail || e.message))
    iconPreview.value = null
  } finally {
    uploadingIcon.value = false
  }
}

async function handleSplit(splitPoints) {
  if (!splitPoints || splitPoints.length === 0) return

  processing.value = true
  try {
    await store.splitChapter(props.archiveId, props.chapter.key, splitPoints)
    emit('refresh')
    emit('close')
  } catch (e) {
    console.error('Split failed:', e)
    alert('Erreur lors du split: ' + e.message)
  } finally {
    processing.value = false
  }
}

async function handleTrim({ startMs, endMs, mode }) {
  processing.value = true
  try {
    await store.trimChapter(props.archiveId, props.chapter.key, startMs, endMs, mode)
    emit('refresh')
  } catch (e) {
    console.error('Trim failed:', e)
    alert('Erreur lors du trim: ' + e.message)
  } finally {
    processing.value = false
  }
}

async function handleReplaceAudio(event) {
  const file = event.target.files?.[0]
  if (!file) return
  event.target.value = ''

  replacingAudio.value = true
  try {
    const formData = new FormData()
    formData.append('audio_file', file)
    await store.replaceChapterAudio(props.archiveId, props.chapter.key, formData)
    emit('refresh')
  } catch (e) {
    console.error('Replace audio failed:', e)
    alert('Erreur lors du remplacement: ' + (e.response?.data?.detail || e.message))
  } finally {
    replacingAudio.value = false
  }
}

async function handleRefresh() {
  refreshing.value = true
  iconCacheBuster.value = Date.now()
  emit('refresh')
  // Small delay to show the spinner
  await new Promise(resolve => setTimeout(resolve, 500))
  refreshing.value = false
}
</script>

<style scoped>
.chapter-editor {
  position: relative;
}
</style>
