<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useArchivesStore } from '../stores/archives'
import TagInput from '../components/TagInput.vue'
import ChapterList from '../components/archive-editor/ChapterList.vue'
import ChapterEditor from '../components/archive-editor/ChapterEditor.vue'
import CoverCropper from '../components/archive-editor/CoverCropper.vue'
import NfoEditor from '../components/archive-editor/NfoEditor.vue'
import CardPreview from '../components/archive-editor/CardPreview.vue'
import api from '../services/api'

const router = useRouter()
const route = useRoute()
const archivesStore = useArchivesStore()

const archive = ref(null)
const archiveContent = ref(null)
const loading = ref(true)
const error = ref('')
const saving = ref(false)
const activeTab = ref('metadata')
const selectedChapter = ref(null)
const showPreview = ref(false)
const cardPreviewRef = ref(null)

const form = ref({
  title: '',
  author: '',
  description: '',
  categories: [],
  ages: [],
})

const tabs = [
  { id: 'metadata', label: 'Métadonnées', icon: 'fa-info-circle' },
  { id: 'chapters', label: 'Chapitres', icon: 'fa-list' },
  { id: 'cover', label: 'Couverture', icon: 'fa-image' },
  { id: 'nfo', label: 'NFO', icon: 'fa-file-alt' },
]

const archiveId = computed(() => parseInt(route.params.id))

onMounted(async () => {
  await archivesStore.fetchCategories()
  await archivesStore.fetchAges()

  try {
    const response = await api.get(`/api/archives/${route.params.id}`)
    archive.value = response.data
    form.value = {
      title: archive.value.title,
      author: archive.value.author || '',
      description: archive.value.description || '',
      categories: archive.value.categories?.map(c => c.name) || [],
      ages: archive.value.ages?.map(a => a.name) || [],
    }

    // Load archive content for chapters
    await loadArchiveContent()
  } catch (e) {
    error.value = 'Archive non trouvée'
  } finally {
    loading.value = false
  }
})

async function loadArchiveContent() {
  try {
    archiveContent.value = await archivesStore.fetchArchiveContent(archiveId.value)
  } catch (e) {
    console.error('Failed to load archive content:', e)
  }
}

async function handleSubmit() {
  saving.value = true
  error.value = ''

  try {
    const formData = new FormData()
    formData.append('title', form.value.title)
    if (form.value.author) formData.append('author', form.value.author)
    if (form.value.description) formData.append('description', form.value.description)
    formData.append('categories', JSON.stringify(form.value.categories))
    formData.append('ages', JSON.stringify(form.value.ages))

    await archivesStore.updateArchive(archive.value.id, formData)
    router.push('/archives')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors de la modification'
    saving.value = false
  }
}

function handleCancel() {
  router.push('/archives')
}

function selectChapter(chapter) {
  selectedChapter.value = chapter
}

async function refreshContent() {
  const currentSelectedKey = selectedChapter.value?.key
  await loadArchiveContent()
  // Update selected chapter with fresh data
  if (currentSelectedKey && archiveContent.value?.chapters) {
    selectedChapter.value = archiveContent.value.chapters.find(ch => ch.key === currentSelectedKey) || null
  }
  // Also refresh archive data
  try {
    const response = await api.get(`/api/archives/${route.params.id}`)
    archive.value = response.data
  } catch (e) {
    console.error('Failed to refresh archive:', e)
  }
  // Refresh card preview icons
  cardPreviewRef.value?.refresh()
}
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <div class="mb-6 md:mb-8">
      <router-link to="/archives" class="text-primary-600 hover:text-primary-800 dark:hover:text-primary-400 mb-4 inline-block">
        <i class="fas fa-arrow-left mr-2"></i>
        Retour
      </router-link>
      <h1 class="text-2xl md:text-3xl font-bold text-gray-800 dark:text-white">
        <i class="fas fa-edit text-primary-600 mr-2"></i>
        Modifier l'archive
      </h1>
      <p v-if="archive" class="text-gray-500 mt-1">{{ archive.title }}</p>
    </div>

    <div v-if="loading" class="text-center py-12">
      <i class="fas fa-spinner fa-spin text-4xl text-primary-600"></i>
    </div>

    <div v-else-if="error && !archive" class="text-center py-12 card">
      <i class="fas fa-exclamation-triangle text-6xl text-red-400"></i>
      <p class="mt-4 text-gray-500 dark:text-gray-400">{{ error }}</p>
      <router-link to="/archives" class="btn btn-primary mt-4 inline-block">
        Retour aux archives
      </router-link>
    </div>

    <div v-else class="flex gap-6">
      <!-- Main content -->
      <div class="flex-1 min-w-0">
        <!-- Tabs -->
        <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
          <nav class="flex gap-4 overflow-x-auto pb-px">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="activeTab = tab.id"
              :class="[
                'px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              ]"
            >
              <i :class="['fas', tab.icon, 'mr-2']"></i>
              {{ tab.label }}
            </button>
          </nav>
        </div>

        <!-- Tab Content -->
        <div class="card p-4 md:p-6">
          <!-- Metadata Tab -->
          <div v-show="activeTab === 'metadata'">
            <div
              v-if="error"
              class="mb-6 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg"
            >
              <i class="fas fa-exclamation-circle mr-2"></i>
              {{ error }}
            </div>

            <form @submit.prevent="handleSubmit" class="space-y-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Titre *
                </label>
                <input
                  v-model="form.title"
                  type="text"
                  class="input"
                  required
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Auteur
                </label>
                <input
                  v-model="form.author"
                  type="text"
                  class="input"
                  placeholder="Optionnel"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  v-model="form.description"
                  class="input"
                  rows="3"
                ></textarea>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  <i class="fas fa-folder mr-1"></i>
                  Catégories
                </label>
                <TagInput
                  v-model="form.categories"
                  :suggestions="archivesStore.categories"
                  placeholder="Ajouter une catégorie..."
                  icon="fas fa-folder"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  <i class="fas fa-child mr-1"></i>
                  Âges
                </label>
                <TagInput
                  v-model="form.ages"
                  :suggestions="archivesStore.ages"
                  placeholder="Ajouter un âge..."
                  icon="fas fa-child"
                />
              </div>

              <div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
                <button
                  type="button"
                  @click="handleCancel"
                  class="btn btn-secondary"
                  :disabled="saving"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  class="btn btn-primary"
                  :disabled="saving"
                >
                  <i v-if="saving" class="fas fa-spinner fa-spin mr-2"></i>
                  Enregistrer
                </button>
              </div>
            </form>
          </div>

          <!-- Chapters Tab -->
          <div v-show="activeTab === 'chapters'">
            <div v-if="archiveContent">
              <!-- Chapter list sidebar + editor -->
              <div class="flex flex-col lg:flex-row gap-6">
                <!-- Chapter list - fixed width sidebar -->
                <div class="lg:w-[350px] lg:flex-shrink-0">
                  <ChapterList
                    :archive-id="archiveId"
                    :chapters="archiveContent.chapters"
                    :selected-chapter="selectedChapter"
                    @select="selectChapter"
                    @refresh="refreshContent"
                  />
                </div>

                <!-- Chapter editor - takes remaining space -->
                <div class="flex-1 min-w-0">
                  <ChapterEditor
                    v-if="selectedChapter"
                    :archive-id="archiveId"
                    :chapter="selectedChapter"
                    @close="selectedChapter = null"
                    @refresh="refreshContent"
                  />
                  <div v-else class="flex items-center justify-center bg-gray-50 dark:bg-gray-800 rounded-lg p-8 h-full min-h-[200px]">
                    <div class="text-center text-gray-500">
                      <i class="fas fa-mouse-pointer text-4xl mb-3"></i>
                      <p>Sélectionnez un chapitre pour l'éditer</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-8">
              <i class="fas fa-spinner fa-spin text-2xl text-primary-600"></i>
            </div>
          </div>

          <!-- Cover Tab -->
          <div v-show="activeTab === 'cover'">
            <CoverCropper
              :archive-id="archiveId"
              :current-cover-path="archive?.cover_path"
              @saved="refreshContent"
            />
          </div>

          <!-- NFO Tab -->
          <div v-show="activeTab === 'nfo'">
            <NfoEditor
              :archive-id="archiveId"
              @saved="refreshContent"
            />
          </div>
        </div>
      </div>

      <!-- Card Preview sidebar - hidden on mobile, visible on xl+ -->
      <div class="hidden xl:block w-[260px] flex-shrink-0">
        <div class="sticky top-4">
          <CardPreview
            v-if="archiveContent"
            ref="cardPreviewRef"
            :archive-id="archiveId"
            :title="archive?.title || ''"
            :cover-path="archive?.cover_path"
            :chapters="archiveContent.chapters"
          />
        </div>
      </div>
    </div>

    <!-- Mobile preview toggle button -->
    <button
      v-if="archive && archiveContent && !loading"
      @click="showPreview = !showPreview"
      class="xl:hidden fixed bottom-6 right-6 w-12 h-12 bg-primary-600 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-primary-700 transition-colors z-40"
      title="Aperçu de la carte"
    >
      <i class="fas fa-id-card"></i>
    </button>

    <!-- Mobile preview overlay -->
    <div
      v-if="showPreview"
      class="xl:hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      @click.self="showPreview = false"
    >
      <div class="bg-white dark:bg-gray-900 rounded-xl p-4 max-w-xs w-full">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold text-gray-700 dark:text-gray-300">Aperçu</span>
          <button @click="showPreview = false" class="text-gray-400 hover:text-gray-600">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <CardPreview
          v-if="archiveContent"
          :archive-id="archiveId"
          :title="archive?.title || ''"
          :cover-path="archive?.cover_path"
          :chapters="archiveContent.chapters"
        />
      </div>
    </div>
  </div>
</template>
