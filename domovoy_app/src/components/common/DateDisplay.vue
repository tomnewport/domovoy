<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed } from 'vue'
import { useSlotTextContent } from './utils'
import {
  startOfWeek,
  addWeeks,
  format,
  isTomorrow,
  isYesterday,
  isToday,
  isThisWeek,
  isThisYear
} from 'date-fns'

const content = useSlotTextContent()
const now = ref<Date>(new Date())
const timer = ref<number | null>(null)

const day = 1000 * 60 * 60 * 24

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
  if (variant === 'natural') {
    if (isToday(value)) return 'Today'
    if (isYesterday(value)) return 'Yesterday'
    if (isTomorrow(value)) return 'Tomorrow'
    if (isThisWeek(value, { weekStartsOn: 1 })) return `this ${format(value, 'EEEE')}`
    if (value > now.value && value < startOfWeek(addWeeks(now.value, 2), { weekStartsOn: 1 }))
      return `next ${format(value, 'EEEE')}`
    if (value < now.value && value > startOfWeek(addWeeks(now.value, -1), { weekStartsOn: 1 }))
      return `last ${format(value, 'EEEE')}`
    if (isThisYear(value)) return format(value, 'do MMMM')
    return format(value, 'do MMMM yyy')
  }
  return value.toLocaleDateString()
})
</script>
<template>{{ display }}</template>
