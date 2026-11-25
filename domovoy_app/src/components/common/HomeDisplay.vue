<script setup lang="ts">
import { computed } from 'vue'
import { useSlotTextContent } from './utils'
import { useHomesStore } from '@/stores/homes'

const homesStore = useHomesStore()

const inputValue = useSlotTextContent()
const content = computed(
  () => homesStore.homes?.find((home) => home.id?.toString() === inputValue.value)?.name
)
</script>
<template>
  <span v-if="!homesStore.homes" class="dmv-placeholder" aria-label="Loading"></span>
  <template v-else>{{ content }}</template>
</template>
