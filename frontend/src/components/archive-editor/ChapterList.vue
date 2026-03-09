<template>
  <div class="chapter-list">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Chapitres</h3>
      <div class="flex gap-2">
        <button
          v-if="selectedChapters.length >= 2"
          @click="handleMerge"
          class="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
        >
          Fusionner ({{ selectedChapters.length }})
        </button>
        <button
          v-if="hasChanges"
          @click="saveChanges"
          :disabled="saving"
          class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {{ saving ? 'Enregistrement...' : 'Enregistrer' }}
        </button>
      </div>
    </div>

    <draggable
      v-model="localChapters"
      item-key="key"
      handle=".drag-handle"
      ghost-class="ghost"
      @change="onDragChange"
      class="space-y-2"
    >
      <template #item="{ element, index }">
        <div
          :class="[
            'chapter-item bg-white dark:bg-gray-800 border rounded-lg p-3 flex items-center gap-3 transition-all',
            selectedChapter?.key === element.key ? 'border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800' : 'border-gray-200 dark:border-gray-700',
            element.delete ? 'opacity-50 bg-red-50 dark:bg-red-900/30' : ''
          ]"
        >
          <!-- Drag handle -->
          <div class="drag-handle cursor-grab text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16" />
            </svg>
          </div>

          <!-- Checkbox for merge selection -->
          <input
            type="checkbox"
            :checked="selectedChapters.includes(element.key)"
            @change="toggleSelection(element.key)"
            class="w-4 h-4 text-blue-600 rounded"
          />

          <!-- Chapter icon -->
          <div class="w-8 h-8 bg-gray-100 dark:bg-gray-700 rounded flex items-center justify-center overflow-hidden">
            <img
              v-if="element.icon_file && !failedIcons.has(element.key)"
              :src="getIconUrl(element.key)"
              class="w-full h-full object-cover"
              @error="onIconError(element.key)"
            />
            <span v-else class="text-xs text-gray-400">{{ index + 1 }}</span>
          </div>

          <!-- Chapter info -->
          <div class="flex-1 min-w-0" @click="selectChapter(element)">
            <input
              v-if="editingKey === element.key"
              v-model="editingTitle"
              @blur="finishEditing"
              @keyup.enter="finishEditing"
              @keyup.escape="cancelEditing"
              class="w-full px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              ref="titleInput"
            />
            <div v-else class="cursor-pointer">
              <p class="text-sm font-medium text-gray-900 dark:text-white truncate" @dblclick="startEditing(element)">
                {{ element.title || 'Sans titre' }}
              </p>
              <p v-if="element.label" class="text-xs text-gray-500 truncate">
                {{ element.label }}
              </p>
            </div>
          </div>

          <!-- Duration -->
          <span class="text-xs text-gray-500 whitespace-nowrap">
            {{ formatDuration(element.duration) }}
          </span>

          <!-- Actions -->
          <div class="flex items-center gap-1">
            <button
              @click.stop="startEditing(element)"
              class="p-1.5 text-gray-400 hover:text-blue-600 rounded transition-colors"
              title="Renommer"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button
              @click.stop="toggleDelete(element)"
              :class="[
                'p-1.5 rounded transition-colors',
                element.delete ? 'text-red-600 bg-red-100' : 'text-gray-400 hover:text-red-600'
              ]"
              :title="element.delete ? 'Annuler suppression' : 'Supprimer'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </template>
    </draggable>

    <!-- Add chapter button -->
    <div class="mt-3">
      <div
        :class="[
          'border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer',
          isDraggingAudio
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-800'
        ]"
        @click="$refs.addAudioInput.click()"
        @dragover.prevent="isDraggingAudio = true"
        @dragleave.prevent="isDraggingAudio = false"
        @drop.prevent="handleAudioDrop"
      >
        <div v-if="addingChapter" class="flex items-center justify-center gap-2 text-blue-600">
          <i class="fas fa-spinner fa-spin"></i>
          <span class="text-sm">Ajout en cours...</span>
        </div>
        <div v-else>
          <i class="fas fa-plus text-gray-400 text-lg mb-1"></i>
          <p class="text-sm text-gray-500 dark:text-gray-400">Ajouter un chapitre</p>
          <p class="text-xs text-gray-400">Glissez un fichier audio ou cliquez</p>
        </div>
      </div>
      <input
        type="file"
        accept="audio/*"
        @change="handleAddAudio"
        class="hidden"
        ref="addAudioInput"
      />
    </div>

    <!-- Add chapter title modal -->
    <div v-if="showAddModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="cancelAdd">
      <div class="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Nouveau chapitre</h3>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Titre</label>
          <input
            v-model="addTitle"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Titre du chapitre..."
            @keyup.enter="confirmAdd"
          />
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          <i class="fas fa-file-audio mr-1"></i>
          {{ pendingAudioFile?.name }}
        </p>
        <div class="flex justify-end gap-2">
          <button
            @click="cancelAdd"
            class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            Annuler
          </button>
          <button
            @click="confirmAdd"
            :disabled="!addTitle.trim() || addingChapter"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Ajouter
          </button>
        </div>
      </div>
    </div>

    <!-- Merge modal -->
    <div v-if="showMergeModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showMergeModal = false">
      <div class="bg-white rounded-xl p-6 max-w-md w-full mx-4">
        <h3 class="text-lg font-semibold mb-4">Fusionner les chapitres</h3>
        <p class="text-sm text-gray-600 mb-4">
          Fusionner {{ selectedChapters.length }} chapitres en un seul.
        </p>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Titre du nouveau chapitre</label>
          <input
            v-model="mergeTitle"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Titre..."
          />
        </div>
        <div class="flex justify-end gap-2">
          <button
            @click="showMergeModal = false"
            class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Annuler
          </button>
          <button
            @click="confirmMerge"
            :disabled="!mergeTitle.trim() || merging"
            class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {{ merging ? 'Fusion...' : 'Fusionner' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import draggable from 'vuedraggable'
import { useArchivesStore } from '../../stores/archives'

const props = defineProps({
  archiveId: { type: Number, required: true },
  chapters: { type: Array, required: true },
  selectedChapter: { type: Object, default: null }
})

const emit = defineEmits(['select', 'update', 'refresh'])

const store = useArchivesStore()
const localChapters = ref([])
const hasChanges = ref(false)
const saving = ref(false)
const editingKey = ref(null)
const editingTitle = ref('')
const titleInput = ref(null)
const selectedChapters = ref([])
const showMergeModal = ref(false)
const mergeTitle = ref('')
const merging = ref(false)
const iconCacheBuster = ref(Date.now())
const failedIcons = ref(new Set())
const addAudioInput = ref(null)
const isDraggingAudio = ref(false)
const addingChapter = ref(false)
const showAddModal = ref(false)
const addTitle = ref('')
const pendingAudioFile = ref(null)

watch(() => props.chapters, (newChapters) => {
  localChapters.value = newChapters.map((ch, i) => ({
    ...ch,
    order: i,
    delete: false
  }))
  hasChanges.value = false
  // Update cache buster to refresh icons
  iconCacheBuster.value = Date.now()
  failedIcons.value = new Set()
}, { immediate: true, deep: true })

function getIconUrl(chapterKey) {
  return `${store.getChapterIconUrl(props.archiveId, chapterKey)}?t=${iconCacheBuster.value}`
}

function onIconError(key) {
  failedIcons.value.add(key)
  failedIcons.value = new Set(failedIcons.value) // trigger reactivity
}

function formatDuration(ms) {
  if (!ms) return '--:--'
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function selectChapter(chapter) {
  if (editingKey.value) return
  emit('select', chapter)
}

function startEditing(chapter) {
  editingKey.value = chapter.key
  editingTitle.value = chapter.title || ''
  nextTick(() => {
    titleInput.value?.focus()
  })
}

function finishEditing() {
  if (!editingKey.value) return
  const chapter = localChapters.value.find(ch => ch.key === editingKey.value)
  if (chapter && chapter.title !== editingTitle.value) {
    chapter.title = editingTitle.value
    hasChanges.value = true
  }
  editingKey.value = null
  editingTitle.value = ''
}

function cancelEditing() {
  editingKey.value = null
  editingTitle.value = ''
}

function toggleDelete(chapter) {
  chapter.delete = !chapter.delete
  hasChanges.value = true
}

function onDragChange() {
  localChapters.value.forEach((ch, i) => {
    ch.order = i
  })
  hasChanges.value = true
}

function toggleSelection(key) {
  const index = selectedChapters.value.indexOf(key)
  if (index === -1) {
    selectedChapters.value.push(key)
  } else {
    selectedChapters.value.splice(index, 1)
  }
}

function handleMerge() {
  // Get first selected chapter title as default
  const firstKey = selectedChapters.value[0]
  const firstChapter = localChapters.value.find(ch => ch.key === firstKey)
  mergeTitle.value = firstChapter?.title || 'Chapitre fusionné'
  showMergeModal.value = true
}

async function confirmMerge() {
  if (!mergeTitle.value.trim()) return
  merging.value = true
  try {
    // Ensure keys are in order
    const orderedKeys = localChapters.value
      .filter(ch => selectedChapters.value.includes(ch.key))
      .map(ch => ch.key)

    await store.mergeChapters(props.archiveId, orderedKeys, mergeTitle.value.trim())
    showMergeModal.value = false
    selectedChapters.value = []
    emit('refresh')
  } catch (e) {
    console.error('Merge failed:', e)
    alert('Erreur lors de la fusion: ' + e.message)
  } finally {
    merging.value = false
  }
}

function handleAddAudio(event) {
  const file = event.target.files?.[0]
  if (!file) return
  promptAddChapter(file)
  event.target.value = ''
}

function handleAudioDrop(event) {
  isDraggingAudio.value = false
  const file = event.dataTransfer.files?.[0]
  if (file && file.type.startsWith('audio/')) {
    promptAddChapter(file)
  }
}

function promptAddChapter(file) {
  pendingAudioFile.value = file
  // Default title from filename without extension
  addTitle.value = file.name.replace(/\.[^/.]+$/, '')
  showAddModal.value = true
}

function cancelAdd() {
  showAddModal.value = false
  pendingAudioFile.value = null
  addTitle.value = ''
}

async function confirmAdd() {
  if (!addTitle.value.trim() || !pendingAudioFile.value) return
  showAddModal.value = false
  addingChapter.value = true
  try {
    const formData = new FormData()
    formData.append('audio_file', pendingAudioFile.value)
    formData.append('title', addTitle.value.trim())
    await store.addChapter(props.archiveId, formData)
    emit('refresh')
  } catch (e) {
    console.error('Add chapter failed:', e)
    alert('Erreur lors de l\'ajout: ' + (e.response?.data?.detail || e.message))
  } finally {
    addingChapter.value = false
    pendingAudioFile.value = null
    addTitle.value = ''
  }
}

async function saveChanges() {
  saving.value = true
  try {
    const updates = localChapters.value.map(ch => ({
      key: ch.key,
      title: ch.title,
      label: ch.label,
      order: ch.order,
      delete: ch.delete
    }))
    await store.updateChapters(props.archiveId, updates)
    hasChanges.value = false
    emit('refresh')
  } catch (e) {
    console.error('Save failed:', e)
    alert('Erreur lors de l\'enregistrement: ' + e.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ghost {
  opacity: 0.5;
  background: #e0e7ff;
}

.chapter-item {
  transition: all 0.2s ease;
}

.drag-handle:active {
  cursor: grabbing;
}
</style>
