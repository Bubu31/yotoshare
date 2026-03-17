<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const themeStore = useThemeStore()
const router = useRouter()

const mobileMenuOpen = ref(false)

function logout() {
  authStore.logout()
  mobileMenuOpen.value = false
  router.push('/login')
}

function closeMenu() {
  mobileMenuOpen.value = false
}
</script>

<template>
  <nav class="relative z-20 glass">
    <div class="container mx-auto px-4">
      <div class="flex justify-between items-center h-16">
        <router-link to="/" class="flex items-center space-x-2.5 group" @click="closeMenu">
          <div class="w-9 h-9 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-200 shadow-lg shadow-indigo-500/30" style="background: linear-gradient(135deg, #6366f1, #38bdf8);">
            <i class="fas fa-share-nodes text-white text-sm"></i>
          </div>
          <span class="text-xl font-extrabold bg-gradient-to-r from-indigo-500 to-cyan-500 dark:from-indigo-400 dark:to-cyan-400 bg-clip-text text-transparent">YotoShare</span>
        </router-link>

        <!-- Desktop menu -->
        <div class="hidden md:flex items-center space-x-1">
          <template v-if="authStore.isAuthenticated">
            <router-link
              v-if="authStore.hasPermission('archives', 'access')"
              to="/archives"
              class="px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-white font-semibold transition-all duration-200 hover:bg-indigo-50 dark:hover:bg-white/5"
            >
              <i class="fas fa-book mr-1.5"></i>
              Archives
            </router-link>
            <router-link
              v-if="authStore.hasPermission('packs', 'access')"
              to="/archives/packs"
              class="px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-white font-semibold transition-all duration-200 hover:bg-indigo-50 dark:hover:bg-white/5"
            >
              <i class="fas fa-box-open mr-1.5"></i>
              Packs
            </router-link>
            <router-link
              v-if="authStore.hasPermission('categories', 'access') || authStore.hasPermission('ages', 'access') || authStore.hasPermission('users', 'access') || authStore.hasPermission('roles', 'access')"
              to="/admin"
              class="px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-white font-semibold transition-all duration-200 hover:bg-indigo-50 dark:hover:bg-white/5"
            >
              <i class="fas fa-cog mr-1.5"></i>
              Admin
            </router-link>
            <button
              @click="logout"
              class="px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-400 hover:text-rose-600 dark:hover:text-rose-400 font-semibold transition-all duration-200 hover:bg-rose-50 dark:hover:bg-rose-500/10"
            >
              <i class="fas fa-sign-out-alt mr-1.5"></i>
              Déconnexion
            </button>
          </template>
          <template v-else>
            <router-link
              to="/login"
              class="btn btn-primary text-sm"
            >
              <i class="fas fa-sign-in-alt mr-1.5"></i>
              Connexion
            </router-link>
          </template>

          <button
            @click="themeStore.toggle()"
            class="ml-2 p-2 text-gray-500 hover:text-amber-500 rounded-lg hover:bg-amber-50 dark:hover:bg-white/5 transition-all duration-200"
            :title="themeStore.isDark ? 'Mode clair' : 'Mode sombre'"
            :aria-label="themeStore.isDark ? 'Mode clair' : 'Mode sombre'"
          >
            <i :class="themeStore.isDark ? 'fas fa-sun' : 'fas fa-moon'"></i>
          </button>
        </div>

        <!-- Mobile menu button -->
        <div class="flex items-center space-x-2 md:hidden">
          <button
            @click="themeStore.toggle()"
            class="p-2 text-gray-500 hover:text-amber-500 rounded-lg hover:bg-amber-50 dark:hover:bg-white/5 transition-all duration-200"
            :aria-label="themeStore.isDark ? 'Mode clair' : 'Mode sombre'"
          >
            <i :class="themeStore.isDark ? 'fas fa-sun' : 'fas fa-moon'"></i>
          </button>
          <button
            @click="mobileMenuOpen = !mobileMenuOpen"
            class="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-white/5 transition-all duration-200"
            :aria-label="mobileMenuOpen ? 'Fermer menu' : 'Ouvrir menu'"
          >
            <i :class="mobileMenuOpen ? 'fas fa-times' : 'fas fa-bars'" class="text-xl"></i>
          </button>
        </div>
      </div>

      <!-- Mobile menu -->
      <div
        v-show="mobileMenuOpen"
        class="md:hidden py-4 space-y-1 border-t border-gray-200 dark:border-white/5"
      >
        <template v-if="authStore.isAuthenticated">
          <router-link
            v-if="authStore.hasPermission('archives', 'access')"
            to="/archives"
            @click="closeMenu"
            class="block px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-white hover:bg-indigo-50 dark:hover:bg-white/5 rounded-lg font-semibold transition-all"
          >
            <i class="fas fa-book mr-2"></i>
            Archives
          </router-link>
          <router-link
            v-if="authStore.hasPermission('packs', 'access')"
            to="/archives/packs"
            @click="closeMenu"
            class="block px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-white hover:bg-indigo-50 dark:hover:bg-white/5 rounded-lg font-semibold transition-all"
          >
            <i class="fas fa-box-open mr-2"></i>
            Packs
          </router-link>
          <router-link
            v-if="authStore.hasPermission('categories', 'access') || authStore.hasPermission('ages', 'access') || authStore.hasPermission('users', 'access') || authStore.hasPermission('roles', 'access')"
            to="/admin"
            @click="closeMenu"
            class="block px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-white hover:bg-indigo-50 dark:hover:bg-white/5 rounded-lg font-semibold transition-all"
          >
            <i class="fas fa-cog mr-2"></i>
            Admin
          </router-link>
          <button
            @click="logout"
            class="block w-full text-left px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg font-semibold transition-all"
          >
            <i class="fas fa-sign-out-alt mr-2"></i>
            Déconnexion
          </button>
        </template>
        <template v-else>
          <router-link
            to="/login"
            @click="closeMenu"
            class="block px-3 py-2.5 text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-white hover:bg-indigo-50 dark:hover:bg-white/5 rounded-lg font-semibold transition-all"
          >
            <i class="fas fa-sign-in-alt mr-2"></i>
            Connexion
          </router-link>
        </template>
      </div>
    </div>
  </nav>
</template>
