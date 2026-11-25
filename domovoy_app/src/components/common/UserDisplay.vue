<script setup lang="ts">
import { computed } from 'vue'
import { useSlotTextContent } from './utils'
import { useUserLookup, useCurrentUser } from '@/lookups/user'
import { useHomesStore } from '@/stores/homes'
const { variant = 'full' } = defineProps<{ variant?: 'short' | 'full' }>()
const content = useSlotTextContent()
const user = useUserLookup({ id: parseInt(content.value || '') })
const me = useCurrentUser()
const homesStore = useHomesStore()
// Names come from the homes list; until it arrives, hold the space instead of
// saying the user is unknown.
const pending = computed(() => !user.value && !homesStore.homes)
const value = computed(() => {
  if (!user.value) return '< unknown >'
  const isYou = me.value?.id === user.value.id ? ' (you)' : ''
  if (variant === 'short') return user.value.name_short
  return `${user.value.name_full}${isYou}`
})
</script>
<template>
  <span v-if="pending" class="dmv-placeholder" aria-label="Loading"></span>
  <template v-else>{{ value }}</template>
</template>
