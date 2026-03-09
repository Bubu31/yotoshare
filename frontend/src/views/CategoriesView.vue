<script setup>
import { ref, onMounted } from 'vue'
import { useArchivesStore } from '../stores/archives'
import { useAuthStore } from '../stores/auth'
import { useMessage } from '../composables/useMessage'
import AlertMessage from '../components/AlertMessage.vue'

const archivesStore = useArchivesStore()
const authStore = useAuthStore()
const { message, showMessage } = useMessage()

const newCategory = ref({ name: '', icon: 'fas fa-folder' })
const showCategoryForm = ref(false)

onMounted(async () => {
  await archivesStore.fetchCategories()
})

async function addCategory() {
  if (!newCategory.value.name) return

  try {
    await archivesStore.createCategory(newCategory.value)
    newCategory.value = { name: '', icon: 'fas fa-folder' }
    showCategoryForm.value = false
    showMessage('success', 'Catégorie ajoutée')
  } catch (e) {
    showMessage('error', 'Erreur lors de l\'ajout')
  }
}

async function removeCategory(id) {
  if (!confirm('Supprimer cette catégorie ?')) return

  try {
    await archivesStore.deleteCategory(id)
    showMessage('success', 'Catégorie supprimée')
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
        <i class="fas fa-tags text-primary-600 mr-2"></i>
        Catégories
      </h1>
    </div>

    <AlertMessage :message="message" />

    <div class="flex justify-end mb-4">
      <button
        @click="showCategoryForm = !showCategoryForm"
        class="btn btn-secondary text-sm"
      >
        <i :class="showCategoryForm ? 'fas fa-times' : 'fas fa-plus'" class="mr-1"></i>
        {{ showCategoryForm ? 'Annuler' : 'Ajouter' }}
      </button>
    </div>

    <div v-if="showCategoryForm" class="card p-4 mb-4">
      <form @submit.prevent="addCategory" class="flex gap-4 items-end">
        <div class="flex-1">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom</label>
          <input
            v-model="newCategory.name"
            type="text"
            class="input"
            placeholder="Nom de la catégorie"
            required
          />
        </div>
        <div class="w-48">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Icône Font Awesome</label>
          <input
            v-model="newCategory.icon"
            type="text"
            class="input"
            placeholder="fas fa-folder"
          />
        </div>
        <button type="submit" class="btn btn-primary">
          <i class="fas fa-check"></i>
        </button>
      </form>
    </div>

    <div class="flex flex-wrap gap-2">
      <div
        v-for="category in archivesStore.categories"
        :key="category.id"
        class="flex items-center bg-white dark:bg-gray-800 px-4 py-2 rounded-lg shadow-sm border dark:border-gray-700"
      >
        <i :class="category.icon" class="mr-2 text-primary-600"></i>
        <span class="dark:text-white">{{ category.name }}</span>
        <button
          v-if="authStore.hasPermission('categories', 'delete')"
          @click="removeCategory(category.id)"
          class="ml-3 text-red-400 hover:text-red-600"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div
        v-if="archivesStore.categories.length === 0"
        class="text-gray-500 dark:text-gray-400"
      >
        Aucune catégorie
      </div>
    </div>
  </div>
</template>
