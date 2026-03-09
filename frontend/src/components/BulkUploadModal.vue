<script setup>
import { ref, computed } from 'vue'
import { useArchivesStore } from '../stores/archives'
import TagInput from './TagInput.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  categories: {
    type: Array,
    default: () => [],
  },
  ages: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'complete'])

const archivesStore = useArchivesStore()

const files = ref([])
const selectedCategories = ref([])
const selectedAges = ref([])
const uploading = ref(false)
const done = ref(false)
const isDragOver = ref(false)
const fileInputRef = ref(null)

const pendingCount = computed(() => files.value.filter(f => f.status === 'pending').length)
const successCount = computed(() => files.value.filter(f => f.status === 'success').length)
const errorCount = computed(() => files.value.filter(f => f.status === 'error').length)
const progress = computed(() => {
  if (files.value.length === 0) return 0
  const processed = successCount.value + errorCount.value
  return Math.round((processed / files.value.length) * 100)
})

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function addFiles(newFiles) {
  for (const file of newFiles) {
    if (!file.name.toLowerCase().endsWith('.zip')) continue
    const duplicate = files.value.some(f => f.file.name === file.name && f.file.size === file.size)
    if (duplicate) continue
    files.value.push({
      file,
      status: 'pending',
      error: null,
      progress: 0,
    })
  }
}

function removeFile(index) {
  if (uploading.value) return
  files.value.splice(index, 1)
}

function handleDragOver(e) {
  e.preventDefault()
  isDragOver.value = true
}

function handleDragLeave() {
  isDragOver.value = false
}

function handleDrop(e) {
  e.preventDefault()
  isDragOver.value = false
  if (uploading.value || done.value) return
  addFiles(e.dataTransfer.files)
}

function handleFileInput(e) {
  addFiles(e.target.files)
  e.target.value = ''
}

function openFilePicker() {
  if (uploading.value || done.value) return
  fileInputRef.value?.click()
}

async function startUpload() {
  if (files.value.length === 0 || uploading.value) return
  uploading.value = true

  for (const entry of files.value) {
    if (entry.status !== 'pending') continue
    entry.status = 'uploading'

    try {
      const formData = new FormData()
      formData.append('archive_file', entry.file)
      if (selectedCategories.value.length > 0) {
        formData.append('categories', JSON.stringify(selectedCategories.value))
      }
      if (selectedAges.value.length > 0) {
        formData.append('ages', JSON.stringify(selectedAges.value))
      }
      await archivesStore.createArchive(formData, {
        onUploadProgress(e) {
          if (e.total) {
            entry.progress = Math.round((e.loaded / e.total) * 100)
          }
        },
      })
      entry.progress = 100
      entry.status = 'success'
    } catch (e) {
      entry.status = 'error'
      entry.error = e.response?.data?.detail || e.message || 'Erreur inconnue'
    }
  }

  uploading.value = false
  done.value = true
}

function handleClose() {
  if (uploading.value) return
  const hadSuccess = successCount.value > 0
  files.value = []
  selectedCategories.value = []
  selectedAges.value = []
  uploading.value = false
  done.value = false
  isDragOver.value = false
  emit('close')
  if (hadSuccess) {
    emit('complete')
  }
}

function handleCloseAfterDone() {
  const hadSuccess = successCount.value > 0
  files.value = []
  selectedCategories.value = []
  selectedAges.value = []
  uploading.value = false
  done.value = false
  isDragOver.value = false
  emit('close')
  if (hadSuccess) {
    emit('complete')
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        class="absolute inset-0 bg-black bg-opacity-50"
        @click="handleClose"
      ></div>

      <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <button
          @click="handleClose"
          :disabled="uploading"
          class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
        >
          <i class="fas fa-times"></i>
        </button>

        <h3 class="text-xl font-semibold text-gray-800 dark:text-white mb-4">
          <i class="fas fa-file-import text-primary-600 mr-2"></i>
          Import en masse
        </h3>

        <!-- Drop zone -->
        <div
          v-if="!done"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @drop="handleDrop"
          @click="openFilePicker"
          :class="[
            'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors mb-4',
            isDragOver
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 hover:bg-gray-50 dark:hover:bg-gray-700/50',
            (uploading) ? 'pointer-events-none opacity-50' : ''
          ]"
        >
          <i class="fas fa-cloud-upload-alt text-4xl text-gray-400 dark:text-gray-500 mb-3"></i>
          <p class="text-gray-600 dark:text-gray-400">
            Glissez-déposez vos fichiers <strong>.zip</strong> ici
          </p>
          <p class="text-sm text-gray-400 dark:text-gray-500 mt-1">
            ou cliquez pour parcourir
          </p>
          <input
            ref="fileInputRef"
            type="file"
            multiple
            accept=".zip"
            class="hidden"
            @change="handleFileInput"
          />
        </div>

        <!-- File list -->
        <div v-if="files.length > 0" class="mb-4">
          <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Fichiers ({{ files.length }})
          </h4>
          <div class="space-y-2 max-h-60 overflow-y-auto">
            <div
              v-for="(entry, index) in files"
              :key="index"
              class="flex items-center gap-3 px-3 py-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
            >
              <i
                :class="{
                  'fas fa-clock text-gray-400': entry.status === 'pending',
                  'fas fa-spinner fa-spin text-primary-500': entry.status === 'uploading',
                  'fas fa-check-circle text-green-500': entry.status === 'success',
                  'fas fa-exclamation-circle text-red-500': entry.status === 'error',
                }"
              ></i>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                  <p class="text-sm text-gray-800 dark:text-gray-200 truncate">
                    {{ entry.file.name }}
                  </p>
                  <span class="text-xs text-gray-400 whitespace-nowrap ml-2">
                    {{ entry.status === 'uploading' ? entry.progress + '% · ' : '' }}{{ formatSize(entry.file.size) }}
                  </span>
                </div>
                <div v-if="entry.status === 'uploading'" class="mt-1 w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                  <div
                    class="h-1.5 rounded-full bg-primary-500 transition-all duration-300 ease-out"
                    :style="{ width: entry.progress + '%' }"
                  ></div>
                </div>
                <p v-if="entry.error" class="text-xs text-red-500 truncate mt-1">
                  {{ entry.error }}
                </p>
              </div>
              <button
                v-if="entry.status === 'pending' && !uploading"
                @click.stop="removeFile(index)"
                class="text-gray-400 hover:text-red-500"
              >
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Progress bar -->
        <div v-if="uploading || done" class="mb-4">
          <div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
            <span>Progression</span>
            <span>{{ progress }}%</span>
          </div>
          <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
            <div
              class="h-2.5 rounded-full transition-all duration-300"
              :class="errorCount > 0 && done ? 'bg-yellow-500' : 'bg-primary-600'"
              :style="{ width: progress + '%' }"
            ></div>
          </div>
          <div v-if="done" class="flex gap-4 mt-2 text-sm">
            <span v-if="successCount > 0" class="text-green-600 dark:text-green-400">
              <i class="fas fa-check-circle mr-1"></i>{{ successCount }} importé{{ successCount > 1 ? 's' : '' }}
            </span>
            <span v-if="errorCount > 0" class="text-red-600 dark:text-red-400">
              <i class="fas fa-exclamation-circle mr-1"></i>{{ errorCount }} échoué{{ errorCount > 1 ? 's' : '' }}
            </span>
          </div>
        </div>

        <!-- Common metadata -->
        <div v-if="!done && files.length > 0" class="mb-4 space-y-3">
          <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300">
            Métadonnées communes (optionnel)
          </h4>
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">
              <i class="fas fa-folder mr-1"></i>Catégories
            </label>
            <TagInput
              v-model="selectedCategories"
              :suggestions="categories"
              placeholder="Ajouter une catégorie..."
              icon="fas fa-folder"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">
              <i class="fas fa-child mr-1"></i>Âges
            </label>
            <TagInput
              v-model="selectedAges"
              :suggestions="ages"
              placeholder="Ajouter un âge..."
              icon="fas fa-child"
            />
          </div>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-3">
          <template v-if="done">
            <button @click="handleCloseAfterDone" class="btn btn-primary">
              <i class="fas fa-check mr-2"></i>
              Fermer
            </button>
          </template>
          <template v-else>
            <button
              @click="handleClose"
              class="btn btn-secondary"
              :disabled="uploading"
            >
              Annuler
            </button>
            <button
              @click="startUpload"
              class="btn btn-primary"
              :disabled="pendingCount === 0 || uploading"
            >
              <i v-if="uploading" class="fas fa-spinner fa-spin mr-2"></i>
              <i v-else class="fas fa-upload mr-2"></i>
              Importer {{ pendingCount }} fichier{{ pendingCount > 1 ? 's' : '' }}
            </button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>
