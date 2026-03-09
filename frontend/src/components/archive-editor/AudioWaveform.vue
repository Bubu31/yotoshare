<template>
  <div class="audio-waveform">
    <!-- Controls -->
    <div class="flex items-center gap-2 mb-3">
      <button
        @click="togglePlay"
        :disabled="!isReady"
        class="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        <svg v-if="isPlaying" class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
        </svg>
        <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z" />
        </svg>
      </button>

      <span class="text-sm font-mono text-gray-600 min-w-[80px]">
        {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
      </span>

      <div class="flex-1"></div>

      <!-- Mode selector -->
      <div class="flex bg-gray-100 rounded-lg p-0.5">
        <button
          @click="mode = 'play'"
          :class="[
            'px-3 py-1 text-xs font-medium rounded-md transition-colors',
            mode === 'play' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
          ]"
        >
          Lecture
        </button>
        <button
          @click="mode = 'trim'"
          :class="[
            'px-3 py-1 text-xs font-medium rounded-md transition-colors',
            mode === 'trim' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
          ]"
        >
          Trim
        </button>
        <button
          @click="mode = 'split'"
          :class="[
            'px-3 py-1 text-xs font-medium rounded-md transition-colors',
            mode === 'split' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
          ]"
        >
          Split
        </button>
      </div>
    </div>

    <!-- Waveform container -->
    <div
      ref="waveformContainer"
      class="waveform-container relative bg-gray-50 rounded-lg overflow-hidden"
      :class="{ 'cursor-crosshair': mode !== 'play' }"
      @click="handleWaveformClick"
    >
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-gray-100">
        <svg class="w-6 h-6 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
      </div>

      <!-- Selection overlay for trim mode -->
      <div
        v-if="mode === 'trim' && selection.start !== null"
        class="absolute top-0 bottom-0 bg-blue-200/50 pointer-events-none z-10"
        :style="selectionStyle"
      ></div>

      <!-- Split markers -->
      <template v-if="mode === 'split'">
        <div
          v-for="(point, index) in splitPoints"
          :key="index"
          class="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20"
          :style="{ left: `${(point / duration) * 100}%` }"
        >
          <button
            @click.stop="removeSplitPoint(index)"
            class="absolute -top-1 -left-2 w-4 h-4 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-600"
          >
            ×
          </button>
        </div>
      </template>
    </div>

    <!-- Action buttons based on mode -->
    <div v-if="mode === 'trim' && selection.start !== null" class="flex items-center gap-2 mt-3">
      <span class="text-sm text-gray-600">
        Sélection: {{ formatTime(selection.start) }} - {{ formatTime(selection.end) }}
      </span>
      <div class="flex-1"></div>
      <button
        @click="clearSelection"
        class="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
      >
        Annuler
      </button>
      <button
        @click="trimKeep"
        class="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
      >
        Garder la sélection
      </button>
      <button
        @click="trimDelete"
        class="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
      >
        Supprimer la sélection
      </button>
    </div>

    <div v-if="mode === 'split' && splitPoints.length > 0" class="flex items-center gap-2 mt-3">
      <span class="text-sm text-gray-600">
        {{ splitPoints.length }} point(s) de découpe
      </span>
      <div class="flex-1"></div>
      <button
        @click="splitPoints = []"
        class="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
      >
        Effacer tout
      </button>
      <button
        @click="confirmSplit"
        class="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700"
      >
        Découper
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import { useArchivesStore } from '../../stores/archives'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  archiveId: { type: Number, required: true },
  chapterKey: { type: String, required: true }
})

const emit = defineEmits(['split', 'trim'])

const store = useArchivesStore()
const authStore = useAuthStore()
const waveformContainer = ref(null)
const loading = ref(true)
const isReady = ref(false)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const mode = ref('play')
const selection = ref({ start: null, end: null })
const splitPoints = ref([])

let wavesurfer = null

const selectionStyle = computed(() => {
  if (selection.value.start === null || duration.value === 0) return {}
  const left = (selection.value.start / duration.value) * 100
  const width = ((selection.value.end - selection.value.start) / duration.value) * 100
  return {
    left: `${left}%`,
    width: `${width}%`
  }
})

function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function togglePlay() {
  if (!wavesurfer) return
  wavesurfer.playPause()
}

function handleWaveformClick(event) {
  if (!wavesurfer || !isReady.value) return

  const rect = waveformContainer.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const ratio = x / rect.width
  const time = ratio * duration.value

  if (mode.value === 'play') {
    wavesurfer.seekTo(ratio)
  } else if (mode.value === 'trim') {
    if (selection.value.start === null) {
      selection.value.start = time
      selection.value.end = time
    } else if (time > selection.value.start) {
      selection.value.end = time
    } else {
      selection.value.start = time
    }
  } else if (mode.value === 'split') {
    // Add split point
    const timeMs = Math.round(time * 1000)
    if (!splitPoints.value.includes(timeMs)) {
      splitPoints.value.push(timeMs)
      splitPoints.value.sort((a, b) => a - b)
    }
  }
}

function clearSelection() {
  selection.value = { start: null, end: null }
}

function removeSplitPoint(index) {
  splitPoints.value.splice(index, 1)
}

function trimKeep() {
  if (selection.value.start === null) return
  emit('trim', {
    startMs: Math.round(selection.value.start * 1000),
    endMs: Math.round(selection.value.end * 1000),
    mode: 'keep'
  })
}

function trimDelete() {
  if (selection.value.start === null) return
  emit('trim', {
    startMs: Math.round(selection.value.start * 1000),
    endMs: Math.round(selection.value.end * 1000),
    mode: 'delete'
  })
}

function confirmSplit() {
  if (splitPoints.value.length === 0) return
  emit('split', [...splitPoints.value])
}

async function initWavesurfer() {
  if (!waveformContainer.value) return

  loading.value = true

  try {
    // Get audio URL with auth token
    const audioUrl = store.getChapterAudioUrl(props.archiveId, props.chapterKey)
    const token = authStore.token

    wavesurfer = WaveSurfer.create({
      container: waveformContainer.value,
      waveColor: '#94a3b8',
      progressColor: '#3b82f6',
      cursorColor: '#1e40af',
      barWidth: 2,
      barRadius: 2,
      barGap: 1,
      height: 80,
      normalize: true,
      fetchParams: {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    })

    wavesurfer.on('ready', () => {
      isReady.value = true
      duration.value = wavesurfer.getDuration()
      loading.value = false
    })

    wavesurfer.on('play', () => {
      isPlaying.value = true
    })

    wavesurfer.on('pause', () => {
      isPlaying.value = false
    })

    wavesurfer.on('timeupdate', (time) => {
      currentTime.value = time
    })

    wavesurfer.on('error', (err) => {
      console.error('WaveSurfer error:', err)
      loading.value = false
    })

    await wavesurfer.load(audioUrl)
  } catch (e) {
    console.error('Failed to init wavesurfer:', e)
    loading.value = false
  }
}

watch(() => props.chapterKey, () => {
  if (wavesurfer) {
    wavesurfer.destroy()
    wavesurfer = null
  }
  isReady.value = false
  isPlaying.value = false
  currentTime.value = 0
  duration.value = 0
  selection.value = { start: null, end: null }
  splitPoints.value = []
  mode.value = 'play'
  initWavesurfer()
})

onMounted(() => {
  initWavesurfer()
})

onUnmounted(() => {
  if (wavesurfer) {
    wavesurfer.destroy()
  }
})
</script>

<style scoped>
.waveform-container {
  min-height: 80px;
}
</style>
