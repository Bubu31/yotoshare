<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const success = ref(false)
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true

  try {
    await authStore.login(username.value, password.value)
    success.value = true
    setTimeout(() => {
      router.push('/archives')
    }, 1000)
  } catch (e) {
    error.value = 'Identifiants incorrects'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-md mx-auto mt-8 md:mt-16 px-4 md:px-0">
    <div class="card p-6 md:p-8">
      <div class="text-center mb-8">
        <div class="w-20 h-20 mx-auto rounded-2xl flex items-center justify-center mb-4" style="background: linear-gradient(135deg, #6366f1, #38bdf8); box-shadow: 0 0 30px -5px rgba(99, 102, 241, 0.5);">
          <i class="fas fa-lock text-3xl text-white"></i>
        </div>
        <h1 class="text-2xl font-extrabold text-gray-900 dark:text-white">Connexion</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-2 font-medium">Accédez au tableau de bord</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <div
          v-if="success"
          class="px-4 py-3 rounded-xl text-emerald-700 dark:text-emerald-300 font-semibold bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20"
        >
          <i class="fas fa-check-circle mr-2"></i>
          Connexion réussie ! Redirection...
        </div>

        <div
          v-if="error"
          class="px-4 py-3 rounded-xl text-rose-700 dark:text-rose-300 font-semibold bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20"
        >
          <i class="fas fa-exclamation-circle mr-2"></i>
          {{ error }}
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">
            Nom d'utilisateur
          </label>
          <div class="relative">
            <i class="fas fa-user absolute left-4 top-1/2 -translate-y-1/2 text-gray-500"></i>
            <input
              v-model="username"
              type="text"
              class="input pl-12"
              placeholder="admin"
              required
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">
            Mot de passe
          </label>
          <div class="relative">
            <i class="fas fa-key absolute left-4 top-1/2 -translate-y-1/2 text-gray-500"></i>
            <input
              v-model="password"
              type="password"
              class="input pl-12"
              placeholder="••••••••"
              required
            />
          </div>
        </div>

        <button
          type="submit"
          class="btn btn-primary w-full"
          :disabled="loading"
        >
          <i v-if="loading" class="fas fa-spinner fa-spin mr-2"></i>
          <i v-else class="fas fa-sign-in-alt mr-2"></i>
          Se connecter
        </button>
      </form>
    </div>
  </div>
</template>
