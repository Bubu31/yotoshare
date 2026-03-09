<template>
  <div class="nfo-editor">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">Fichier NFO (signature.nfo)</h3>
      <button
        v-if="hasChanges"
        @click="saveNfo"
        :disabled="saving"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {{ saving ? 'Enregistrement...' : 'Enregistrer' }}
      </button>
    </div>

    <div class="grid md:grid-cols-2 gap-6">
      <!-- Editor -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">Édition</label>
        <textarea
          v-model="content"
          class="w-full h-96 px-3 py-2 font-mono text-sm bg-gray-50 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          placeholder="Contenu du fichier NFO..."
          @input="hasChanges = true"
        ></textarea>
        <p class="text-xs text-gray-500 mt-1">
          Le fichier NFO est généralement utilisé pour stocker des informations sur l'archive (signature, crédits, etc.)
        </p>
      </div>

      <!-- Preview -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">Aperçu</label>
        <div class="h-96 bg-black text-green-400 font-mono text-xs p-4 rounded-lg overflow-auto whitespace-pre">{{ content || '(vide)' }}</div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex items-center justify-center py-8">
      <svg class="w-6 h-6 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useArchivesStore } from '../../stores/archives'

const props = defineProps({
  archiveId: { type: Number, required: true }
})

const emit = defineEmits(['saved'])

const store = useArchivesStore()
const content = ref('')
const originalContent = ref('')
const loading = ref(false)
const saving = ref(false)
const hasChanges = ref(false)

async function loadNfo() {
  loading.value = true
  try {
    const nfoContent = await store.getNfo(props.archiveId)
    content.value = nfoContent || ''
    originalContent.value = content.value
    hasChanges.value = false
  } catch (e) {
    console.error('Failed to load NFO:', e)
  } finally {
    loading.value = false
  }
}

async function saveNfo() {
  saving.value = true
  try {
    await store.updateNfo(props.archiveId, content.value)
    originalContent.value = content.value
    hasChanges.value = false
    emit('saved')
  } catch (e) {
    console.error('Failed to save NFO:', e)
    alert('Erreur lors de l\'enregistrement: ' + e.message)
  } finally {
    saving.value = false
  }
}

watch(() => props.archiveId, () => {
  loadNfo()
})

onMounted(() => {
  loadNfo()
})
</script>
