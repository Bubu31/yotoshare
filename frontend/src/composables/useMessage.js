import { ref } from 'vue'

export function useMessage() {
  const message = ref(null)

  function showMessage(type, text, duration = 5000) {
    message.value = { type, text }
    if (duration > 0) {
      setTimeout(() => {
        message.value = null
      }, duration)
    }
  }

  return { message, showMessage }
}
