<template>
  <div
    v-if="message?.text"
    :class="[
      'mb-6 px-4 py-3 rounded-lg',
      message.type === 'success' ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800' :
      message.type === 'info' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800' :
      'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'
    ]"
  >
    <i :class="message.type === 'success' ? 'fas fa-check-circle' : message.type === 'info' ? 'fas fa-info-circle' : 'fas fa-exclamation-circle'" class="mr-2"></i>
    {{ message.text }}
  </div>
</template>

<script setup>
defineProps({
  message: {
    type: Object,
    required: true,
  },
})
</script>
