<script setup>
import { ref } from 'vue'
import { usePacksStore } from '../stores/packs'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  selectedArchives: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'created'])

const packsStore = usePacksStore()

const packName = ref('')
const packDescription = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleSubmit() {
  if (!packName.value.trim()) return
  loading.value = true
  errorMsg.value = ''

  try {
    const pack = await packsStore.createPack({
      name: packName.value.trim(),
      description: packDescription.value.trim() || null,
      archive_ids: props.selectedArchives.map(a => a.id),
    })

    // Copy share URL to clipboard
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(pack.share_url)
      } catch (_) {
        // Clipboard not available
      }
    }

    emit('created', pack)
    handleClose()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Erreur lors de la création du pack'
  } finally {
    loading.value = false
  }
}

function handleClose() {
  packName.value = ''
  packDescription.value = ''
  errorMsg.value = ''
  emit('close')
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

      <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <button
          @click="handleClose"
          :disabled="loading"
          class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
        >
          <i class="fas fa-times"></i>
        </button>

        <h3 class="text-xl font-semibold text-gray-800 dark:text-white mb-4">
          <i class="fas fa-box-open text-primary-600 mr-2"></i>
          Créer un pack de partage
        </h3>

        <!-- Error -->
        <div v-if="errorMsg" class="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg text-sm">
          {{ errorMsg }}
        </div>

        <!-- Pack name -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Nom du pack *
          </label>
          <input
            v-model="packName"
            type="text"
            class="input w-full"
            placeholder="Mon super pack..."
            maxlength="255"
            :disabled="loading"
          />
        </div>

        <!-- Description -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description
          </label>
          <textarea
            v-model="packDescription"
            class="input w-full"
            rows="3"
            placeholder="Un pack d'histoires audio à écouter sur ta Yoto !"
            :disabled="loading"
          ></textarea>
        </div>

        <!-- Archives preview -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Archives sélectionnées ({{ selectedArchives.length }})
          </label>
          <div class="space-y-2 max-h-48 overflow-y-auto">
            <div
              v-for="archive in selectedArchives"
              :key="archive.id"
              class="flex items-center gap-3 px-3 py-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
            >
              <img
                v-if="archive.cover_path"
                :src="`/api/archives/cover/${archive.cover_path}`"
                :alt="archive.title"
                class="w-10 h-14 object-cover rounded flex-shrink-0"
              />
              <div
                v-else
                class="w-10 h-14 bg-gray-200 dark:bg-gray-600 rounded flex-shrink-0 flex items-center justify-center"
              >
                <i class="fas fa-book text-gray-400 text-sm"></i>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-gray-800 dark:text-gray-200 truncate">{{ archive.title }}</p>
                <p v-if="archive.author" class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ archive.author }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3">
          <button
            @click="handleSubmit"
            :disabled="loading || !packName.trim()"
            class="btn btn-primary flex-1"
          >
            <i :class="loading ? 'fas fa-spinner fa-spin' : 'fas fa-share-alt'" class="mr-2"></i>
            {{ loading ? 'Création...' : 'Créer et copier le lien' }}
          </button>
          <button @click="handleClose" class="btn btn-secondary" :disabled="loading">
            Annuler
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
