import { ref } from 'vue'

export function useLoadingState() {
  const loading = ref(false)
  const initialized = ref(false)
  const error = ref<string | null>(null)

  const startLoading = () => {
    loading.value = true
    error.value = null
  }

  const finishLoading = () => {
    loading.value = false
    initialized.value = true
  }

  const setError = (errorMessage: string) => {
    error.value = errorMessage
    loading.value = false
  }

  return {
    loading,
    initialized,
    error,
    startLoading,
    finishLoading,
    setError
  }
}
