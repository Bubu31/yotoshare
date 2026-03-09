<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  itemLabel: {
    type: String,
    default: '',
  },
  isOpen: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'confirm'])

const loading = ref(false)

watch(() => props.isOpen, (open) => {
  if (!open) {
    loading.value = false
  }
})

function handleConfirm() {
  loading.value = true
  emit('confirm', props.item)
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        class="absolute inset-0 bg-black bg-opacity-50"
        @click="emit('close')"
      ></div>

      <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <button
          @click="emit('close')"
          class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <i class="fas fa-times"></i>
        </button>

        <div class="text-center">
          <div class="w-16 h-16 mx-auto bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center mb-4">
            <i class="fab fa-discord text-3xl text-indigo-600 dark:text-indigo-400"></i>
          </div>

          <h3 class="text-xl font-semibold text-gray-800 dark:text-white mb-2">
            Publier sur Discord
          </h3>

          <p class="text-gray-600 dark:text-gray-400 mb-6">
            Vous êtes sur le point de publier
            <strong>{{ item.title || item.name }}</strong>
            {{ itemLabel ? `(${itemLabel})` : '' }}
            sur le serveur Discord. Un post sera créé dans le forum.
          </p>

          <div class="flex flex-col-reverse sm:flex-row gap-3 sm:justify-center">
            <button
              @click="emit('close')"
              class="btn btn-secondary"
              :disabled="loading"
            >
              Annuler
            </button>
            <button
              @click="handleConfirm"
              class="btn btn-primary"
              :disabled="loading"
            >
              <i v-if="loading" class="fas fa-spinner fa-spin mr-2"></i>
              <i v-else class="fab fa-discord mr-2"></i>
              Publier
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
