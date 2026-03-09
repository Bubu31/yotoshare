<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const props = defineProps({
  archive: {
    type: Object,
    required: true,
  },
  showActions: {
    type: Boolean,
    default: false,
  },
  selectionMode: {
    type: Boolean,
    default: false,
  },
  selected: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['edit', 'delete', 'publish', 'share', 'add-to-gallery', 'add-icons-to-gallery', 'toggle-select'])

function handleCardClick() {
  if (props.selectionMode) {
    emit('toggle-select', props.archive)
  }
}

const coverUrl = computed(() => {
  if (props.archive.cover_path) {
    return `/api/archives/cover/${props.archive.cover_path}`
  }
  return null
})

const fileSize = computed(() => {
  const mb = props.archive.file_size / (1024 * 1024)
  return `${mb.toFixed(1)} MB`
})

const duration = computed(() => {
  if (!props.archive.total_duration) return null
  const totalSeconds = props.archive.total_duration
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m ${seconds}s`
})

const isPublished = computed(() => !!props.archive.discord_post_id)
</script>

<template>
  <div
    class="card relative"
    :class="{
      'ring-2 ring-indigo-500/60': selected,
      'cursor-pointer': selectionMode,
    }"
    @click="handleCardClick"
  >
    <!-- Selection checkbox overlay -->
    <div
      v-if="selectionMode"
      class="absolute top-3 left-3 z-10 w-7 h-7 rounded-full flex items-center justify-center transition-all duration-200"
      :class="selected
        ? 'text-white scale-110'
        : 'border border-gray-300 dark:border-white/20 bg-white dark:bg-white/5'"
      :style="selected ? 'background: linear-gradient(135deg, #6366f1, #38bdf8); box-shadow: 0 0 12px rgba(99, 102, 241, 0.5);' : ''"
    >
      <i v-if="selected" class="fas fa-check text-xs"></i>
    </div>

    <div class="flex flex-col sm:flex-row">
      <div class="w-full sm:w-32 h-40 sm:h-48 flex-shrink-0 bg-gray-100 dark:bg-white/5">
        <img
          v-if="coverUrl"
          :src="coverUrl"
          :alt="archive.title"
          class="w-full h-full object-cover"
        />
        <div
          v-else
          class="w-full h-full flex items-center justify-center text-gray-300 dark:text-indigo-400/40"
        >
          <i class="fas fa-book text-4xl"></i>
        </div>
      </div>

      <div class="flex-1 p-4">
        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
          <div class="flex-1 min-w-0">
            <h3 class="text-lg font-extrabold text-gray-900 dark:text-white truncate">{{ archive.title }}</h3>
            <p v-if="archive.author" class="text-sm text-gray-500 dark:text-gray-400">{{ archive.author }}</p>
          </div>
          <div class="flex flex-wrap gap-1 sm:justify-end">
            <span
              v-for="category in archive.categories"
              :key="'cat-' + category.id"
              class="px-2.5 py-1 text-xs font-bold rounded-full text-indigo-600 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-500/15 border border-indigo-200 dark:border-indigo-500/25"
            >
              <i :class="category.icon" class="mr-1"></i>
              {{ category.name }}
            </span>
            <span
              v-for="age in archive.ages"
              :key="'age-' + age.id"
              class="px-2.5 py-1 text-xs font-bold rounded-full text-emerald-600 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-500/15 border border-emerald-200 dark:border-emerald-500/25"
            >
              <i :class="age.icon" class="mr-1"></i>
              {{ age.name }}
            </span>
          </div>
        </div>

        <p
          v-if="archive.description"
          class="mt-2 text-sm text-gray-500 dark:text-gray-400 line-clamp-2"
        >
          {{ archive.description }}
        </p>

        <div class="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500">
            <span>
              <i class="fas fa-file-archive mr-1"></i>
              {{ fileSize }}
            </span>
            <span v-if="duration">
              <i class="fas fa-clock mr-1"></i>
              {{ duration }}
            </span>
            <span v-if="archive.chapters_count">
              <i class="fas fa-list mr-1"></i>
              {{ archive.chapters_count }} chap.
            </span>
            <span v-if="archive.download_count">
              <i class="fas fa-download mr-1"></i>
              {{ archive.download_count }}
            </span>
          </div>

          <div v-if="showActions" class="flex space-x-2">
            <button
              v-if="!isPublished"
              @click="emit('publish', archive)"
              class="btn btn-primary text-sm"
              title="Publier sur Discord"
            >
              <i class="fab fa-discord"></i>
            </button>
            <span
              v-else
              class="text-emerald-500 dark:text-emerald-400 text-sm flex items-center"
              title="Publié sur Discord"
            >
              <i class="fab fa-discord"></i>
              <i class="fas fa-check ml-1"></i>
            </span>
            <button
              v-if="coverUrl && authStore.hasPermission('visuals', 'modify')"
              @click="emit('add-to-gallery', archive)"
              class="btn btn-secondary text-sm"
              title="Ajouter la cover à la galerie"
            >
              <i class="fas fa-images"></i>
            </button>
            <button
              v-if="authStore.hasPermission('visuals', 'modify')"
              @click="emit('add-icons-to-gallery', archive)"
              class="btn btn-secondary text-sm"
              title="Ajouter les icônes à la galerie"
            >
              <i class="fas fa-icons"></i>
            </button>
            <button
              @click="emit('share', archive)"
              class="btn btn-secondary text-sm"
              title="Partager"
            >
              <i class="fas fa-share-alt"></i>
            </button>
            <button
              @click="emit('edit', archive)"
              class="btn btn-secondary text-sm"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              v-if="authStore.hasPermission('archives', 'delete')"
              @click="emit('delete', archive)"
              class="btn btn-danger text-sm"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
