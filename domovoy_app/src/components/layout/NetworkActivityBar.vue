<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { networkBusy } from '@/services/domovoy/activity'

// Only appear for requests that take a noticeable time, so quick ones don't
// flicker the bar.
const SHOW_AFTER_MS = 250

const visible = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

watch(
  networkBusy,
  (busy) => {
    clearTimeout(timer)
    if (busy) timer = setTimeout(() => (visible.value = true), SHOW_AFTER_MS)
    else visible.value = false
  },
  { immediate: true }
)

onBeforeUnmount(() => clearTimeout(timer))
</script>
<template>
  <v-progress-linear
    :active="visible"
    class="network-activity"
    color="primary"
    height="3"
    indeterminate
    aria-label="Loading"
  />
</template>
<style scoped>
.network-activity {
  position: fixed !important;
  top: 0;
  left: 0;
  right: 0;
  z-index: 3000;
}
</style>
