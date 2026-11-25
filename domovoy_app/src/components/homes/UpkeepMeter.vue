<script setup lang="ts">
import type { UpkeepStatus } from '@/utils/upkeep'

// Upkeep as a filled bar, in its status colour, full at 100% of the ideal.
const { ratio, status, label } = defineProps<{
  ratio: number
  status: UpkeepStatus | null
  label: string
}>()
</script>
<template>
  <div
    class="meter"
    :class="`meter--${status?.color ?? 'success'}`"
    role="meter"
    :aria-valuenow="Math.round(ratio * 100)"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-label="label"
  >
    <span class="meter__fill" :style="{ width: `${Math.min(100, ratio * 100)}%` }"></span>
  </div>
</template>
<style scoped>
.meter {
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  background: rgba(var(--meter-color), 0.2);
}
.meter__fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: rgb(var(--meter-color));
}
.meter--success {
  --meter-color: var(--v-theme-success);
}
.meter--warning {
  --meter-color: var(--v-theme-warning);
}
.meter--error {
  --meter-color: var(--v-theme-error);
}
</style>
