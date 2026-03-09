<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useArchivesStore } from '../stores/archives'
import { useAuthStore } from '../stores/auth'
import { useVisualsStore } from '../stores/visuals'
import { useMessage } from '../composables/useMessage'
import api from '../services/api'
import ArchiveCard from '../components/ArchiveCard.vue'
import AlertMessage from '../components/AlertMessage.vue'
import PublishModal from '../components/PublishModal.vue'
import BulkUploadModal from '../components/BulkUploadModal.vue'
import CreatePackModal from '../components/CreatePackModal.vue'
import ThemeAutocomplete from '../components/ThemeAutocomplete.vue'

const router = useRouter()
const archivesStore = useArchivesStore()
const authStore = useAuthStore()
const visualsStore = useVisualsStore()
const { message, showMessage } = useMessage()

const selectedArchive = ref(null)
const showPublishModal = ref(false)
const showBulkUploadModal = ref(false)
const showShareModal = ref(false)
const shareUrl = ref('')

// Selection mode for packs
const selectionMode = ref(false)
const selectedIds = ref(new Set())
const showCreatePackModal = ref(false)

const selectedArchiveObjects = computed(() => {
  return sortedArchives.value.filter(a => selectedIds.value.has(a.id))
})

function toggleSelectionMode() {
  selectionMode.value = !selectionMode.value
  if (!selectionMode.value) {
    selectedIds.value = new Set()
  }
}

function toggleSelect(archive) {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(archive.id)) {
    newSet.delete(archive.id)
  } else {
    newSet.add(archive.id)
  }
  selectedIds.value = newSet
}

function selectAll() {
  selectedIds.value = new Set(sortedArchives.value.map(a => a.id))
}

function deselectAll() {
  selectedIds.value = new Set()
}

function openCreatePackModal() {
  if (selectedIds.value.size === 0) return
  showCreatePackModal.value = true
}

function handlePackCreated() {
  showMessage('success', 'Pack créé ! Lien copié dans le presse-papier')
  selectionMode.value = false
  selectedIds.value = new Set()
}

// Add to gallery modal
const showGalleryModal = ref(false)
const galleryArchive = ref(null)
const galleryAuthor = ref(localStorage.getItem('visual_submitter') || '')
const galleryThemeIds = ref([])
const galleryLoading = ref(false)

// Add icons to gallery modal
const showIconGalleryModal = ref(false)
const iconGalleryArchive = ref(null)
const iconGalleryAuthor = ref(localStorage.getItem('visual_submitter') || '')
const iconGalleryItems = ref([])
const iconGalleryLoading = ref(false)

const searchQuery = ref('')
const sortBy = ref(localStorage.getItem('archives_sortBy') || 'date-desc')
const filterCategory = ref(JSON.parse(localStorage.getItem('archives_filterCategory')) || null)
const filterAge = ref(JSON.parse(localStorage.getItem('archives_filterAge')) || null)
const hidePublished = ref(localStorage.getItem('archives_hidePublished') === 'true')
let searchTimeout = null

watch(sortBy, v => localStorage.setItem('archives_sortBy', v))
watch(filterCategory, v => localStorage.setItem('archives_filterCategory', JSON.stringify(v)))
watch(filterAge, v => localStorage.setItem('archives_filterAge', JSON.stringify(v)))
watch(hidePublished, v => localStorage.setItem('archives_hidePublished', v))

const filteredArchives = computed(() => {
  let list = archivesStore.archives
  if (hidePublished.value) {
    list = list.filter(a => !a.discord_post_id)
  }
  return list
})

const sortedArchives = computed(() => {
  const list = [...filteredArchives.value]
  switch (sortBy.value) {
    case 'alpha-asc':
      return list.sort((a, b) => (a.title || '').localeCompare(b.title || ''))
    case 'alpha-desc':
      return list.sort((a, b) => (b.title || '').localeCompare(a.title || ''))
    case 'date-asc':
      return list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    case 'downloads-desc':
      return list.sort((a, b) => (b.download_count || 0) - (a.download_count || 0))
    case 'downloads-asc':
      return list.sort((a, b) => (a.download_count || 0) - (b.download_count || 0))
    case 'date-desc':
    default:
      return list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  }
})

function debouncedFetch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    archivesStore.fetchArchives(
      filterCategory.value || null,
      filterAge.value || null,
      searchQuery.value || null
    )
  }, 300)
}

watch(searchQuery, debouncedFetch)
watch(filterCategory, debouncedFetch)
watch(filterAge, debouncedFetch)

onMounted(async () => {
  await Promise.all([
    archivesStore.fetchCategories(),
    archivesStore.fetchAges(),
    archivesStore.fetchArchives(filterCategory.value || null, filterAge.value || null),
    visualsStore.fetchThemes(),
  ])
})

onUnmounted(() => clearTimeout(searchTimeout))

function handleEdit(archive) {
  router.push(`/archives/edit/${archive.id}`)
}

async function handleDelete(archive) {
  if (!confirm(`Supprimer "${archive.title}" ?`)) return

  try {
    await archivesStore.deleteArchive(archive.id)
    showMessage('success', 'Archive supprimée')
  } catch (e) {
    showMessage('error', 'Erreur lors de la suppression')
  }
}

async function handleShare(archive) {
  try {
    const url = await archivesStore.generateShareLink(archive.id)

    // Try clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(url)
        showMessage('success', 'Lien copié ! Expire dans 30 jours')
        return
      } catch (clipboardError) {
        // Clipboard API not available, fall through to modal
      }
    }

    // Fallback: show modal with link to copy manually
    shareUrl.value = url
    showShareModal.value = true
  } catch (e) {
    console.error('[Share] Error generating link:', e)
    showMessage('error', 'Erreur lors de la génération du lien')
  }
}

async function copyShareUrl() {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    showShareModal.value = false
    showMessage('success', 'Lien copié !')
  } catch (e) {
    // Select the text so user can copy manually
    showMessage('info', 'Sélectionnez et copiez le lien manuellement')
  }
}

function handlePublish(archive) {
  selectedArchive.value = archive
  showPublishModal.value = true
}

async function confirmPublish(archive) {
  try {
    const result = await archivesStore.publishToDiscord(archive.id)
    showPublishModal.value = false
    if (result.success) {
      showMessage('success', 'Publié sur Discord')
    } else {
      showMessage('error', result.message || 'Erreur inconnue')
    }
  } catch (e) {
    showPublishModal.value = false
    console.error('[Publish] Error:', e)
    showMessage('error', e.response?.data?.message || e.message || 'Erreur lors de la publication')
  }
}

async function handleBulkUploadComplete() {
  await archivesStore.fetchArchives()
  showMessage('success', 'Import en masse terminé')
}

function handleAddToGallery(archive) {
  galleryArchive.value = archive
  galleryAuthor.value = localStorage.getItem('visual_submitter') || ''
  galleryThemeIds.value = []
  showGalleryModal.value = true
}

function closeGalleryModal() {
  showGalleryModal.value = false
  galleryArchive.value = null
  galleryThemeIds.value = []
}

async function confirmAddToGallery() {
  if (!galleryArchive.value?.cover_path) return
  galleryLoading.value = true
  try {
    const coverUrl = `/api/archives/cover/${galleryArchive.value.cover_path}`
    const response = await fetch(coverUrl)
    const blob = await response.blob()
    const file = new File([blob], `${galleryArchive.value.title || 'cover'}.jpg`, { type: blob.type })

    const formData = new FormData()
    formData.append('image', file)
    formData.append('title', galleryArchive.value.title || '')
    if (galleryAuthor.value.trim()) {
      formData.append('author', galleryAuthor.value.trim())
      localStorage.setItem('visual_submitter', galleryAuthor.value.trim())
    }
    if (galleryThemeIds.value.length) {
      formData.append('theme_ids', galleryThemeIds.value.join(','))
    }

    await visualsStore.uploadVisual(formData)
    closeGalleryModal()
    showMessage('success', 'Visuel ajouté à la galerie')
  } catch (e) {
    showMessage('error', e.response?.data?.detail || 'Erreur lors de l\'ajout à la galerie')
  } finally {
    galleryLoading.value = false
  }
}

async function onGalleryThemeCreated(name) {
  try {
    const theme = await visualsStore.getOrCreateTheme(name)
    galleryThemeIds.value = [...galleryThemeIds.value, theme.id]
  } catch (e) {
    showMessage('error', 'Erreur lors de la création du thème')
  }
}

async function handleAddIconsToGallery(archive) {
  iconGalleryArchive.value = archive
  iconGalleryAuthor.value = localStorage.getItem('visual_submitter') || ''
  iconGalleryItems.value = []
  iconGalleryLoading.value = true
  showIconGalleryModal.value = true

  try {
    const response = await api.get(`/api/archives/${archive.id}/content`)
    const chapters = response.data.chapters || []
    iconGalleryItems.value = chapters
      .filter(ch => ch.icon_file)
      .map(ch => ({
        chapterKey: ch.key,
        title: ch.title || ch.key,
        keywords: '',
        included: true,
      }))
  } catch (e) {
    showMessage('error', 'Erreur lors du chargement des chapitres')
    showIconGalleryModal.value = false
  } finally {
    iconGalleryLoading.value = false
  }
}

function closeIconGalleryModal() {
  showIconGalleryModal.value = false
  iconGalleryArchive.value = null
  iconGalleryItems.value = []
}

function toggleIconIncluded(index) {
  iconGalleryItems.value[index].included = !iconGalleryItems.value[index].included
}

const includedIconCount = computed(() => iconGalleryItems.value.filter(i => i.included).length)

async function confirmAddIconsToGallery() {
  const items = iconGalleryItems.value.filter(i => i.included)
  if (!items.length) return

  iconGalleryLoading.value = true
  let successCount = 0

  try {
    if (iconGalleryAuthor.value.trim()) {
      localStorage.setItem('visual_submitter', iconGalleryAuthor.value.trim())
    }

    for (const item of items) {
      try {
        const iconUrl = `/api/archives/${iconGalleryArchive.value.id}/chapters/${item.chapterKey}/icon`
        const response = await fetch(iconUrl)
        if (!response.ok) continue

        const blob = await response.blob()
        const file = new File([blob], `${item.title}.png`, { type: 'image/png' })

        const formData = new FormData()
        formData.append('image', file)
        formData.append('type', 'icon')
        formData.append('title', item.title)
        if (iconGalleryAuthor.value.trim()) {
          formData.append('author', iconGalleryAuthor.value.trim())
        }
        if (item.keywords.trim()) {
          formData.append('keywords', item.keywords.trim())
        }

        await visualsStore.uploadVisual(formData)
        successCount++
      } catch (e) {
        console.error(`[IconGallery] Failed to upload icon for ${item.chapterKey}:`, e)
      }
    }

    closeIconGalleryModal()
    if (successCount > 0) {
      showMessage('success', `${successCount} icône${successCount > 1 ? 's' : ''} ajoutée${successCount > 1 ? 's' : ''} à la galerie`)
    } else {
      showMessage('error', 'Aucune icône n\'a pu être ajoutée')
    }
  } catch (e) {
    showMessage('error', 'Erreur lors de l\'ajout des icônes')
  } finally {
    iconGalleryLoading.value = false
  }
}

</script>

<template>
  <div>
    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6 md:mb-8">
      <div>
        <h1 class="text-2xl md:text-3xl font-bold text-gray-800 dark:text-white">
          <i class="fas fa-book text-primary-600 mr-2"></i>
          Archives
        </h1>
        <p class="text-sm md:text-base text-gray-600 dark:text-gray-400">Gérez vos archives audio</p>
      </div>
      <div class="flex flex-wrap gap-2 sm:gap-3">
        <button
          v-if="authStore.hasPermission('packs', 'access')"
          @click="toggleSelectionMode"
          :class="selectionMode ? 'btn btn-primary' : 'btn btn-secondary'"
          class="text-sm sm:text-base"
        >
          <i class="fas fa-check-square mr-1 sm:mr-2"></i>
          <span class="hidden sm:inline">{{ selectionMode ? 'Annuler' : 'Sélectionner' }}</span>
          <span class="sm:hidden">{{ selectionMode ? 'Annuler' : 'Sélect.' }}</span>
        </button>
        <button @click="showBulkUploadModal = true" class="btn btn-secondary text-sm sm:text-base">
          <i class="fas fa-file-import mr-1 sm:mr-2"></i>
          <span class="hidden sm:inline">Import en masse</span>
          <span class="sm:hidden">Import</span>
        </button>
        <router-link to="/archives/upload" class="btn btn-primary text-sm sm:text-base">
          <i class="fas fa-plus mr-1 sm:mr-2"></i>
          <span class="hidden sm:inline">Nouvelle archive</span>
          <span class="sm:hidden">Nouveau</span>
        </router-link>
      </div>
    </div>

    <AlertMessage :message="message" />

    <div>
      <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-4">
        <h2 class="text-xl font-semibold text-gray-800 dark:text-white">
          <i class="fas fa-book mr-2"></i>
          Archives ({{ filteredArchives.length }}{{ hidePublished ? ` / ${archivesStore.archives.length}` : '' }})
        </h2>
        <div class="flex flex-col sm:flex-row gap-2 sm:gap-3 sm:items-center">
          <div class="relative">
            <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
            <input
              v-model="searchQuery"
              type="text"
              class="input pl-9 w-full sm:w-48 md:w-64"
              placeholder="Rechercher..."
            />
          </div>
          <div class="flex gap-2">
            <select v-model="filterCategory" class="input w-full sm:w-auto text-sm">
              <option :value="null">Catégories</option>
              <option v-for="cat in archivesStore.categories" :key="cat.id" :value="cat.id">
                {{ cat.name }}
              </option>
            </select>
            <select v-model="filterAge" class="input w-full sm:w-auto text-sm">
              <option :value="null">Âges</option>
              <option v-for="age in archivesStore.ages" :key="age.id" :value="age.id">
                {{ age.name }}
              </option>
            </select>
            <select v-model="sortBy" class="input w-full sm:w-auto text-sm">
              <option value="date-desc">Récentes</option>
              <option value="date-asc">Anciennes</option>
              <option value="alpha-asc">A → Z</option>
              <option value="alpha-desc">Z → A</option>
              <option value="downloads-desc">DL (+ → -)</option>
              <option value="downloads-asc">DL (- → +)</option>
            </select>
          </div>
          <label class="flex items-center gap-2 cursor-pointer whitespace-nowrap select-none">
            <div class="relative">
              <input type="checkbox" v-model="hidePublished" class="sr-only peer" />
              <div class="w-9 h-5 bg-gray-300 dark:bg-gray-600 rounded-full peer-checked:bg-primary-600 transition-colors"></div>
              <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow peer-checked:translate-x-4 transition-transform"></div>
            </div>
            <span class="text-sm text-gray-600 dark:text-gray-400">
              <i class="fab fa-discord mr-1"></i>Non publiés
            </span>
          </label>
        </div>
      </div>

      <div v-if="archivesStore.loading" class="text-center py-12">
        <i class="fas fa-spinner fa-spin text-4xl text-primary-600"></i>
      </div>

      <div v-else-if="archivesStore.archives.length === 0" class="text-center py-12 card">
        <i class="fas fa-inbox text-6xl text-gray-300 dark:text-gray-600"></i>
        <p class="mt-4 text-gray-500 dark:text-gray-400">Aucune archive</p>
        <router-link to="/archives/upload" class="btn btn-primary mt-4 inline-block">
          <i class="fas fa-plus mr-2"></i>
          Ajouter une archive
        </router-link>
      </div>

      <div v-else class="grid gap-4">
        <ArchiveCard
          v-for="archive in sortedArchives"
          :key="archive.id"
          :archive="archive"
          :show-actions="!selectionMode"
          :selection-mode="selectionMode"
          :selected="selectedIds.has(archive.id)"
          @edit="handleEdit"
          @delete="handleDelete"
          @share="handleShare"
          @publish="handlePublish"
          @add-to-gallery="handleAddToGallery"
          @add-icons-to-gallery="handleAddIconsToGallery"
          @toggle-select="toggleSelect"
        />
      </div>
    </div>

    <PublishModal
      v-if="selectedArchive"
      :item="selectedArchive"
      :is-open="showPublishModal"
      @close="showPublishModal = false"
      @confirm="confirmPublish"
    />

    <BulkUploadModal
      :is-open="showBulkUploadModal"
      :categories="archivesStore.categories"
      :ages="archivesStore.ages"
      @close="showBulkUploadModal = false"
      @complete="handleBulkUploadComplete"
    />

    <CreatePackModal
      :is-open="showCreatePackModal"
      :selected-archives="selectedArchiveObjects"
      @close="showCreatePackModal = false"
      @created="handlePackCreated"
    />

    <!-- Selection mode floating bar -->
    <Teleport to="body">
      <div
        v-if="selectionMode"
        class="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-gray-800 dark:bg-gray-700 text-white rounded-xl shadow-2xl px-6 py-3 flex items-center gap-4"
      >
        <span class="text-sm font-medium">
          {{ selectedIds.size }} sélectionnée{{ selectedIds.size > 1 ? 's' : '' }}
        </span>
        <button
          @click="selectedIds.size === sortedArchives.length ? deselectAll() : selectAll()"
          class="text-sm text-primary-400 hover:text-primary-300 transition-colors"
        >
          {{ selectedIds.size === sortedArchives.length ? 'Tout désélectionner' : 'Tout sélectionner' }}
        </button>
        <button
          @click="openCreatePackModal"
          :disabled="selectedIds.size === 0"
          class="btn btn-primary text-sm disabled:opacity-50"
        >
          <i class="fas fa-box-open mr-1"></i>
          Créer un pack
        </button>
      </div>
    </Teleport>

    <!-- Share Link Modal (fallback for mobile) -->
    <Teleport to="body">
      <div
        v-if="showShareModal"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <div
          class="absolute inset-0 bg-black bg-opacity-50"
          @click="showShareModal = false"
        ></div>

        <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
          <button
            @click="showShareModal = false"
            class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <i class="fas fa-times"></i>
          </button>

          <div class="text-center">
            <div class="w-16 h-16 mx-auto bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center mb-4">
              <i class="fas fa-link text-3xl text-primary-600 dark:text-primary-400"></i>
            </div>

            <h3 class="text-xl font-semibold text-gray-800 dark:text-white mb-2">
              Lien de partage
            </h3>

            <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Ce lien expire dans 30 jours
            </p>

            <div class="flex gap-2 mb-4">
              <input
                type="text"
                :value="shareUrl"
                readonly
                class="input flex-1 text-sm"
                @focus="$event.target.select()"
              />
              <button
                @click="copyShareUrl"
                class="btn btn-primary"
              >
                <i class="fas fa-copy"></i>
              </button>
            </div>

            <button
              @click="showShareModal = false"
              class="btn btn-secondary w-full"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Add to Gallery Modal -->
    <Teleport to="body">
      <div
        v-if="showGalleryModal && galleryArchive"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <div class="absolute inset-0 bg-black bg-opacity-50" @click="closeGalleryModal"></div>

        <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
          <button
            @click="closeGalleryModal"
            class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <i class="fas fa-times"></i>
          </button>

          <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">
            <i class="fas fa-images text-primary-600 mr-2"></i>
            Ajouter à la galerie
          </h3>

          <!-- Cover preview -->
          <div class="rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 mb-4 flex justify-center">
            <img
              :src="`/api/archives/cover/${galleryArchive.cover_path}`"
              :alt="galleryArchive.title"
              class="max-h-64 object-contain"
            />
          </div>

          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Le visuel de <strong>{{ galleryArchive.title }}</strong> sera ajouté directement à la galerie.
          </p>

          <!-- Author -->
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Pseudo du créateur
            </label>
            <input
              v-model="galleryAuthor"
              type="text"
              class="input w-full"
              placeholder="Créateur du visuel..."
              maxlength="100"
            />
          </div>

          <!-- Themes -->
          <div class="mb-4 overflow-visible">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Thèmes
            </label>
            <ThemeAutocomplete
              v-model="galleryThemeIds"
              :themes="visualsStore.visualThemes"
              @theme-created="onGalleryThemeCreated"
            />
          </div>

          <!-- Actions -->
          <div class="flex gap-3">
            <button
              @click="confirmAddToGallery"
              :disabled="galleryLoading"
              class="btn btn-primary flex-1"
            >
              <i :class="galleryLoading ? 'fas fa-spinner fa-spin' : 'fas fa-plus'" class="mr-2"></i>
              {{ galleryLoading ? 'Ajout...' : 'Ajouter' }}
            </button>
            <button @click="closeGalleryModal" class="btn btn-secondary">
              Annuler
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Add Icons to Gallery Modal -->
    <Teleport to="body">
      <div
        v-if="showIconGalleryModal && iconGalleryArchive"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <div class="absolute inset-0 bg-black bg-opacity-50" @click="closeIconGalleryModal"></div>

        <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
          <button
            @click="closeIconGalleryModal"
            class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <i class="fas fa-times"></i>
          </button>

          <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">
            <i class="fas fa-icons text-primary-600 mr-2"></i>
            Ajouter les icônes à la galerie
          </h3>

          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Icônes des chapitres de <strong>{{ iconGalleryArchive.title }}</strong>
          </p>

          <!-- Author -->
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Pseudo du créateur
            </label>
            <input
              v-model="iconGalleryAuthor"
              type="text"
              class="input w-full"
              placeholder="Créateur des icônes..."
              maxlength="100"
            />
          </div>

          <!-- Loading -->
          <div v-if="iconGalleryLoading && iconGalleryItems.length === 0" class="text-center py-8">
            <i class="fas fa-spinner fa-spin text-3xl text-primary-600"></i>
            <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Chargement des chapitres...</p>
          </div>

          <!-- No icons found -->
          <div v-else-if="iconGalleryItems.length === 0" class="text-center py-8">
            <i class="fas fa-image text-4xl text-gray-300 dark:text-gray-600"></i>
            <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Aucun chapitre avec icône trouvé</p>
          </div>

          <!-- Icons grid -->
          <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            <div
              v-for="(item, index) in iconGalleryItems"
              :key="item.chapterKey"
              class="relative rounded-lg border dark:border-gray-700 overflow-hidden transition-opacity"
              :class="item.included ? 'opacity-100' : 'opacity-40'"
            >
              <!-- Exclude/include toggle -->
              <button
                @click="toggleIconIncluded(index)"
                class="absolute top-1 right-1 z-10 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
                :class="item.included
                  ? 'bg-red-500/80 text-white hover:bg-red-600'
                  : 'bg-green-500/80 text-white hover:bg-green-600'"
                :title="item.included ? 'Exclure' : 'Réinclure'"
              >
                <i :class="item.included ? 'fas fa-times' : 'fas fa-plus'" class="text-[10px]"></i>
              </button>

              <!-- Icon preview -->
              <div class="aspect-square bg-gray-100 dark:bg-gray-700 flex items-center justify-center p-2 checkerboard-sm">
                <img
                  :src="`/api/archives/${iconGalleryArchive.id}/chapters/${item.chapterKey}/icon`"
                  :alt="item.title"
                  class="w-8 h-8 icon-pixelated"
                  loading="lazy"
                />
              </div>

              <!-- Chapter info -->
              <div class="p-2">
                <p class="text-[11px] text-gray-700 dark:text-gray-300 truncate mb-1" :title="item.title">
                  {{ item.title }}
                </p>
                <input
                  v-model="item.keywords"
                  type="text"
                  class="w-full text-[11px] px-1.5 py-0.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                  placeholder="Mots-clés..."
                  :disabled="!item.included"
                />
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div v-if="iconGalleryItems.length > 0" class="flex items-center gap-3">
            <button
              @click="confirmAddIconsToGallery"
              :disabled="iconGalleryLoading || includedIconCount === 0"
              class="btn btn-primary flex-1"
            >
              <i :class="iconGalleryLoading ? 'fas fa-spinner fa-spin' : 'fas fa-plus'" class="mr-2"></i>
              {{ iconGalleryLoading ? 'Ajout en cours...' : `Ajouter ${includedIconCount} icône${includedIconCount > 1 ? 's' : ''}` }}
            </button>
            <button @click="closeIconGalleryModal" class="btn btn-secondary" :disabled="iconGalleryLoading">
              Annuler
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.checkerboard-sm {
  background-image:
    linear-gradient(45deg, #e5e7eb 25%, transparent 25%),
    linear-gradient(-45deg, #e5e7eb 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #e5e7eb 75%),
    linear-gradient(-45deg, transparent 75%, #e5e7eb 75%);
  background-size: 12px 12px;
  background-position: 0 0, 0 6px, 6px -6px, -6px 0px;
  background-color: #fff;
}

:root.dark .checkerboard-sm,
.dark .checkerboard-sm {
  background-image:
    linear-gradient(45deg, #374151 25%, transparent 25%),
    linear-gradient(-45deg, #374151 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #374151 75%),
    linear-gradient(-45deg, transparent 75%, #374151 75%);
  background-color: #1f2937;
}

.icon-pixelated {
  image-rendering: pixelated;
  image-rendering: -moz-crisp-edges;
}
</style>
