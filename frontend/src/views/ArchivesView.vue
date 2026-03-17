<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useArchivesStore } from '../stores/archives'
import { useAuthStore } from '../stores/auth'
import { useMessage } from '../composables/useMessage'
import api from '../services/api'
import ArchiveCard from '../components/ArchiveCard.vue'
import AlertMessage from '../components/AlertMessage.vue'
import PublishModal from '../components/PublishModal.vue'
import BulkUploadModal from '../components/BulkUploadModal.vue'
import CreatePackModal from '../components/CreatePackModal.vue'
const router = useRouter()
const archivesStore = useArchivesStore()
const authStore = useAuthStore()
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
  return archivesStore.archives.filter(a => selectedIds.value.has(a.id))
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
  selectedIds.value = new Set(archivesStore.archives.map(a => a.id))
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

function buildParams() {
  const params = { sort: sortBy.value }
  if (filterCategory.value) params.category_id = filterCategory.value
  if (filterAge.value) params.age_id = filterAge.value
  if (searchQuery.value) params.search = searchQuery.value
  if (hidePublished.value) params.hide_published = true
  return params
}

function debouncedFetch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    archivesStore.fetchArchives(buildParams())
  }, 300)
}

watch(searchQuery, debouncedFetch)
watch(filterCategory, debouncedFetch)
watch(filterAge, debouncedFetch)
watch(sortBy, debouncedFetch)
watch(hidePublished, debouncedFetch)

// Infinite scroll
const sentinel = ref(null)
let observer = null

function checkAndLoadMore() {
  if (!sentinel.value || !archivesStore.hasMore() || archivesStore.loading || archivesStore.loadingMore) return
  const rect = sentinel.value.getBoundingClientRect()
  if (rect.top < window.innerHeight + 200) {
    archivesStore.loadMore()
  }
}

// After loadMore finishes, check if sentinel is still visible (need another page)
watch(() => archivesStore.loadingMore, (val) => {
  if (!val) nextTick(checkAndLoadMore)
})

onMounted(async () => {
  await Promise.all([
    archivesStore.fetchCategories(),
    archivesStore.fetchAges(),
    archivesStore.fetchArchives(buildParams()),
  ])

  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting) {
        checkAndLoadMore()
      }
    },
    { rootMargin: '200px' }
  )
  if (sentinel.value) observer.observe(sentinel.value)
})

onUnmounted(() => {
  clearTimeout(searchTimeout)
  if (observer) observer.disconnect()
})

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
  await archivesStore.fetchArchives(buildParams())
  showMessage('success', 'Import en masse terminé')
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
          Archives ({{ archivesStore.archives.length }}{{ archivesStore.total > archivesStore.archives.length ? ` / ${archivesStore.total}` : '' }})
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
          v-for="archive in archivesStore.archives"
          :key="archive.id"
          :archive="archive"
          :show-actions="!selectionMode"
          :selection-mode="selectionMode"
          :selected="selectedIds.has(archive.id)"
          @edit="handleEdit"
          @delete="handleDelete"
          @share="handleShare"
          @publish="handlePublish"
          @toggle-select="toggleSelect"
        />

        <!-- Infinite scroll sentinel -->
        <div ref="sentinel" class="h-4"></div>

        <div v-if="archivesStore.loadingMore" class="text-center py-4">
          <i class="fas fa-spinner fa-spin text-2xl text-primary-600"></i>
        </div>
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
          @click="selectedIds.size === archivesStore.archives.length ? deselectAll() : selectAll()"
          class="text-sm text-primary-400 hover:text-primary-300 transition-colors"
        >
          {{ selectedIds.size === archivesStore.archives.length ? 'Tout désélectionner' : 'Tout sélectionner' }}
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

  </div>
</template>
