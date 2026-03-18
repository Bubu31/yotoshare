<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from '../composables/useMessage'
import api from '../services/api'

const route = useRoute()
const router = useRouter()
const { showMessage } = useMessage()

const submission = ref(null)
const content = ref(null)
const loading = ref(true)
const processing = ref(false)
const showRejectModal = ref(false)
const showReworkModal = ref(false)
const showCoverModal = ref(false)
const rejectionReason = ref('')
const reworkComment = ref('')
const playingKey = ref(null)
const audioRef = ref(null)
const audioUrl = ref(null)
const extracting = ref(false)
const audioCurrentTime = ref(0)
const audioDuration = ref(0)

function onTimeUpdate() {
  if (audioRef.value) {
    audioCurrentTime.value = audioRef.value.currentTime
    audioDuration.value = audioRef.value.duration || 0
  }
}

function seekAudio(event) {
  const bar = event.currentTarget
  const rect = bar.getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
  if (audioRef.value && audioDuration.value) {
    audioRef.value.currentTime = ratio * audioDuration.value
  }
}

function formatTime(seconds) {
  if (!seconds || !isFinite(seconds)) return '0:00'
  const min = Math.floor(seconds / 60)
  const sec = Math.floor(seconds % 60)
  return `${min}:${sec.toString().padStart(2, '0')}`
}

onMounted(async () => {
  await loadSubmission()
})

async function loadSubmission() {
  loading.value = true
  try {
    const { data } = await api.get(`/api/submissions/${route.params.id}`)
    submission.value = data
  } catch (e) {
    showMessage('error',e.response?.data?.detail || 'Erreur lors du chargement')
    loading.value = false
    return
  }
  try {
    const { data } = await api.get(`/api/submissions/${route.params.id}/content`)
    content.value = data
  } catch (e) {
    console.error('Failed to load submission content:', e)
    showMessage('error', e.response?.data?.detail || 'Impossible de charger le contenu de l\'archive')
  }
  loading.value = false
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDuration(ms) {
  if (!ms) return '—'
  const totalSec = Math.round(ms / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function toggleAudio(key) {
  if (playingKey.value === key) {
    audioRef.value?.pause()
    playingKey.value = null
    return
  }
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = null
  }
  audioCurrentTime.value = 0
  audioDuration.value = 0
  playingKey.value = key
  try {
    const { data } = await api.get(`/api/submissions/${submission.value.id}/audio/${key}`, { responseType: 'blob' })
    audioUrl.value = URL.createObjectURL(data)
    await nextTick()
    await audioRef.value?.play()
  } catch (e) {
    showMessage('error', 'Impossible de charger l\'audio')
    playingKey.value = null
  }
}

async function extractData() {
  extracting.value = true
  try {
    await api.post(`/api/submissions/${route.params.id}/extract`)
    showMessage('success', 'Extraction terminée')
    await loadSubmission()
  } catch (e) {
    showMessage('error', e.response?.data?.detail || "Erreur lors de l'extraction")
  } finally {
    extracting.value = false
  }
}

async function approve() {
  processing.value = true
  try {
    const { data } = await api.post(`/api/submissions/${route.params.id}/review`, {
      action: 'approve',
    })
    showMessage('success',data.message)
    router.push('/admin/submissions')
  } catch (e) {
    showMessage('error',e.response?.data?.detail || "Erreur lors de l'approbation")
  } finally {
    processing.value = false
  }
}

async function reject() {
  processing.value = true
  try {
    const { data } = await api.post(`/api/submissions/${route.params.id}/review`, {
      action: 'reject',
      rejection_reason: rejectionReason.value || null,
    })
    showMessage('success',data.message)
    showRejectModal.value = false
    router.push('/admin/submissions')
  } catch (e) {
    showMessage('error',e.response?.data?.detail || 'Erreur lors du rejet')
  } finally {
    processing.value = false
  }
}

async function rework() {
  if (!reworkComment.value.trim()) return
  processing.value = true
  try {
    const { data } = await api.post(`/api/submissions/${route.params.id}/review`, {
      action: 'rework',
      rework_comment: reworkComment.value.trim(),
    })
    showMessage('success', data.message)
    showReworkModal.value = false
    router.push('/admin/submissions')
  } catch (e) {
    showMessage('error', e.response?.data?.detail || 'Erreur lors du rework')
  } finally {
    processing.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <div class="mb-6">
      <router-link to="/admin/submissions" class="text-primary-600 hover:text-primary-800 dark:hover:text-primary-400 mb-4 inline-block">
        <i class="fas fa-arrow-left mr-2"></i>
        Retour aux soumissions
      </router-link>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
    </div>

    <template v-else-if="submission">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Left column: Cover + Info -->
        <div class="md:col-span-1">
          <div class="card overflow-hidden">
            <!-- Cover -->
            <div class="aspect-square bg-gray-100 dark:bg-gray-800 relative group">
              <img
                v-if="submission.cover_path"
                :src="`/api/archives/cover/${submission.cover_path}`"
                :alt="submission.title"
                class="w-full h-full object-contain cursor-pointer"
                @click="showCoverModal = true"
              >
              <div v-else class="w-full h-full flex items-center justify-center">
                <i class="fas fa-file-archive text-5xl text-gray-300 dark:text-gray-600"></i>
              </div>
              <button
                v-if="submission.cover_path"
                @click="showCoverModal = true"
                class="absolute bottom-2 right-2 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <i class="fas fa-expand text-xs"></i>
              </button>
            </div>

            <div class="p-4 space-y-3">
              <h2 class="text-lg font-bold text-gray-800 dark:text-white">
                {{ submission.title || 'Sans titre' }}
              </h2>

              <div v-if="submission.pseudonym" class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <i class="fas fa-user text-gray-400"></i>
                {{ submission.pseudonym }}
              </div>

              <div class="space-y-1.5 text-sm text-gray-500 dark:text-gray-400">
                <div><i class="fas fa-weight-hanging mr-2 w-4 text-center"></i>{{ formatSize(submission.file_size) }}</div>
                <div v-if="submission.total_duration"><i class="fas fa-clock mr-2 w-4 text-center"></i>{{ formatDuration(submission.total_duration) }}</div>
                <div v-if="submission.chapters_count"><i class="fas fa-list mr-2 w-4 text-center"></i>{{ submission.chapters_count }} chapitres</div>
                <div><i class="fas fa-calendar mr-2 w-4 text-center"></i>{{ formatDate(submission.created_at) }}</div>
              </div>

              <div class="pt-2 flex flex-wrap items-center gap-2">
                <span :class="[
                  'px-2.5 py-1 rounded-full text-xs font-semibold',
                  submission.status === 'pending' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' :
                  submission.status === 'approved' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                  submission.status === 'rework' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400' :
                  'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                ]">
                  {{ submission.status === 'pending' ? 'En attente' : submission.status === 'approved' ? 'Approuvée' : submission.status === 'rework' ? 'A retravailler' : 'Rejetée' }}
                </span>
                <span v-if="submission.parent_submission_id" class="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                  <i class="fas fa-redo mr-1"></i>Re-soumission de #{{ submission.parent_submission_id }}
                </span>
              </div>

              <div v-if="submission.rework_comment" class="text-sm text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 rounded-lg p-3">
                <i class="fas fa-wrench mr-1"></i>
                {{ submission.rework_comment }}
              </div>

              <div v-if="submission.rejection_reason" class="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
                <i class="fas fa-comment mr-1"></i>
                {{ submission.rejection_reason }}
              </div>
            </div>
          </div>
        </div>

        <!-- Right column: Chapters + Actions -->
        <div class="md:col-span-2 space-y-6">
          <!-- Extraction banner -->
          <div
            v-if="submission && !submission.has_extracted_data"
            class="card p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800"
          >
            <div class="flex items-center justify-between gap-4">
              <div class="flex items-center gap-3 min-w-0">
                <i class="fas fa-box-open text-amber-500 text-lg flex-shrink-0"></i>
                <div>
                  <p class="text-sm font-medium text-amber-800 dark:text-amber-300">Données non extraites</p>
                  <p class="text-xs text-amber-600 dark:text-amber-400">La consultation sera lente car les fichiers sont lus depuis le ZIP. Extrayez les données pour une consultation rapide.</p>
                </div>
              </div>
              <button
                @click="extractData"
                :disabled="extracting"
                class="btn bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors disabled:opacity-50 whitespace-nowrap flex-shrink-0"
              >
                <i :class="extracting ? 'fas fa-spinner fa-spin' : 'fas fa-archive'" class="mr-1.5"></i>
                {{ extracting ? 'Extraction...' : 'Extraire' }}
              </button>
            </div>
          </div>

          <!-- Chapters -->
          <div class="card p-4 md:p-6">
            <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">
              <i class="fas fa-list-ol mr-2 text-primary-600"></i>
              Chapitres
            </h3>

            <div v-if="content?.chapters?.length" class="space-y-2">
              <div
                v-for="(ch, i) in content.chapters"
                :key="ch.key"
                class="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex-wrap"
              >
                <!-- Icon -->
                <div class="w-8 h-8 rounded flex items-center justify-center flex-shrink-0 bg-gray-200 dark:bg-gray-700">
                  <img
                    v-if="ch.icon_file"
                    :src="`/api/submissions/${submission.id}/icon/${ch.key}`"
                    class="w-8 h-8 rounded"
                    :alt="ch.title"
                  >
                  <span v-else class="text-xs text-gray-500 font-semibold">{{ i + 1 }}</span>
                </div>

                <!-- Info -->
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-800 dark:text-white truncate">
                    {{ ch.title || ch.label || `Chapitre ${i + 1}` }}
                  </p>
                  <p v-if="ch.duration" class="text-xs text-gray-400">
                    {{ formatDuration(ch.duration) }}
                  </p>
                </div>

                <!-- Play button -->
                <button
                  v-if="ch.audio_file"
                  @click="toggleAudio(ch.key)"
                  class="w-8 h-8 rounded-full flex items-center justify-center text-primary-600 hover:bg-primary-100 dark:hover:bg-primary-900/30 transition-colors flex-shrink-0"
                >
                  <i :class="playingKey === ch.key ? 'fas fa-pause' : 'fas fa-play'" class="text-sm"></i>
                </button>

                <!-- Progress bar -->
                <div
                  v-if="playingKey === ch.key && audioDuration > 0"
                  class="w-full col-span-full flex items-center gap-2 mt-1 px-1"
                >
                  <span class="text-[10px] tabular-nums text-gray-400 w-8 text-right flex-shrink-0">{{ formatTime(audioCurrentTime) }}</span>
                  <div
                    class="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full cursor-pointer group relative"
                    @click="seekAudio($event)"
                  >
                    <div
                      class="h-full bg-primary-500 rounded-full transition-[width] duration-100 relative"
                      :style="{ width: (audioCurrentTime / audioDuration * 100) + '%' }"
                    >
                      <div class="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-primary-600 rounded-full shadow opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    </div>
                  </div>
                  <span class="text-[10px] tabular-nums text-gray-400 w-8 flex-shrink-0">{{ formatTime(audioDuration) }}</span>
                </div>
              </div>
            </div>

            <p v-else class="text-gray-500 dark:text-gray-400 text-sm">Aucun chapitre trouvé.</p>
          </div>

          <!-- Audio player (hidden) -->
          <audio
            ref="audioRef"
            :src="audioUrl"
            @ended="playingKey = null; audioCurrentTime = 0; audioDuration = 0"
            @timeupdate="onTimeUpdate"
            @loadedmetadata="onTimeUpdate"
            class="hidden"
          ></audio>

          <!-- Actions -->
          <div v-if="submission.status === 'pending'" class="flex gap-3">
            <button
              @click="approve"
              :disabled="processing"
              class="flex-1 btn bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-xl transition-colors disabled:opacity-50"
            >
              <i class="fas fa-check mr-2"></i>
              Approuver
            </button>
            <button
              @click="showReworkModal = true"
              :disabled="processing"
              class="flex-1 btn bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 rounded-xl transition-colors disabled:opacity-50"
            >
              <i class="fas fa-wrench mr-2"></i>
              A retravailler
            </button>
            <button
              @click="showRejectModal = true"
              :disabled="processing"
              class="flex-1 btn bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-xl transition-colors disabled:opacity-50"
            >
              <i class="fas fa-times mr-2"></i>
              Rejeter
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- Reject modal -->
    <Teleport to="body">
      <div v-if="showRejectModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="showRejectModal = false"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-md w-full p-6">
          <h3 class="text-lg font-bold text-gray-800 dark:text-white mb-4">
            <i class="fas fa-times-circle text-red-500 mr-2"></i>
            Rejeter la soumission
          </h3>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Raison du rejet <span class="text-gray-400 font-normal">(optionnel)</span>
            </label>
            <textarea
              v-model="rejectionReason"
              rows="3"
              class="input w-full"
              placeholder="Expliquer pourquoi cette soumission est rejetée..."
            ></textarea>
          </div>
          <div class="flex gap-3">
            <button
              @click="showRejectModal = false"
              class="flex-1 btn bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-xl py-2.5"
            >
              Annuler
            </button>
            <button
              @click="reject"
              :disabled="processing"
              class="flex-1 btn bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl py-2.5 disabled:opacity-50"
            >
              <i class="fas fa-times mr-1"></i>
              Confirmer le rejet
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  <!-- Rework modal -->
  <Teleport to="body">
    <div v-if="showReworkModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="fixed inset-0 bg-black/50" @click="showReworkModal = false"></div>
      <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-md w-full p-6">
        <h3 class="text-lg font-bold text-gray-800 dark:text-white mb-4">
          <i class="fas fa-wrench text-orange-500 mr-2"></i>
          Demander un rework
        </h3>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Commentaire <span class="text-red-500">*</span>
          </label>
          <textarea
            v-model="reworkComment"
            rows="3"
            class="input w-full"
            placeholder="Expliquer ce qui doit être retravaillé..."
          ></textarea>
        </div>
        <div class="flex gap-3">
          <button
            @click="showReworkModal = false"
            class="flex-1 btn bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-xl py-2.5"
          >
            Annuler
          </button>
          <button
            @click="rework"
            :disabled="processing || !reworkComment.trim()"
            class="flex-1 btn bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-xl py-2.5 disabled:opacity-50"
          >
            <i class="fas fa-wrench mr-1"></i>
            Confirmer
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Cover modal -->
  <Teleport to="body">
    <div v-if="showCoverModal" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click="showCoverModal = false">
      <div class="fixed inset-0 bg-black/80"></div>
      <img
        :src="`/api/archives/cover/${submission.cover_path}`"
        :alt="submission.title"
        class="relative max-w-full max-h-full rounded-xl shadow-2xl"
        @click.stop
      >
    </div>
  </Teleport>
  </div>
</template>
