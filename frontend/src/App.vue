<script setup>
import { RouterView } from 'vue-router'
import Navbar from './components/Navbar.vue'
import { useThemeStore } from './stores/theme'

const themeStore = useThemeStore()
</script>

<template>
  <div class="min-h-screen flex flex-col bg-immersive relative">
    <Navbar />
    <main class="container mx-auto px-4 py-8 pb-20 flex-1 relative z-10">
      <RouterView />
    </main>
    <footer class="fixed bottom-0 left-0 right-0 z-10 py-4 border-t border-gray-200 dark:border-white/5 bg-white/60 dark:bg-transparent" style="backdrop-filter: blur(8px);">
      <div class="container mx-auto px-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-gray-500 dark:text-gray-500 font-semibold">
        <router-link
          to="/dmca"
          class="inline-flex items-center gap-1.5 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
        >
          <i class="fas fa-shield-alt"></i>
          Retrait de contenu
        </router-link>
      </div>
    </footer>
  </div>
</template>
