<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useArchivesStore } from '../stores/archives'
import ArchiveForm from '../components/ArchiveForm.vue'

const router = useRouter()
const archivesStore = useArchivesStore()
const error = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadedBytes = ref(0)
const totalBytes = ref(0)
const uploadStartTime = ref(null)

const uploadSpeed = computed(() => {
  if (!uploadStartTime.value || uploadedBytes.value === 0) return null
  const elapsed = (Date.now() - uploadStartTime.value) / 1000
  if (elapsed === 0) return null
  return uploadedBytes.value / elapsed
})

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

function formatSpeed(bytesPerSec) {
  if (!bytesPerSec) return ''
  return formatSize(bytesPerSec) + '/s'
}

const estimatedTimeLeft = computed(() => {
  if (!uploadSpeed.value || uploadProgress.value >= 100) return null
  const remaining = totalBytes.value - uploadedBytes.value
  const seconds = Math.round(remaining / uploadSpeed.value)
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}min ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}min`
})

onMounted(async () => {
  await archivesStore.fetchCategories()
  await archivesStore.fetchAges()
})

async function handleSubmit(formData) {
  error.value = ''
  uploading.value = true
  uploadProgress.value = 0
  uploadedBytes.value = 0
  totalBytes.value = 0
  uploadStartTime.value = Date.now()

  try {
    await archivesStore.createArchive(formData, {
      onUploadProgress(e) {
        if (e.total) {
          totalBytes.value = e.total
          uploadedBytes.value = e.loaded
          uploadProgress.value = Math.round((e.loaded / e.total) * 100)
        }
      },
    })
    router.push('/archives')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors de l\'upload'
    uploading.value = false
  }
}

function handleCancel() {
  router.push('/archives')
}
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <div class="mb-6 md:mb-8">
      <router-link to="/archives" class="text-primary-600 hover:text-primary-800 dark:hover:text-primary-400 mb-4 inline-block">
        <i class="fas fa-arrow-left mr-2"></i>
        Retour
      </router-link>
      <h1 class="text-2xl md:text-3xl font-bold text-gray-800 dark:text-white">
        <i class="fas fa-upload text-primary-600 mr-2"></i>
        Nouvelle archive
      </h1>
    </div>

    <div class="card p-4 md:p-6">
      <div
        v-if="error"
        class="mb-6 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg"
      >
        <i class="fas fa-exclamation-circle mr-2"></i>
        {{ error }}
      </div>

      <!-- Upload progress overlay -->
      <div v-if="uploading" class="mb-6">
        <div class="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-primary-700 dark:text-primary-300">
              <i class="fas fa-spinner fa-spin mr-2"></i>
              Upload en cours...
            </span>
            <span class="text-sm font-semibold text-primary-700 dark:text-primary-300">
              {{ uploadProgress }}%
            </span>
          </div>
          <div class="w-full bg-primary-100 dark:bg-primary-900/40 rounded-full h-3">
            <div
              class="h-3 rounded-full bg-primary-600 transition-all duration-300 ease-out"
              :style="{ width: uploadProgress + '%' }"
            ></div>
          </div>
          <div class="flex justify-between mt-2 text-xs text-primary-600 dark:text-primary-400">
            <span v-if="totalBytes > 0">
              {{ formatSize(uploadedBytes) }} / {{ formatSize(totalBytes) }}
            </span>
            <span v-if="uploadSpeed">
              {{ formatSpeed(uploadSpeed) }}
              <template v-if="estimatedTimeLeft"> &mdash; {{ estimatedTimeLeft }} restant</template>
            </span>
          </div>
        </div>
      </div>

      <ArchiveForm
        :categories="archivesStore.categories"
        :ages="archivesStore.ages"
        :disabled="uploading"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </div>
  </div>
</template>
