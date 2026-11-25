import { computed, ref } from 'vue'

// Counts API requests in flight, so the UI can show one app-wide progress bar
// instead of each view guessing whether something is still loading.
const inFlight = ref(0)

export const networkBusy = computed(() => inFlight.value > 0)

export async function trackedFetch(input: RequestInfo | URL, init?: RequestInit) {
  inFlight.value++
  try {
    return await fetch(input, init)
  } finally {
    inFlight.value--
  }
}
