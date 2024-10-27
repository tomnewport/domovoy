<script setup lang="ts">
import { computed } from 'vue'
import { useSlotTextContent } from './utils'
import { useUserLookup, useCurrentUser } from '@/lookups/user'
const { variant = 'full' } = defineProps<{ variant?: 'short' | 'full' }>()
const content = useSlotTextContent()
const user = useUserLookup({ id: parseInt(content.value || '') })
const me = useCurrentUser()
const value = computed(() => {
  if (!user.value) return '< unknown >'
  const isYou = me.value?.id === user.value.id ? ' (you)' : ''
  if (variant === 'short') return user.value.name_short
  return `${user.value.name_full}${isYou}`
})
</script>
<template>
  {{ value }}
</template>
