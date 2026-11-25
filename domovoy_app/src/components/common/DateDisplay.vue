<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed } from 'vue'
import { useSlotTextContent } from './utils'
import { formatNaturalDate } from '@/utils/dates'

const content = useSlotTextContent()
const now = ref<Date>(new Date())
const timer = ref<number | null>(null)

const { variant } = defineProps<{ variant?: 'natural' }>()

onMounted(() => {
  timer.value = setInterval(() => {
    now.value = new Date()
  }, 60000)
})
onBeforeUnmount(() => {
  timer.value && clearInterval(timer.value)
})
const display = computed(() => {
  if (!content.value) return ''
  const value = new Date(content.value)
  if (variant === 'natural') return formatNaturalDate(value, now.value)
  return value.toLocaleDateString()
})
</script>
<template>{{ display }}</template>
