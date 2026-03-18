<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const submissions = ref([])
const loading = ref(true)
const error = ref('')

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

function downloadUrl(id) {
  return `/api/submissions/rework/${id}/download`
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
              <div class="flex gap-2 mt-4">
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
</template>
