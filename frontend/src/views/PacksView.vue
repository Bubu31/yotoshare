<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { usePacksStore } from '../stores/packs'
import { useAuthStore } from '../stores/auth'
import { useMessage } from '../composables/useMessage'
import AlertMessage from '../components/AlertMessage.vue'
import PublishModal from '../components/PublishModal.vue'

const packsStore = usePacksStore()
const authStore = useAuthStore()
const { message, showMessage } = useMessage()

const showConfig = ref(false)
const uploadingBackground = ref(false)
const uploadingMascot = ref(false)
const regeneratingId = ref(null)
const selectedPack = ref(null)
const showPublishModal = ref(false)
const sentinel = ref(null)
let observer = null

onMounted(async () => {
  await packsStore.fetchPacks()
  if (authStore.hasPermission('packs', 'modify')) {
    packsStore.fetchAssets()
  }

  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && packsStore.hasMore() && !packsStore.loading) {
        packsStore.loadMore()
      }
    },
    { rootMargin: '200px' }
  )
  if (sentinel.value) observer.observe(sentinel.value)
})

onUnmounted(() => {
  if (observer) observer.disconnect()
})

function isExpired(pack) {
  return new Date(pack.expires_at) < new Date()
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function daysLeft(dateStr) {
  const diff = new Date(dateStr) - new Date()
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24))
  return days > 0 ? days : 0
}

async function handleReshare(pack) {
  try {
    const updated = await packsStore.resharePack(pack.id)
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(updated.share_url)
        showMessage('success', 'Lien renouvel\u00e9 et copi\u00e9 !')
        return
      } catch (_) {}
    }
    showMessage('success', 'Lien renouvel\u00e9 pour 30 jours')
  } catch (e) {
    showMessage('error', 'Erreur lors du renouvellement')
  }
}

async function handleCopyLink(pack) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(pack.share_url)
      showMessage('success', 'Lien copi\u00e9 !')
    } catch (_) {
      showMessage('info', pack.share_url)
    }
  }
}

async function handleDelete(pack) {
  if (!confirm(`Supprimer le pack "${pack.name}" ?`)) return
  try {
    await packsStore.deletePack(pack.id)
    showMessage('success', 'Pack supprim\u00e9')
  } catch (e) {
    showMessage('error', 'Erreur lors de la suppression')
  }
}

async function handleRegenerateImage(pack) {
  regeneratingId.value = pack.id
  try {
    const updated = await packsStore.regenerateImage(pack.id)
    // Download the generated image
    const imageUrl = `/api/packs/${updated.id}/image`
    const response = await fetch(imageUrl)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${pack.name.replace(/[^a-zA-Z0-9\u00C0-\u024F -]/g, '_')}.jpg`
    a.click()
    URL.revokeObjectURL(url)
    showMessage('success', 'Image g\u00e9n\u00e9r\u00e9e et t\u00e9l\u00e9charg\u00e9e')
  } catch (e) {
    showMessage('error', 'Erreur lors de la g\u00e9n\u00e9ration')
  } finally {
    regeneratingId.value = null
  }
}

async function handleAssetUpload(type, event) {
  const file = event.target.files?.[0]
  if (!file) return

  const loading = type === 'background' ? uploadingBackground : uploadingMascot
  loading.value = true
  try {
    await packsStore.uploadAsset(type, file)
    showMessage('success', `${type === 'background' ? 'Fond' : 'Mascotte'} mis \u00e0 jour`)
  } catch (e) {
    showMessage('error', `Erreur lors de l'upload`)
  } finally {
    loading.value = false
    event.target.value = ''
  }
}

async function handleAssetDelete(type) {
  const label = type === 'background' ? 'le fond' : 'la mascotte'
  if (!confirm(`Supprimer ${label} ?`)) return
  try {
    await packsStore.deleteAsset(type)
    showMessage('success', `${type === 'background' ? 'Fond' : 'Mascotte'} supprim\u00e9`)
  } catch (e) {
    showMessage('error', 'Erreur lors de la suppression')
  }
}

function handlePublish(pack) {
  selectedPack.value = pack
  showPublishModal.value = true
}

async function confirmPublish(pack) {
  try {
    const result = await packsStore.publishToDiscord(pack.id)
    showPublishModal.value = false
    if (result.success) {
      showMessage('success', 'Pack publié sur Discord')
    } else {
      showMessage('error', result.message || 'Erreur inconnue')
    }
  } catch (e) {
    showPublishModal.value = false
    showMessage('error', e.response?.data?.message || e.message || 'Erreur lors de la publication')
  }
}

function assetUrl(type) {
  return `/api/packs/assets/${type}/image?t=${Date.now()}`
}
</script>

<template>
  <div>
    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6 md:mb-8">
      <div>
        <h1 class="text-2xl md:text-3xl font-bold text-gray-800 dark:text-white">
          <i class="fas fa-box-open text-primary-600 mr-2"></i>
          Packs de partage
        </h1>
        <p class="text-sm md:text-base text-gray-600 dark:text-gray-400">G\u00e9rez vos packs de partage multi-archives</p>
      </div>
      <div class="flex gap-2">
        <button
          v-if="authStore.hasPermission('packs', 'modify')"
          @click="showConfig = !showConfig"
          class="btn btn-secondary text-sm sm:text-base"
          :class="{ 'ring-2 ring-primary-500': showConfig }"
        >
          <i class="fas fa-sliders mr-2"></i>
          Configurer
        </button>
        <router-link to="/archives" class="btn btn-secondary text-sm sm:text-base">
          <i class="fas fa-arrow-left mr-2"></i>
          Retour aux archives
        </router-link>
      </div>
    </div>

    <AlertMessage :message="message" />

    <!-- Config panel -->
    <transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-2 max-h-0"
      enter-to-class="opacity-100 translate-y-0 max-h-[600px]"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0 max-h-[600px]"
      leave-to-class="opacity-0 -translate-y-2 max-h-0"
    >
      <div v-if="showConfig" class="card mb-6 overflow-hidden">
        <div class="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-800 dark:text-white">
            <i class="fas fa-image text-primary-600 mr-2"></i>
            Assets de l'image OG
          </h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Personnalisez le fond et la mascotte utilis\u00e9s pour g\u00e9n\u00e9rer l'image de partage des packs
          </p>
        </div>
        <div class="p-4 grid md:grid-cols-2 gap-6">
          <!-- Background section -->
          <div>
            <h3 class="font-medium text-gray-700 dark:text-gray-300 mb-3">
              <i class="fas fa-panorama mr-1"></i>
              Fond (1200x630)
            </h3>
            <div v-if="packsStore.assets.background" class="mb-3">
              <img
                :src="assetUrl('background')"
                alt="Background"
                class="w-full max-w-[600px] rounded border border-gray-200 dark:border-gray-700"
                style="aspect-ratio: 1200/630; object-fit: cover;"
              />
            </div>
            <div v-else class="mb-3 w-full max-w-[600px] rounded border-2 border-dashed border-gray-300 dark:border-gray-600 flex items-center justify-center bg-gray-50 dark:bg-gray-800" style="aspect-ratio: 1200/630;">
              <span class="text-gray-400 dark:text-gray-500 text-sm">D\u00e9grad\u00e9 par d\u00e9faut</span>
            </div>
            <div class="flex gap-2">
              <label class="btn btn-primary text-sm cursor-pointer">
                <i class="fas fa-upload mr-1"></i>
                <span v-if="uploadingBackground"><i class="fas fa-spinner fa-spin mr-1"></i>Upload...</span>
                <span v-else>Upload</span>
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  :disabled="uploadingBackground"
                  @change="handleAssetUpload('background', $event)"
                />
              </label>
              <button
                v-if="packsStore.assets.background && authStore.hasPermission('packs', 'delete')"
                @click="handleAssetDelete('background')"
                class="btn btn-danger text-sm"
              >
                <i class="fas fa-trash mr-1"></i>
                Supprimer
              </button>
            </div>
          </div>

          <!-- Mascot section -->
          <div>
            <h3 class="font-medium text-gray-700 dark:text-gray-300 mb-3">
              <i class="fas fa-user-astronaut mr-1"></i>
              Mascotte (max 400px hauteur)
            </h3>
            <div v-if="packsStore.assets.mascot" class="mb-3">
              <img
                :src="assetUrl('mascot')"
                alt="Mascotte"
                class="max-h-[200px] rounded border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800"
              />
            </div>
            <div v-else class="mb-3 w-32 h-32 rounded border-2 border-dashed border-gray-300 dark:border-gray-600 flex items-center justify-center bg-gray-50 dark:bg-gray-800">
              <span class="text-gray-400 dark:text-gray-500 text-xs text-center">Aucune<br/>mascotte</span>
            </div>
            <div class="flex gap-2">
              <label class="btn btn-primary text-sm cursor-pointer">
                <i class="fas fa-upload mr-1"></i>
                <span v-if="uploadingMascot"><i class="fas fa-spinner fa-spin mr-1"></i>Upload...</span>
                <span v-else>Upload</span>
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  :disabled="uploadingMascot"
                  @change="handleAssetUpload('mascot', $event)"
                />
              </label>
              <button
                v-if="packsStore.assets.mascot && authStore.hasPermission('packs', 'delete')"
                @click="handleAssetDelete('mascot')"
                class="btn btn-danger text-sm"
              >
                <i class="fas fa-trash mr-1"></i>
                Supprimer
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <div v-if="packsStore.loading" class="text-center py-12">
      <i class="fas fa-spinner fa-spin text-4xl text-primary-600"></i>
    </div>

    <div v-else-if="packsStore.packs.length === 0" class="text-center py-12 card">
      <i class="fas fa-box-open text-6xl text-gray-300 dark:text-gray-600"></i>
      <p class="mt-4 text-gray-500 dark:text-gray-400">Aucun pack de partage</p>
      <p class="text-sm text-gray-400 dark:text-gray-500 mt-1">
        S\u00e9lectionnez des archives pour cr\u00e9er un pack
      </p>
      <router-link to="/archives" class="btn btn-primary mt-4 inline-block">
        <i class="fas fa-book mr-2"></i>
        Aller aux archives
      </router-link>
    </div>

    <div v-else class="grid gap-4">
      <div
        v-for="pack in packsStore.packs"
        :key="pack.id"
        class="card"
        :class="{ 'opacity-60': isExpired(pack) }"
      >
        <div class="flex flex-col sm:flex-row gap-4 p-4">
          <!-- Cover thumbnails -->
          <div class="flex gap-1 flex-shrink-0">
            <template v-for="(archive, i) in pack.archives.slice(0, 4)" :key="archive.id">
              <img
                v-if="archive.cover_path"
                :src="`/api/archives/cover/${archive.cover_path}`"
                :alt="archive.title"
                class="w-16 h-22 object-cover rounded"
                :class="{ '-ml-4': i > 0 }"
                :style="{ zIndex: 4 - i }"
              />
              <div
                v-else
                class="w-16 h-22 bg-gray-200 dark:bg-gray-700 rounded flex items-center justify-center"
                :class="{ '-ml-4': i > 0 }"
                :style="{ zIndex: 4 - i }"
              >
                <i class="fas fa-book text-gray-400"></i>
              </div>
            </template>
            <div
              v-if="pack.archives.length > 4"
              class="w-16 h-22 bg-gray-200 dark:bg-gray-700 rounded flex items-center justify-center -ml-4"
              :style="{ zIndex: 0 }"
            >
              <span class="text-xs font-bold text-gray-500">+{{ pack.archives.length - 4 }}</span>
            </div>
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <h3 class="text-lg font-semibold text-gray-800 dark:text-white truncate">{{ pack.name }}</h3>
            <p v-if="pack.description" class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mt-1">
              {{ pack.description }}
            </p>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 text-sm text-gray-500 dark:text-gray-400">
              <span>
                <i class="fas fa-book mr-1"></i>
                {{ pack.archive_count }} archive{{ pack.archive_count > 1 ? 's' : '' }}
              </span>
              <span v-if="!isExpired(pack)" class="text-green-600 dark:text-green-400">
                <i class="fas fa-clock mr-1"></i>
                {{ daysLeft(pack.expires_at) }}j restants
              </span>
              <span v-else class="text-red-500">
                <i class="fas fa-exclamation-circle mr-1"></i>
                Expir\u00e9
              </span>
              <span>
                <i class="fas fa-calendar mr-1"></i>
                {{ formatDate(pack.created_at) }}
              </span>
              <span v-if="pack.discord_post_id" class="text-green-600 dark:text-green-400" title="Publié sur Discord">
                <i class="fab fa-discord mr-1"></i>
                Publié
              </span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-start gap-2 flex-shrink-0">
            <button
              v-if="!isExpired(pack)"
              @click="handleCopyLink(pack)"
              class="btn btn-secondary text-sm"
              title="Copier le lien"
            >
              <i class="fas fa-copy"></i>
            </button>
            <button
              @click="handleReshare(pack)"
              class="btn btn-primary text-sm"
              :title="isExpired(pack) ? 'Renouveler' : 'Renouveler et copier'"
            >
              <i class="fas fa-redo"></i>
            </button>
            <button
              v-if="authStore.hasPermission('discord', 'modify') && !pack.discord_post_id && !isExpired(pack)"
              @click="handlePublish(pack)"
              class="btn btn-secondary text-sm"
              title="Publier sur Discord"
            >
              <i class="fab fa-discord"></i>
            </button>
            <button
              v-if="authStore.hasPermission('packs', 'modify')"
              @click="handleRegenerateImage(pack)"
              class="btn btn-secondary text-sm"
              title="R\u00e9g\u00e9n\u00e9rer l'image"
              :disabled="regeneratingId === pack.id"
            >
              <i class="fas fa-image" :class="{ 'fa-spin': regeneratingId === pack.id }"></i>
            </button>
            <button
              v-if="authStore.hasPermission('packs', 'delete')"
              @click="handleDelete(pack)"
              class="btn btn-danger text-sm"
              title="Supprimer"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Infinite scroll sentinel -->
      <div ref="sentinel" class="h-4"></div>

      <div v-if="packsStore.loadingMore" class="text-center py-4">
        <i class="fas fa-spinner fa-spin text-2xl text-primary-600"></i>
      </div>
    </div>
    <PublishModal
      v-if="selectedPack"
      :item="selectedPack"
      item-label="pack"
      :is-open="showPublishModal"
      @close="showPublishModal = false"
      @confirm="confirmPublish"
    />
  </div>
</template>
