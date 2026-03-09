<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
  suggestions: {
    type: Array,
    default: () => [],
  },
  placeholder: {
    type: String,
    default: 'Ajouter...',
  },
  icon: {
    type: String,
    default: 'fas fa-tag',
  },
})

const emit = defineEmits(['update:modelValue'])

const inputValue = ref('')
const showSuggestions = ref(false)
const inputRef = ref(null)

const filteredSuggestions = computed(() => {
  const search = inputValue.value.toLowerCase()
  return props.suggestions
    .filter(s => !search || s.name.toLowerCase().includes(search))
    .filter(s => !props.modelValue.includes(s.name))
    .slice(0, 5)
})

const canCreateNew = computed(() => {
  if (!inputValue.value.trim()) return false
  const search = inputValue.value.toLowerCase().trim()
  const existsInSuggestions = props.suggestions.some(s => s.name.toLowerCase() === search)
  const alreadySelected = props.modelValue.some(v => v.toLowerCase() === search)
  return !existsInSuggestions && !alreadySelected
})

function addTag(name) {
  const trimmed = name.trim()
  if (!trimmed) return
  if (props.modelValue.includes(trimmed)) return

  emit('update:modelValue', [...props.modelValue, trimmed])
  inputValue.value = ''
  // Garder les suggestions ouvertes pour permettre d'ajouter plusieurs tags
}

function removeTag(index) {
  const newValue = [...props.modelValue]
  newValue.splice(index, 1)
  emit('update:modelValue', newValue)
}

function handleKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    if (filteredSuggestions.value.length > 0) {
      addTag(filteredSuggestions.value[0].name)
    } else if (canCreateNew.value) {
      addTag(inputValue.value)
    }
  } else if (e.key === 'Backspace' && !inputValue.value && props.modelValue.length > 0) {
    removeTag(props.modelValue.length - 1)
  }
}

function handleBlur() {
  setTimeout(() => {
    showSuggestions.value = false
  }, 200)
}
</script>

<template>
  <div class="relative">
    <div class="input flex flex-wrap gap-2 items-center min-h-[42px] py-1.5">
      <span
        v-for="(tag, index) in modelValue"
        :key="index"
        class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded-full text-sm"
      >
        <i :class="icon" class="text-xs"></i>
        {{ tag }}
        <button
          type="button"
          @click="removeTag(index)"
          class="hover:text-primary-900 dark:hover:text-primary-100"
        >
          <i class="fas fa-times text-xs"></i>
        </button>
      </span>
      <input
        ref="inputRef"
        v-model="inputValue"
        type="text"
        :placeholder="modelValue.length === 0 ? placeholder : ''"
        class="flex-1 min-w-[120px] bg-transparent border-none outline-none p-0 text-gray-900 dark:text-white placeholder-gray-400"
        @focus="showSuggestions = true"
        @blur="handleBlur"
        @keydown="handleKeydown"
      />
    </div>

    <div
      v-if="showSuggestions && (filteredSuggestions.length > 0 || canCreateNew)"
      class="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden"
    >
      <button
        v-for="suggestion in filteredSuggestions"
        :key="suggestion.id"
        type="button"
        class="w-full px-4 py-2 text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
        @mousedown.prevent="addTag(suggestion.name)"
      >
        <i :class="suggestion.icon || icon" class="text-primary-600"></i>
        {{ suggestion.name }}
      </button>
      <button
        v-if="canCreateNew"
        type="button"
        class="w-full px-4 py-2 text-left text-green-600 dark:text-green-400 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 border-t border-gray-200 dark:border-gray-700"
        @mousedown.prevent="addTag(inputValue)"
      >
        <i class="fas fa-plus"></i>
        Créer "{{ inputValue }}"
      </button>
    </div>
  </div>
</template>
