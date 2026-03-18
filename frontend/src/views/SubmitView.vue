<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const parentSubmissionId = ref(route.query.rework ? parseInt(route.query.rework) : null)

const file = ref(null)
const pseudonym = ref('')
const dragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadedBytes = ref(0)
const totalBytes = ref(0)
const uploadStartTime = ref(null)
const success = ref(false)
const error = ref('')

const uploadSpeed = computed(() => {
  if (!uploadStartTime.value || uploadedBytes.value === 0) return null
  const elapsed = (Date.now() - uploadStartTime.value) / 1000
  if (elapsed === 0) return null
  return uploadedBytes.value / elapsed
})

const estimatedTimeLeft = computed(() => {
  if (!uploadSpeed.value || uploadProgress.value >= 100) return null
  const remaining = totalBytes.value - uploadedBytes.value
  const seconds = Math.round(remaining / uploadSpeed.value)
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}min ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}min`
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

function onDrop(e) {
  dragging.value = false
  const files = e.dataTransfer?.files
  if (files?.length) {
    selectFile(files[0])
  }
}

function onFileInput(e) {
  if (e.target.files?.length) {
    selectFile(e.target.files[0])
  }
}

function selectFile(f) {
  error.value = ''
  if (!f.name.toLowerCase().endsWith('.zip')) {
    error.value = 'Seuls les fichiers .zip sont acceptés.'
    return
  }
  if (f.size > 500 * 1024 * 1024) {
    error.value = 'Fichier trop volumineux (max 500 MB).'
    return
  }
  file.value = f
}

function removeFile() {
  file.value = null
}

async function submit() {
  if (!file.value) return

  error.value = ''
  uploading.value = true
  uploadProgress.value = 0
  uploadedBytes.value = 0
  totalBytes.value = 0
  uploadStartTime.value = Date.now()

  const formData = new FormData()
  formData.append('file', file.value)
  if (pseudonym.value.trim()) {
    formData.append('pseudonym', pseudonym.value.trim())
  }
  if (parentSubmissionId.value) {
    formData.append('parent_submission_id', parentSubmissionId.value)
  }

  try {
    await axios.post('/api/submissions', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress(e) {
        if (e.total) {
          totalBytes.value = e.total
          uploadedBytes.value = e.loaded
          uploadProgress.value = Math.round((e.loaded / e.total) * 100)
        }
      },
    })
    success.value = true
  } catch (e) {
    error.value = e.response?.data?.detail || "Erreur lors de l'envoi"
  } finally {
    uploading.value = false
  }
}

function reset() {
  file.value = null
  pseudonym.value = ''
  success.value = false
  error.value = ''
  uploading.value = false
  uploadProgress.value = 0
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4">
    <div class="w-full max-w-lg">
      <!-- Branding -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center space-x-2.5 mb-2">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/30" style="background: linear-gradient(135deg, #6366f1, #38bdf8);">
            <i class="fas fa-share-nodes text-white"></i>
          </div>
          <span class="text-2xl font-extrabold bg-gradient-to-r from-indigo-500 to-cyan-500 bg-clip-text text-transparent">YotoShare</span>
        </div>
        <h1 class="text-xl font-bold text-gray-800 dark:text-white mt-2">Soumettre une archive</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Partagez votre archive MYO avec la communauté</p>
      </div>

      <!-- Success state -->
      <div v-if="success" class="card p-8 text-center">
        <div class="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <i class="fas fa-check text-3xl text-green-600 dark:text-green-400"></i>
        </div>
        <h2 class="text-lg font-bold text-gray-800 dark:text-white mb-2">Merci !</h2>
        <p class="text-gray-600 dark:text-gray-400 mb-6">Votre archive a été soumise et sera examinée par un modérateur.</p>
        <button @click="reset" class="btn btn-primary">
          <i class="fas fa-plus mr-2"></i>
          Soumettre une autre archive
        </button>
      </div>

      <!-- Form -->
      <div v-else class="card p-6">
        <!-- Rework banner -->
        <div v-if="parentSubmissionId" class="mb-4 bg-orange-50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800 text-orange-700 dark:text-orange-400 px-4 py-3 rounded-lg text-sm">
          <i class="fas fa-redo mr-2"></i>
          Vous re-soumettez une archive retravaillée (soumission #{{ parentSubmissionId }})
        </div>

        <!-- Error -->
        <div v-if="error" class="mb-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg text-sm">
          <i class="fas fa-exclamation-circle mr-2"></i>
          {{ error }}
        </div>

        <!-- Upload progress -->
        <div v-if="uploading" class="mb-4">
          <div class="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-primary-700 dark:text-primary-300">
                <i class="fas fa-spinner fa-spin mr-2"></i>
                Envoi en cours...
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

        <!-- Drop zone -->
        <div
          v-if="!file && !uploading"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
          :class="[
            'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200',
            dragging
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-300 dark:border-gray-700 hover:border-primary-400 dark:hover:border-primary-600'
          ]"
          @click="$refs.fileInput.click()"
        >
          <i class="fas fa-cloud-upload-alt text-4xl text-gray-400 dark:text-gray-600 mb-3"></i>
          <p class="text-gray-600 dark:text-gray-400 font-medium">Glissez votre fichier .zip ici</p>
          <p class="text-sm text-gray-400 dark:text-gray-500 mt-1">ou cliquez pour parcourir (max 500 MB)</p>
          <input ref="fileInput" type="file" accept=".zip" class="hidden" @change="onFileInput">
        </div>

        <!-- File selected -->
        <div v-if="file && !uploading" class="border border-gray-200 dark:border-gray-700 rounded-xl p-4 flex items-center gap-3">
          <div class="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
            <i class="fas fa-file-archive text-primary-600 dark:text-primary-400"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-800 dark:text-white truncate">{{ file.name }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">{{ formatSize(file.size) }}</p>
          </div>
          <button @click="removeFile" class="text-gray-400 hover:text-red-500 transition-colors">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <!-- Pseudonym -->
        <div class="mt-4" v-if="!uploading">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Pseudonyme <span class="text-gray-400 font-normal">(optionnel)</span>
          </label>
          <input
            v-model="pseudonym"
            type="text"
            maxlength="255"
            placeholder="Votre pseudo"
            class="input"
          >
        </div>

        <!-- Submit button -->
        <button
          v-if="!uploading"
          @click="submit"
          :disabled="!file"
          class="btn btn-primary w-full mt-6"
          :class="{ 'opacity-50 cursor-not-allowed': !file }"
        >
          <i class="fas fa-paper-plane mr-2"></i>
          Soumettre
        </button>
      </div>
    </div>
  </div>
</template>
