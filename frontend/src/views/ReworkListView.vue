<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const submissions = ref([])
const loading = ref(true)
const error = ref('')
const selectedSub = ref(null)

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/submissions/rework')
    submissions.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors du chargement'
  } finally {
    loading.value = false
  }
})

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

function chaptersCount(sub) {
  if (sub.chapters_count) return sub.chapters_count
  if (sub.chapters_data) {
    try {
      return JSON.parse(sub.chapters_data).length
    } catch { return null }
  }
  return null
}

function parsedChapters(sub) {
  if (!sub.chapters_data) return []
  try {
    return JSON.parse(sub.chapters_data)
  } catch { return [] }
}

function iconUrl(subId, key) {
  return `/api/submissions/${subId}/icon/${key}`
}

function isYotoIcon(icon) {
  return icon && icon.startsWith('yoto:')
}

function downloadUrl(id) {
  return `/api/submissions/rework/${id}/download`
}

function openDetail(sub) {
  selectedSub.value = sub
}

function closeDetail() {
  selectedSub.value = null
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <!-- Header -->
    <div class="text-center mb-8">
      <h1 class="text-xl font-bold text-gray-800 dark:text-white">
        <i class="fas fa-wrench text-orange-500 mr-2"></i>
        Archives à retravailler
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        Ces archives ont du potentiel mais nécessitent des améliorations. Téléchargez, retravaillez et re-soumettez !
      </p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-12">
      <div class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg text-sm inline-block">
        <i class="fas fa-exclamation-circle mr-2"></i>{{ error }}
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="submissions.length === 0" class="text-center py-12">
      <i class="fas fa-check-circle text-4xl text-green-400 dark:text-green-600 mb-3"></i>
      <p class="text-gray-500 dark:text-gray-400">Aucune archive à retravailler pour le moment.</p>
    </div>

    <!-- List -->
    <div v-else class="space-y-4">
      <div
        v-for="sub in submissions"
        :key="sub.id"
        class="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden"
      >
        <div class="flex flex-col sm:flex-row">
          <!-- Cover -->
          <div class="sm:w-40 sm:h-40 h-48 bg-gray-100 dark:bg-gray-800 flex-shrink-0">
            <img
              v-if="sub.cover_path"
              :src="`/api/submissions/${sub.id}/cover`"
              :alt="sub.title"
              class="w-full h-full object-cover"
            >
            <div v-else class="w-full h-full flex items-center justify-center">
              <i class="fas fa-file-archive text-3xl text-gray-300 dark:text-gray-600"></i>
            </div>
          </div>

          <!-- Content -->
          <div class="flex-1 p-4 sm:p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <h3 class="font-semibold text-gray-800 dark:text-white text-lg">
                  {{ sub.title || 'Sans titre' }}
                </h3>
                <p v-if="sub.pseudonym" class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                  <i class="fas fa-user mr-1"></i>{{ sub.pseudonym }}
                </p>
              </div>
            </div>

            <!-- Meta -->
            <div class="flex items-center gap-3 mt-2 text-xs text-gray-400 dark:text-gray-500">
              <span><i class="fas fa-weight-hanging mr-1"></i>{{ formatSize(sub.file_size) }}</span>
              <span v-if="sub.total_duration"><i class="fas fa-clock mr-1"></i>{{ formatDuration(sub.total_duration) }}</span>
              <span v-if="chaptersCount(sub)"><i class="fas fa-list mr-1"></i>{{ chaptersCount(sub) }} ch.</span>
            </div>

            <!-- Rework comment -->
            <div v-if="sub.rework_comment" class="mt-3 px-3 py-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-sm text-orange-700 dark:text-orange-400">
              <i class="fas fa-comment mr-1.5"></i>{{ sub.rework_comment }}
            </div>

            <!-- Actions -->
            <div class="flex flex-wrap gap-2 mt-4">
              <button
                @click="openDetail(sub)"
                class="inline-flex items-center px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg transition-colors"
              >
                <i class="fas fa-list-ul mr-2"></i>
                Voir les chapitres
              </button>
              <a
                :href="downloadUrl(sub.id)"
                class="inline-flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <i class="fas fa-download mr-2"></i>
                Télécharger le ZIP
              </a>
              <router-link
                :to="`/submit?rework=${sub.id}`"
                class="inline-flex items-center px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <i class="fas fa-redo mr-2"></i>
                Re-soumettre
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Detail Modal -->
  <Teleport to="body">
    <div
      v-if="selectedSub"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      @click.self="closeDetail"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeDetail"></div>

      <!-- Panel -->
      <div class="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 w-full max-w-2xl max-h-[85vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-start gap-4 p-5 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
          <img
            v-if="selectedSub.cover_path"
            :src="`/api/submissions/${selectedSub.id}/cover`"
            :alt="selectedSub.title"
            class="w-16 h-16 rounded-xl object-cover flex-shrink-0"
          >
          <div v-else class="w-16 h-16 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
            <i class="fas fa-file-archive text-2xl text-gray-400"></i>
          </div>
          <div class="flex-1 min-w-0">
            <h2 class="font-bold text-gray-900 dark:text-white text-lg truncate">{{ selectedSub.title || 'Sans titre' }}</h2>
            <p v-if="selectedSub.pseudonym" class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              <i class="fas fa-user mr-1"></i>{{ selectedSub.pseudonym }}
            </p>
            <div class="flex items-center gap-3 mt-1.5 text-xs text-gray-400 dark:text-gray-500">
              <span><i class="fas fa-weight-hanging mr-1"></i>{{ formatSize(selectedSub.file_size) }}</span>
              <span v-if="selectedSub.total_duration"><i class="fas fa-clock mr-1"></i>{{ formatDuration(selectedSub.total_duration) }}</span>
              <span v-if="chaptersCount(selectedSub)"><i class="fas fa-list mr-1"></i>{{ chaptersCount(selectedSub) }} chapitres</span>
            </div>
          </div>
          <button @click="closeDetail" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 flex-shrink-0 transition-colors">
            <i class="fas fa-times text-lg"></i>
          </button>
        </div>

        <!-- Rework comment -->
        <div v-if="selectedSub.rework_comment" class="mx-5 mt-4 flex-shrink-0 px-4 py-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-xl text-sm text-orange-700 dark:text-orange-400">
          <p class="font-semibold mb-1"><i class="fas fa-comment-dots mr-1.5"></i>Commentaire du modérateur</p>
          <p>{{ selectedSub.rework_comment }}</p>
        </div>

        <!-- Chapters list -->
        <div class="flex-1 overflow-y-auto p-5">
          <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            Chapitres
          </h3>

          <div v-if="parsedChapters(selectedSub).length === 0" class="text-center py-8 text-gray-400 dark:text-gray-500 text-sm">
            <i class="fas fa-info-circle mr-1"></i>Aucune information sur les chapitres.
          </div>

          <div v-else class="space-y-1.5">
            <div
              v-for="(ch, i) in parsedChapters(selectedSub)"
              :key="ch.key || i"
              class="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800/50"
            >
              <!-- Icon -->
              <div class="w-8 h-8 rounded-lg overflow-hidden bg-gray-200 dark:bg-gray-700 flex-shrink-0 flex items-center justify-center">
                <img
                  v-if="ch.key && !isYotoIcon(ch.icon)"
                  :src="iconUrl(selectedSub.id, ch.key)"
                  class="w-full h-full object-cover"
                  @error="$event.target.style.display='none'; $event.target.nextSibling.style.display='flex'"
                >
                <span class="text-xs text-gray-400 dark:text-gray-500 hidden items-center justify-center w-full h-full">{{ i + 1 }}</span>
              </div>
              <!-- Info -->
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-800 dark:text-white truncate">
                  {{ ch.title || `Chapitre ${i + 1}` }}
                </p>
                <p v-if="ch.label" class="text-xs text-gray-400 dark:text-gray-500 truncate">{{ ch.label }}</p>
              </div>
              <!-- Duration -->
              <span v-if="ch.duration" class="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0 font-mono">
                {{ formatDuration(ch.duration < 100000 ? ch.duration * 1000 : ch.duration) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Footer actions -->
        <div class="flex gap-2 p-5 border-t border-gray-200 dark:border-gray-800 flex-shrink-0">
          <a
            :href="downloadUrl(selectedSub.id)"
            class="inline-flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-download mr-2"></i>
            Télécharger le ZIP
          </a>
          <router-link
            :to="`/submit?rework=${selectedSub.id}`"
            class="inline-flex items-center px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-redo mr-2"></i>
            Re-soumettre
          </router-link>
        </div>
      </div>
    </div>
  </Teleport>
</template>
