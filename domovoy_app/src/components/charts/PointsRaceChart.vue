<script setup lang="ts">
import { computed, ref } from 'vue'
import { format, isToday } from 'date-fns'
import { useElementWidth } from './useElementWidth'

export interface ChartSeries {
  id: number
  name: string
  values: number[]
  isSelf?: boolean
}

// Several housemates' points on ONE pair of axes, so the lines compare
// directly. With `cumulative`, each line is a running total over the period.
const {
  dates,
  series,
  colors,
  cumulative = false,
  height = 200,
  title
} = defineProps<{
  dates: string[]
  series: ChartSeries[]
  colors: Map<number, string>
  cumulative?: boolean
  height?: number
  title: string
}>()

const root = ref<HTMLElement | null>(null)
const width = useElementWidth(root, 320)
const hoverIndex = ref<number | null>(null)
const showTable = ref(false)

const plotted = computed(() =>
  series.map((s) => {
    if (!cumulative) return { ...s, points: s.values }
    let total = 0
    return { ...s, points: s.values.map((v) => (total += v)) }
  })
)

// Up to four series get a name label at the line end, as long as the labels
// don't collide; otherwise the legend and tooltip carry identity.
const MAX_DIRECT_LABELS = 4
const margin = computed(() => ({
  top: 10,
  right: plotted.value.length <= MAX_DIRECT_LABELS ? 72 : 12,
  bottom: 22,
  left: 32
}))
const plotWidth = computed(() => Math.max(10, width.value - margin.value.left - margin.value.right))
const plotHeight = computed(() => height - margin.value.top - margin.value.bottom)

// Round tick steps (1, 2, 5 × 10^n) giving about four gridlines.
const ticks = computed(() => {
  const max = Math.max(1, ...plotted.value.flatMap((s) => s.points))
  const rough = max / 4
  const power = 10 ** Math.floor(Math.log10(rough))
  const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? power * 10
  const top = Math.ceil(max / step) * step
  const values: number[] = []
  for (let v = 0; v <= top + step / 2; v += step) values.push(v)
  return { top, values }
})

const x = (i: number) =>
  margin.value.left +
  (dates.length <= 1 ? plotWidth.value / 2 : (i / (dates.length - 1)) * plotWidth.value)
const y = (v: number) => margin.value.top + (1 - v / ticks.value.top) * plotHeight.value

const lines = computed(() =>
  plotted.value.map((s) => ({
    ...s,
    color: colors.get(s.id) ?? '#9c9c9c',
    path: s.points.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' '),
    end: { x: x(s.points.length - 1), y: y(s.points[s.points.length - 1] ?? 0) },
    last: s.points[s.points.length - 1] ?? 0
  }))
)

const endLabels = computed(() => {
  if (lines.value.length > MAX_DIRECT_LABELS) return []
  const sorted = [...lines.value].sort((a, b) => a.end.y - b.end.y)
  const collide = sorted.some((s, i) => i > 0 && s.end.y - sorted[i - 1].end.y < 14)
  return collide ? [] : sorted
})

function dateLabel(value: string | undefined, long = false) {
  if (!value) return ''
  const date = new Date(value)
  if (isToday(date)) return 'Today'
  return format(date, long ? 'EEE d MMM' : 'd MMM')
}

// Crosshair: snap to the nearest day under the pointer.
function onPointer(event: PointerEvent) {
  const box = (event.currentTarget as SVGElement).getBoundingClientRect()
  const px = event.clientX - box.left - margin.value.left
  const ratio = dates.length <= 1 ? 0 : px / plotWidth.value
  hoverIndex.value = Math.min(dates.length - 1, Math.max(0, Math.round(ratio * (dates.length - 1))))
}

function onKey(event: KeyboardEvent) {
  const last = dates.length - 1
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault()
    const current = hoverIndex.value ?? last
    hoverIndex.value = Math.min(last, Math.max(0, current + (event.key === 'ArrowLeft' ? -1 : 1)))
  } else if (event.key === 'Escape') {
    hoverIndex.value = null
  }
}

const tooltip = computed(() => {
  const i = hoverIndex.value
  if (i === null) return null
  const rows = lines.value
    .map((s) => ({
      id: s.id,
      name: s.name,
      isSelf: s.isSelf,
      color: s.color,
      value: s.points[i] ?? 0
    }))
    .sort((a, b) => b.value - a.value)
  // Keep the box inside the chart: flip to the left of the crosshair near the right edge.
  const left = x(i) > width.value / 2 ? undefined : x(i) + 10
  const right = left === undefined ? width.value - x(i) + 10 : undefined
  return { i, date: dateLabel(dates[i], true), rows, left, right }
})
</script>
<template>
  <div ref="root" class="race">
    <ul class="race__legend" :aria-label="`${title} legend`">
      <li v-for="s in lines" :key="s.id">
        <span class="race__key" :style="{ background: s.color }"></span>
        <span>{{ s.name }}<template v-if="s.isSelf"> (you)</template></span>
      </li>
    </ul>

    <div class="race__plot">
      <svg
        :width="width"
        :height="height"
        role="img"
        :aria-label="`${title}. Use the table view for the values.`"
        tabindex="0"
        class="race__svg"
        @pointermove="onPointer"
        @pointerdown="onPointer"
        @pointerleave="hoverIndex = null"
        @keydown="onKey"
        @blur="hoverIndex = null"
      >
        <!-- Recessive grid and y ticks -->
        <g v-for="t in ticks.values" :key="t">
          <line
            :x1="margin.left"
            :x2="margin.left + plotWidth"
            :y1="y(t)"
            :y2="y(t)"
            class="race__grid"
          />
          <text :x="margin.left - 6" :y="y(t)" class="race__tick" text-anchor="end" dy="0.32em">
            {{ t }}
          </text>
        </g>
        <!-- X labels: first and last day -->
        <text :x="x(0)" :y="height - 4" class="race__tick" text-anchor="start">
          {{ dateLabel(dates[0]) }}
        </text>
        <text :x="x(dates.length - 1)" :y="height - 4" class="race__tick" text-anchor="end">
          {{ dateLabel(dates[dates.length - 1]) }}
        </text>

        <line
          v-if="tooltip"
          :x1="x(tooltip.i)"
          :x2="x(tooltip.i)"
          :y1="margin.top"
          :y2="margin.top + plotHeight"
          class="race__crosshair"
        />

        <path
          v-for="s in lines"
          :key="`line-${s.id}`"
          :d="s.path"
          fill="none"
          :stroke="s.color"
          stroke-width="2"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
        <circle
          v-for="s in lines"
          :key="`end-${s.id}`"
          :cx="s.end.x"
          :cy="s.end.y"
          r="4"
          :fill="s.color"
          class="race__dot"
        />
        <template v-if="tooltip">
          <circle
            v-for="s in lines"
            :key="`hover-${s.id}`"
            :cx="x(tooltip.i)"
            :cy="y(s.points[tooltip.i] ?? 0)"
            r="4"
            :fill="s.color"
            class="race__dot"
          />
        </template>
        <text
          v-for="s in endLabels"
          :key="`label-${s.id}`"
          :x="s.end.x + 8"
          :y="s.end.y"
          dy="0.32em"
          class="race__label"
          :class="{ 'race__label--self': s.isSelf }"
        >
          {{ s.name }} {{ s.last }}
        </text>
      </svg>

      <div
        v-if="tooltip"
        class="race__tooltip"
        :style="{
          left: tooltip.left !== undefined ? `${tooltip.left}px` : undefined,
          right: tooltip.right !== undefined ? `${tooltip.right}px` : undefined
        }"
        aria-live="polite"
      >
        <div class="race__tooltip-date">{{ tooltip.date }}</div>
        <div v-for="row in tooltip.rows" :key="row.id" class="race__tooltip-row">
          <span class="race__line-key" :style="{ background: row.color }"></span>
          <strong>{{ row.value }}</strong>
          <span class="race__tooltip-name"
            >{{ row.name }}<template v-if="row.isSelf"> (you)</template></span
          >
        </div>
      </div>
    </div>

    <v-btn
      size="small"
      variant="text"
      class="mt-1 px-1"
      :prepend-icon="showTable ? 'mdi-chart-line' : 'mdi-table'"
      @click="showTable = !showTable"
    >
      {{ showTable ? 'Hide table' : 'Show as table' }}
    </v-btn>
    <v-table v-if="showTable" density="compact" class="race__table">
      <thead>
        <tr>
          <th>Day</th>
          <th v-for="s in lines" :key="s.id" class="text-right">{{ s.name }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(day, i) in dates" :key="day">
          <td>{{ dateLabel(day, true) }}</td>
          <td v-for="s in lines" :key="s.id" class="text-right">{{ s.points[i] }}</td>
        </tr>
      </tbody>
    </v-table>
  </div>
</template>
<style scoped>
.race {
  position: relative;
  --text-primary: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  --text-secondary: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.race__legend {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  padding: 0;
  margin: 0 0 8px;
  font-size: 0.8125rem;
  color: var(--text-primary);
}
.race__legend li {
  display: flex;
  align-items: center;
  gap: 6px;
}
.race__key,
.race__line-key {
  display: inline-block;
  width: 14px;
  height: 2px;
  border-radius: 1px;
}
.race__plot {
  position: relative;
}
.race__svg {
  display: block;
  touch-action: pan-y;
  outline: none;
}
.race__svg:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
  border-radius: 4px;
}
.race__grid {
  stroke: rgba(var(--v-theme-on-surface), 0.12);
  stroke-width: 1;
}
.race__crosshair {
  stroke: rgba(var(--v-theme-on-surface), 0.45);
  stroke-width: 1;
}
.race__tick {
  fill: var(--text-secondary);
  font-size: 11px;
}
.race__label {
  fill: var(--text-secondary);
  font-size: 12px;
}
.race__label--self {
  fill: var(--text-primary);
  font-weight: 600;
}
.race__dot {
  stroke: rgb(var(--v-theme-surface));
  stroke-width: 2;
}
.race__tooltip {
  position: absolute;
  top: 0;
  min-width: 120px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgb(var(--v-theme-background));
  border: 1px solid rgba(var(--v-theme-on-surface), 0.16);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  font-size: 0.8125rem;
  pointer-events: none;
  z-index: 1;
}
.race__tooltip-date {
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.race__tooltip-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}
.race__tooltip-name {
  color: var(--text-secondary);
}
.race__table {
  max-height: 240px;
  overflow-y: auto;
}
</style>
