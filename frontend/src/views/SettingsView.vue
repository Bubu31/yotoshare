<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'

const authStore = useAuthStore()
const generatingGrid = ref(false)

async function generateGridVisual() {
  generatingGrid.value = true
  try {
    const response = await api.get('/api/archives/grid-visual', { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'grid-visual.jpg'
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    alert(err.response?.data?.detail || 'Erreur lors de la génération du visuel')
  } finally {
    generatingGrid.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <div class="mb-6 md:mb-8">
      <h1 class="text-2xl md:text-3xl font-bold text-gray-800 dark:text-white">
        <i class="fas fa-cog text-primary-600 mr-2"></i>
        Administration
      </h1>
      <p class="text-sm md:text-base text-gray-600 dark:text-gray-400">Paramètres et configuration</p>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <router-link
        v-if="authStore.hasPermission('categories', 'access')"
        to="/admin/categories"
        class="card p-6 hover:shadow-lg transition-shadow duration-300 group"
      >
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-primary-100 dark:bg-primary-900 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <i class="fas fa-tags text-xl text-primary-600 dark:text-primary-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-gray-800 dark:text-white">Catégories</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">Gérer les catégories</p>
          </div>
        </div>
      </router-link>

      <router-link
        v-if="authStore.hasPermission('ages', 'access')"
        to="/admin/ages"
        class="card p-6 hover:shadow-lg transition-shadow duration-300 group"
      >
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <i class="fas fa-child text-xl text-green-600 dark:text-green-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-gray-800 dark:text-white">Âges</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">Gérer les tranches d'âge</p>
          </div>
        </div>
      </router-link>

      <router-link
        v-if="authStore.hasPermission('users', 'access')"
        to="/admin/users"
        class="card p-6 hover:shadow-lg transition-shadow duration-300 group"
      >
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-orange-100 dark:bg-orange-900 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <i class="fas fa-users text-xl text-orange-600 dark:text-orange-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-gray-800 dark:text-white">Utilisateurs</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">Gérer les comptes</p>
          </div>
        </div>
      </router-link>

      <router-link
        v-if="authStore.hasPermission('roles', 'access')"
        to="/admin/roles"
        class="card p-6 hover:shadow-lg transition-shadow duration-300 group"
      >
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-red-100 dark:bg-red-900 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <i class="fas fa-shield-alt text-xl text-red-600 dark:text-red-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-gray-800 dark:text-white">Rôles</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">Gérer les permissions</p>
          </div>
        </div>
      </router-link>

      <button
        v-if="authStore.hasPermission('archives', 'modify')"
        @click="generateGridVisual"
        :disabled="generatingGrid"
        class="card p-6 hover:shadow-lg transition-shadow duration-300 group text-left"
      >
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-indigo-100 dark:bg-indigo-900 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <i v-if="!generatingGrid" class="fas fa-th text-xl text-indigo-600 dark:text-indigo-400"></i>
            <i v-else class="fas fa-spinner fa-spin text-xl text-indigo-600 dark:text-indigo-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-gray-800 dark:text-white">Visuel grille</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">Mosaïque des covers Discord</p>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
