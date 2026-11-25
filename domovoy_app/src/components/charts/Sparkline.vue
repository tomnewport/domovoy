<script setup lang="ts">
import { computed, ref } from 'vue'
import { useElementWidth } from './useElementWidth'

// A small trend line. Pass the same `max` to every sparkline you want to
// compare, so they share one y scale (0 at the bottom, `max` at the top).
const {
  values,
  max,
  color,
  height = 28,
  label
} = defineProps<{
  values: number[]
  max?: number
  color: string
  height?: number
  label: string
}>()

const root = ref<HTMLElement | null>(null)
const width = useElementWidth(root, 120)
const PAD = 4 // keeps the 2px line and the end dot inside the box

const top = computed(() => Math.max(max ?? 0, ...values, 1))

const points = computed(() => {
  const n = values.length
  const usable = width.value - PAD * 2
  return values.map((value, i) => {
    const x = PAD + (n === 1 ? usable / 2 : (i / (n - 1)) * usable)
    const y = PAD + (1 - value / top.value) * (height - PAD * 2)
    return [x, y] as const
  })
})

const line = computed(() => points.value.map(([x, y]) => `${x},${y}`).join(' '))
const area = computed(() => {
  const pts = points.value
  if (!pts.length) return ''
  const base = height - PAD
  return `${pts[0][0]},${base} ${line.value} ${pts[pts.length - 1][0]},${base}`
})
const end = computed(() => points.value[points.value.length - 1])
</script>
<template>
  <div ref="root" class="sparkline">
    <svg :width="width" :height="height" role="img" :aria-label="label">
      <polygon v-if="area" :points="area" :fill="color" fill-opacity="0.1" />
      <polyline
        :points="line"
        fill="none"
        :stroke="color"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
      <circle
        v-if="end"
        :cx="end[0]"
        :cy="end[1]"
        r="4"
        :fill="color"
        stroke="rgb(var(--v-theme-surface))"
        stroke-width="2"
      />
    </svg>
  </div>
</template>
<style scoped>
.sparkline {
  width: 100%;
  line-height: 0;
}
</style>
