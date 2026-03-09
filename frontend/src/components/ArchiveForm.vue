<script setup>
import { ref, computed } from 'vue'
import TagInput from './TagInput.vue'

const props = defineProps({
  categories: {
    type: Array,
    default: () => [],
  },
  ages: {
    type: Array,
    default: () => [],
  },
  initialData: {
    type: Object,
    default: null,
  },
  isEdit: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit', 'cancel'])

const title = ref(props.initialData?.title || '')
const author = ref(props.initialData?.author || '')
const description = ref(props.initialData?.description || '')
const selectedCategories = ref(props.initialData?.categories?.map(c => c.name) || [])
const selectedAges = ref(props.initialData?.ages?.map(a => a.name) || [])
const archiveFile = ref(null)
const loading = ref(false)

const isValid = computed(() => {
  if (!props.isEdit && !archiveFile.value) return false
  return true
})

function handleArchiveChange(event) {
  const file = event.target.files[0]
  if (file && file.name.endsWith('.zip')) {
    archiveFile.value = file
  } else {
    archiveFile.value = null
    alert('Veuillez sélectionner un fichier .zip')
  }
}

async function handleSubmit() {
  if (!isValid.value) return

  loading.value = true

  const formData = new FormData()
  if (author.value) formData.append('author', author.value)
  if (title.value) formData.append('title', title.value)
  if (description.value) formData.append('description', description.value)
  formData.append('categories', JSON.stringify(selectedCategories.value))
  formData.append('ages', JSON.stringify(selectedAges.value))
  if (archiveFile.value) formData.append('archive_file', archiveFile.value)

  emit('submit', formData)
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-6">
    <div v-if="!isEdit" class="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400 px-4 py-3 rounded-lg">
      <i class="fas fa-info-circle mr-2"></i>
      Le titre et la couverture seront automatiquement extraits de l'archive.
    </div>

    <div v-if="!isEdit">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        Archive (.zip) *
      </label>
      <input
        type="file"
        accept=".zip"
        @change="handleArchiveChange"
        class="input"
        required
      />
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        Titre
        <span class="text-gray-500 dark:text-gray-400 font-normal">(optionnel, extrait de l'archive)</span>
      </label>
      <input
        v-model="title"
        type="text"
        class="input"
        placeholder="Laissez vide pour utiliser le titre de l'archive"
      />
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        Auteur
        <span class="text-gray-500 dark:text-gray-400 font-normal">(optionnel)</span>
      </label>
      <input
        v-model="author"
        type="text"
        class="input"
        placeholder="Nom de l'auteur"
      />
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        Description
      </label>
      <textarea
        v-model="description"
        class="input"
        rows="3"
        placeholder="Description du livre (optionnel)"
      ></textarea>
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        <i class="fas fa-folder mr-1"></i>
        Catégories
      </label>
      <TagInput
        v-model="selectedCategories"
        :suggestions="categories"
        placeholder="Ajouter une catégorie..."
        icon="fas fa-folder"
      />
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        <i class="fas fa-child mr-1"></i>
        Âges
      </label>
      <TagInput
        v-model="selectedAges"
        :suggestions="ages"
        placeholder="Ajouter un âge..."
        icon="fas fa-child"
      />
    </div>

    <div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
      <button
        type="button"
        @click="emit('cancel')"
        class="btn btn-secondary"
        :disabled="loading || disabled"
      >
        Annuler
      </button>
      <button
        type="submit"
        class="btn btn-primary"
        :disabled="!isValid || loading || disabled"
      >
        <i v-if="loading || disabled" class="fas fa-spinner fa-spin mr-2"></i>
        {{ isEdit ? 'Modifier' : 'Ajouter' }}
      </button>
    </div>
  </form>
</template>
