<script setup lang="ts">
import { computed, ref } from 'vue'
import { format, isToday } from 'date-fns'
import type { HomeUpkeep } from '@/services/domovoy/stats'
import type { Period } from './progress'

// How well the home is keeping up: points earned (without overdue bonuses)
// against the ideal, the points a period of every job done on schedule
// would earn.
const { upkeep, period } = defineProps<{ upkeep: HomeUpkeep; period: Period }>()

const showTable = ref(false)
const showBreakdown = ref(false)
const hovered = ref<number | null>(null)

const sum = (values: number[]) => values.reduce((a, b) => a + b, 0)
const round = (n: number) => Math.round(n)

const current = computed(() => {
  const points = sum(upkeep.daily_points.slice(-period))
  const ideal = (upkeep.ideal_per_week * period) / 7
  return { points, ideal, ratio: ideal > 0 ? points / ideal : null }
})

// Status bands: the fill colour carries it, and an icon and label always
// say it too.
const status = computed(() => {
  const r = current.value.ratio
  if (r === null) return null
  if (r >= 1) return { label: 'Ahead', icon: 'mdi-check-circle', color: 'success' }
  if (r >= 0.9) return { label: 'Keeping up', icon: 'mdi-check-circle', color: 'success' }
  if (r >= 0.7) return { label: 'Slipping', icon: 'mdi-alert', color: 'warning' }
  return { label: 'Falling behind', icon: 'mdi-alert-octagon', color: 'error' }
})

const periodLabel = computed(() => (period === 7 ? 'this week' : 'in the last 30 days'))

// Rolling 7-day weeks, oldest first, the last ending today.
const weeks = computed(() => {
  const days = upkeep.daily_points
  const count = Math.floor(days.length / 7)
  return [...Array(count)].map((_, i) => {
    const end = days.length - (count - 1 - i) * 7
    const points = sum(days.slice(end - 7, end))
    const first = new Date(upkeep.dates[end - 7])
    const last = new Date(upkeep.dates[end - 1])
    return {
      points,
      ratio: upkeep.ideal_per_week > 0 ? points / upkeep.ideal_per_week : 0,
      label: isToday(last) ? 'This week' : `${format(first, 'd MMM')} – ${format(last, 'd MMM')}`,
      short: isToday(last) ? 'This week' : format(first, 'd MMM')
    }
  })
})

// Column geometry: the scale tops out at the higher of 100% and the best week.
const CHART_HEIGHT = 72
const BAR_WIDTH = 20
const scaleTop = computed(() => Math.max(1, ...weeks.value.map((w) => w.ratio)))
const barHeight = (ratio: number) =>
  Math.max(ratio > 0 ? 4 : 0, (ratio / scaleTop.value) * CHART_HEIGHT)
const chartWidth = computed(() => weeks.value.length * (BAR_WIDTH + 12))
const idealY = computed(() => CHART_HEIGHT - (1 / scaleTop.value) * CHART_HEIGHT)

const percent = (r: number | null) => (r === null ? '—' : `${round(r * 100)}%`)
// "Daily", "2× a week", "every 3 days", "every 30 days".
function howOften(perWeek: number) {
  const whole = Math.round(perWeek)
  if (whole === 7 && Math.abs(perWeek - 7) < 0.05) return 'Daily'
  if (whole >= 1 && Math.abs(perWeek - whole) < 0.05) return `${whole}× a week`
  const days = 7 / perWeek
  return `every ${days >= 10 ? Math.round(days) : +days.toFixed(1)} days`
}
</script>
<template>
  <div class="upkeep">
    <div class="d-flex align-center justify-space-between mb-1">
      <span class="text-body-2 text-medium-emphasis">Upkeep {{ periodLabel }}</span>
      <v-chip
        v-if="status"
        :color="status.color"
        :prepend-icon="status.icon"
        size="small"
        variant="tonal"
      >
        {{ status.label }}
      </v-chip>
    </div>

    <template v-if="current.ratio !== null">
      <div class="d-flex align-baseline ga-2">
        <span class="text-h4 font-weight-bold">{{ percent(current.ratio) }}</span>
        <span class="text-body-2 text-medium-emphasis">
          {{ current.points }} of {{ round(current.ideal) }} points
        </span>
      </div>
      <div
        class="meter mt-2"
        :class="`meter--${status?.color}`"
        role="meter"
        :aria-valuenow="round(current.ratio * 100)"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`Upkeep ${periodLabel}`"
      >
        <span
          class="meter__fill"
          :style="{ width: `${Math.min(100, current.ratio * 100)}%` }"
        ></span>
      </div>

      <div class="text-body-2 text-medium-emphasis mt-4 mb-1">Last {{ weeks.length }} weeks</div>
      <div class="weeks">
        <svg
          :width="chartWidth"
          :height="CHART_HEIGHT + 4"
          role="img"
          :aria-label="`Weekly upkeep: ${weeks.map((w) => `${w.label} ${percent(w.ratio)}`).join(', ')}`"
          class="weeks__svg"
        >
          <line :x1="0" :x2="chartWidth" :y1="idealY" :y2="idealY" class="weeks__ideal" />
          <g
            v-for="(week, i) in weeks"
            :key="i"
            tabindex="0"
            class="weeks__bar"
            @pointerenter="hovered = i"
            @pointerleave="hovered = null"
            @focus="hovered = i"
            @blur="hovered = null"
          >
            <!-- Hit area bigger than the bar -->
            <rect
              :x="i * (BAR_WIDTH + 12)"
              y="0"
              :width="BAR_WIDTH + 12"
              :height="CHART_HEIGHT"
              fill="transparent"
            />
            <path
              v-if="week.ratio > 0"
              :d="`M${i * (BAR_WIDTH + 12) + 6},${CHART_HEIGHT}
                   v-${barHeight(week.ratio) - 4}
                   q0,-4 4,-4 h${BAR_WIDTH - 8} q4,0 4,4
                   v${barHeight(week.ratio) - 4} z`"
              class="weeks__fill"
              :class="{
                'weeks__fill--hover': hovered === i,
                'weeks__fill--current': i === weeks.length - 1
              }"
            />
          </g>
        </svg>
        <span class="weeks__ideal-label text-caption" :style="{ top: `${idealY - 8}px` }"
          >ideal</span
        >
      </div>
      <div
        class="d-flex justify-space-between text-caption text-medium-emphasis"
        :style="{ width: `${chartWidth}px` }"
      >
        <span>{{ weeks[0]?.short }}</span>
        <span>{{ weeks[weeks.length - 1]?.short }}</span>
      </div>
      <div class="text-caption mt-1 weeks__readout" aria-live="polite">
        <template v-if="hovered !== null">
          <strong>{{ percent(weeks[hovered].ratio) }}</strong>
          <span class="text-medium-emphasis">
            · {{ weeks[hovered].points }} of {{ round(upkeep.ideal_per_week) }} points ·
            {{ weeks[hovered].label }}
          </span>
        </template>
        <span v-else class="text-medium-emphasis">Tap a week for its numbers.</span>
      </div>

      <div class="d-flex flex-wrap ga-1 mt-1">
        <v-btn size="small" variant="text" class="px-1" @click="showBreakdown = !showBreakdown">
          {{ showBreakdown ? 'Hide' : 'How is the ideal worked out?' }}
        </v-btn>
        <v-btn
          size="small"
          variant="text"
          class="px-1"
          :prepend-icon="showTable ? 'mdi-chart-bar' : 'mdi-table'"
          @click="showTable = !showTable"
        >
          {{ showTable ? 'Hide table' : 'Weeks as table' }}
        </v-btn>
      </div>

      <div v-if="showBreakdown" class="text-body-2 mt-2">
        <p class="text-medium-emphasis mb-2">
          Every job done on schedule, at its usual points, earns
          <strong>{{ round(upkeep.ideal_per_week) }}</strong> points a week. Overdue bonuses aren't
          counted on either side.
        </p>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Job</th>
              <th>How often</th>
              <th class="text-right">Points</th>
              <th class="text-right">A week</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in upkeep.jobs" :key="job.id">
              <td>{{ job.name }}</td>
              <td>{{ howOften(job.per_week) }}</td>
              <td class="text-right">{{ job.value }}</td>
              <td class="text-right">{{ +job.points_per_week.toFixed(1) }}</td>
            </tr>
          </tbody>
        </v-table>
      </div>

      <v-table v-if="showTable" density="compact" class="mt-2">
        <thead>
          <tr>
            <th>Week</th>
            <th class="text-right">Points</th>
            <th class="text-right">Of ideal</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(week, i) in [...weeks].reverse()" :key="i">
            <td>{{ week.label }}</td>
            <td class="text-right">{{ week.points }} / {{ round(upkeep.ideal_per_week) }}</td>
            <td class="text-right">{{ percent(week.ratio) }}</td>
          </tr>
        </tbody>
      </v-table>
    </template>
    <p v-else class="text-body-2 text-medium-emphasis">
      No scheduled jobs yet, so there's nothing to keep up with.
    </p>
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
.weeks {
  position: relative;
  display: inline-block;
}
.weeks__svg {
  display: block;
  overflow: visible;
}
.weeks__ideal {
  stroke: rgba(var(--v-theme-on-surface), 0.45);
  stroke-width: 1;
}
.weeks__ideal-label {
  position: absolute;
  left: 100%;
  margin-left: 6px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.weeks__fill {
  fill: rgba(var(--v-theme-primary), 0.55);
}
.weeks__fill--current {
  fill: rgb(var(--v-theme-primary));
}
.weeks__fill--hover {
  fill: rgb(var(--v-theme-primary));
  filter: brightness(1.15);
}
.weeks__bar {
  outline: none;
  cursor: default;
}
.weeks__bar:focus-visible .weeks__fill {
  stroke: rgb(var(--v-theme-on-surface));
  stroke-width: 2;
}
.weeks__readout {
  min-height: 1.25rem;
}
</style>
