<script setup>
import { ref, onMounted } from 'vue'
import { useArchivesStore } from '../stores/archives'
import { useAuthStore } from '../stores/auth'
import { useMessage } from '../composables/useMessage'
import AlertMessage from '../components/AlertMessage.vue'

const archivesStore = useArchivesStore()
const authStore = useAuthStore()
const { message, showMessage } = useMessage()

const newAge = ref({ name: '', icon: 'fas fa-child' })
const showAgeForm = ref(false)

onMounted(async () => {
  await archivesStore.fetchAges()
})

async function addAge() {
  if (!newAge.value.name) return

  try {
    await archivesStore.createAge(newAge.value)
    newAge.value = { name: '', icon: 'fas fa-child' }
    showAgeForm.value = false
    showMessage('success', 'Âge ajouté')
  } catch (e) {
    showMessage('error', 'Erreur lors de l\'ajout')
  }
}

async function removeAge(id) {
  if (!confirm('Supprimer cet âge ?')) return

  try {
    await archivesStore.deleteAge(id)
    showMessage('success', 'Âge supprimé')
  } catch (e) {
    showMessage('error', 'Erreur lors de la suppression')
  }
}

</script>

<template>
  <div>
    <div class="flex items-center mb-8">
      <router-link to="/admin" class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mr-4">
        <i class="fas fa-arrow-left text-xl"></i>
      </router-link>
      <h1 class="text-3xl font-bold text-gray-800 dark:text-white">
        <i class="fas fa-child text-green-600 mr-2"></i>
        Âges
      </h1>
    </div>

    <AlertMessage :message="message" />

    <div class="flex justify-end mb-4">
      <button
        @click="showAgeForm = !showAgeForm"
        class="btn btn-secondary text-sm"
      >
        <i :class="showAgeForm ? 'fas fa-times' : 'fas fa-plus'" class="mr-1"></i>
        {{ showAgeForm ? 'Annuler' : 'Ajouter' }}
      </button>
    </div>

    <div v-if="showAgeForm" class="card p-4 mb-4">
      <form @submit.prevent="addAge" class="flex gap-4 items-end">
        <div class="flex-1">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom</label>
          <input
            v-model="newAge.name"
            type="text"
            class="input"
            placeholder="Ex: 3-5 ans"
            required
          />
        </div>
        <div class="w-48">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Icône Font Awesome</label>
          <input
            v-model="newAge.icon"
            type="text"
            class="input"
            placeholder="fas fa-child"
          />
        </div>
        <button type="submit" class="btn btn-primary">
          <i class="fas fa-check"></i>
        </button>
      </form>
    </div>

    <div class="flex flex-wrap gap-2">
      <div
        v-for="age in archivesStore.ages"
        :key="age.id"
        class="flex items-center bg-white dark:bg-gray-800 px-4 py-2 rounded-lg shadow-sm border dark:border-gray-700"
      >
        <i :class="age.icon" class="mr-2 text-green-600"></i>
        <span class="dark:text-white">{{ age.name }}</span>
        <button
          v-if="authStore.hasPermission('ages', 'delete')"
          @click="removeAge(age.id)"
          class="ml-3 text-red-400 hover:text-red-600"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div
        v-if="archivesStore.ages.length === 0"
        class="text-gray-500 dark:text-gray-400"
      >
        Aucun âge
      </div>
    </div>
  </div>
</template>
