<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from '../composables/useMessage'
import api from '../services/api'

const router = useRouter()
const { showMessage } = useMessage()

const submissions = ref([])
const loading = ref(true)
const activeTab = ref('pending')

const tabs = [
  { key: 'pending', label: 'En attente', icon: 'fa-clock' },
  { key: 'approved', label: 'Approuvées', icon: 'fa-check-circle' },
  { key: 'rework', label: 'A retravailler', icon: 'fa-wrench' },
  { key: 'rejected', label: 'Rejetées', icon: 'fa-times-circle' },
]

const filteredSubmissions = computed(() => {
  return submissions.value.filter(s => s.status === activeTab.value)
})

const pendingCount = computed(() => {
  return submissions.value.filter(s => s.status === 'pending').length
})

onMounted(async () => {
  await fetchSubmissions()
})

async function fetchSubmissions() {
  loading.value = true
  try {
    const { data } = await api.get('/api/submissions')
    submissions.value = data
  } catch (e) {
    showMessage('error', e.response?.data?.detail || 'Erreur lors du chargement')
  } finally {
    loading.value = false
  }
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDuration(ms) {
  if (!ms) return '—'
  const totalSec = Math.round(ms / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

async function deleteSubmission(sub) {
  if (!confirm(`Supprimer la soumission "${sub.title || 'Sans titre'}" ?`)) return
  try {
    await api.delete(`/api/submissions/${sub.id}`)
    submissions.value = submissions.value.filter(s => s.id !== sub.id)
    showMessage('success', 'Soumission supprimée')
  } catch (e) {
    showMessage('error', e.response?.data?.detail || 'Erreur lors de la suppression')
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const statusColors = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  approved: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  rework: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
}
</script>

<template>
  <div class="max-w-6xl mx-auto">
    <div class="mb-6 md:mb-8">
      <router-link to="/admin" class="text-primary-600 hover:text-primary-800 dark:hover:text-primary-400 mb-4 inline-block">
        <i class="fas fa-arrow-left mr-2"></i>
        Administration
      </router-link>
      <div class="flex items-center gap-3">
        <h1 class="text-2xl md:text-3xl font-bold text-gray-800 dark:text-white">
          <i class="fas fa-inbox text-purple-600 mr-2"></i>
          Soumissions
        </h1>
        <span v-if="pendingCount > 0" class="px-2.5 py-0.5 rounded-full text-sm font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
          {{ pendingCount }} en attente
        </span>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 w-fit">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        @click="activeTab = tab.key"
        :class="[
          'px-4 py-2 rounded-md text-sm font-medium transition-all duration-200',
          activeTab === tab.key
            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
        ]"
      >
        <i :class="['fas', tab.icon, 'mr-1.5']"></i>
        {{ tab.label }}
        <span
          v-if="tab.key === 'pending' && pendingCount > 0"
          class="ml-1.5 px-1.5 py-0.5 rounded-full text-xs bg-amber-500 text-white"
        >
          {{ pendingCount }}
        </span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
    </div>

    <!-- Empty state -->
    <div v-else-if="filteredSubmissions.length === 0" class="text-center py-12">
      <i class="fas fa-inbox text-4xl text-gray-300 dark:text-gray-600 mb-3"></i>
      <p class="text-gray-500 dark:text-gray-400">Aucune soumission {{ activeTab === 'pending' ? 'en attente' : activeTab === 'approved' ? 'approuvée' : activeTab === 'rework' ? 'à retravailler' : 'rejetée' }}</p>
    </div>

    <!-- List (approved / rework / rejected) -->
    <div v-else-if="activeTab === 'approved' || activeTab === 'rejected' || activeTab === 'rework'" class="space-y-3">
      <div
        v-for="sub in filteredSubmissions"
        :key="sub.id"
        class="card p-4"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <h3 class="font-semibold text-gray-800 dark:text-white truncate">
              {{ sub.title || 'Sans titre' }}
            </h3>
            <p v-if="sub.pseudonym" class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              <i class="fas fa-user mr-1"></i>{{ sub.pseudonym }}
            </p>
          </div>
          <span class="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
            {{ formatDate(sub.reviewed_at || sub.created_at) }}
          </span>
        </div>
        <div v-if="sub.rework_comment && activeTab === 'rework'" class="mt-2 px-3 py-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg text-sm text-orange-700 dark:text-orange-400">
          <i class="fas fa-wrench mr-1.5"></i>{{ sub.rework_comment }}
        </div>
        <div v-if="activeTab === 'rework'" class="mt-2 flex justify-end">
          <button
            @click="deleteSubmission(sub)"
            class="text-xs px-3 py-1.5 rounded-lg bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50 transition-colors"
          >
            <i class="fas fa-trash mr-1"></i>Supprimer
          </button>
        </div>
        <div v-if="sub.rejection_reason" class="mt-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-400">
          <i class="fas fa-comment-slash mr-1.5"></i>{{ sub.rejection_reason }}
        </div>
        <div v-else-if="activeTab === 'rejected'" class="mt-2 text-sm text-gray-400 dark:text-gray-500 italic">
          Aucune raison spécifiée
        </div>
      </div>
    </div>

    <!-- Grid (pending) -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="sub in filteredSubmissions"
        :key="sub.id"
        @click="router.push(`/admin/submissions/${sub.id}`)"
        class="card overflow-hidden cursor-pointer hover:shadow-lg transition-shadow duration-200 group"
      >
        <!-- Cover -->
        <div class="aspect-[4/3] bg-gray-100 dark:bg-gray-800 relative overflow-hidden">
          <img
            v-if="sub.cover_path"
            :src="`/api/archives/cover/${sub.cover_path}`"
            :alt="sub.title"
            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          >
          <div v-else class="w-full h-full flex items-center justify-center">
            <i class="fas fa-file-archive text-4xl text-gray-300 dark:text-gray-600"></i>
          </div>
          <span :class="['absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs font-semibold', statusColors[sub.status]]">
            {{ sub.status === 'pending' ? 'En attente' : sub.status === 'approved' ? 'Approuvée' : 'Rejetée' }}
          </span>
        </div>

        <!-- Info -->
        <div class="p-4">
          <h3 class="font-semibold text-gray-800 dark:text-white truncate">
            {{ sub.title || 'Sans titre' }}
          </h3>
          <p v-if="sub.pseudonym" class="text-sm text-gray-500 dark:text-gray-400 truncate">
            <i class="fas fa-user mr-1"></i>
            {{ sub.pseudonym }}
          </p>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-400 dark:text-gray-500">
            <span><i class="fas fa-weight-hanging mr-1"></i>{{ formatSize(sub.file_size) }}</span>
            <span v-if="sub.total_duration"><i class="fas fa-clock mr-1"></i>{{ formatDuration(sub.total_duration) }}</span>
            <span v-if="sub.chapters_count"><i class="fas fa-list mr-1"></i>{{ sub.chapters_count }} ch.</span>
          </div>
          <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
            {{ formatDate(sub.created_at) }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
