<template>
  <div class="card-preview">
    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
      <i class="fas fa-id-card mr-1"></i>
      Aperçu de la carte
    </h3>

    <!-- Card frame (3:4 ratio like real Yoto card 638x1011) -->
    <div class="card-frame mx-auto bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-lg border border-gray-200 dark:border-gray-700">
      <!-- Cover image -->
      <div class="card-cover relative">
        <img
          v-if="coverUrl"
          :src="coverUrl"
          class="w-full h-full object-cover"
          @error="coverError = true"
        />
        <div v-else class="w-full h-full bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-600 flex items-center justify-center">
          <i class="fas fa-image text-3xl text-gray-400 dark:text-gray-500"></i>
        </div>

        <!-- Title overlay -->
        <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3 pt-8">
          <p class="text-white text-sm font-bold leading-tight truncate">{{ title }}</p>
        </div>
      </div>

      <!-- Chapter list -->
      <div class="card-chapters p-2 space-y-1 overflow-y-auto">
        <div
          v-for="(chapter, i) in chapters"
          :key="chapter.key"
          class="flex items-center gap-2 px-2 py-1 rounded text-xs hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        >
          <div class="w-4 h-4 flex-shrink-0 rounded overflow-hidden bg-gray-100 dark:bg-gray-700">
            <img
              v-if="chapter.icon_file && !failedIcons.has(chapter.key)"
              :src="getIconUrl(chapter.key)"
              class="w-full h-full object-cover"
              @error="onIconError(chapter.key)"
            />
            <span v-else class="flex items-center justify-center w-full h-full text-[8px] text-gray-400 font-bold">{{ i + 1 }}</span>
          </div>
          <span class="flex-1 truncate text-gray-800 dark:text-gray-200">{{ chapter.title || 'Sans titre' }}</span>
          <span class="text-gray-400 whitespace-nowrap">{{ formatDuration(chapter.duration) }}</span>
        </div>
        <div v-if="!chapters.length" class="text-center py-3 text-gray-400 text-xs">
          Aucun chapitre
        </div>
      </div>

      <!-- Footer info -->
      <div class="px-3 py-2 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between text-xs text-gray-500">
        <span>{{ chapters.length }} chapitre{{ chapters.length > 1 ? 's' : '' }}</span>
        <span>{{ formatTotalDuration }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useArchivesStore } from '../../stores/archives'

const props = defineProps({
  archiveId: { type: Number, required: true },
  title: { type: String, default: '' },
  coverPath: { type: String, default: null },
  chapters: { type: Array, default: () => [] },
})

const store = useArchivesStore()
const coverError = ref(false)
const iconCacheBuster = ref(Date.now())
const failedIcons = ref(new Set())

const coverUrl = computed(() => {
  if (!props.coverPath || coverError.value) return null
  return `/api/archives/cover/${props.coverPath}`
})

const formatTotalDuration = computed(() => {
  const totalMs = props.chapters.reduce((sum, ch) => sum + (ch.duration || 0), 0)
  return formatDuration(totalMs)
})

function getIconUrl(chapterKey) {
  return `${store.getChapterIconUrl(props.archiveId, chapterKey)}?t=${iconCacheBuster.value}`
}

function onIconError(key) {
  failedIcons.value.add(key)
  failedIcons.value = new Set(failedIcons.value)
}

function formatDuration(ms) {
  if (!ms) return '--:--'
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}h${mins.toString().padStart(2, '0')}`
  }
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

defineExpose({
  refresh() {
    iconCacheBuster.value = Date.now()
    coverError.value = false
    failedIcons.value = new Set()
  }
})
</script>

<style scoped>
.card-frame {
  max-width: 220px;
  aspect-ratio: auto;
}

.card-cover {
  aspect-ratio: 638 / 700;
  overflow: hidden;
}

.card-chapters {
  max-height: 180px;
}
</style>
