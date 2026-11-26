<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  addDays,
  addMonths,
  endOfMonth,
  endOfWeek,
  format,
  isSameMonth,
  startOfMonth,
  startOfWeek
} from 'date-fns'
import { todayString, type HolidayGroup } from './holidays'

// A month at a time, with your holidays shaded across their days. Emits the
// day tapped; the parent decides whether that opens a holiday or starts a
// new one. `selection` highlights a range being picked.
const { groups, selection } = defineProps<{
  groups: HolidayGroup[]
  selection: { from: string; to?: string } | null
}>()
const emit = defineEmits<{ pick: [day: string] }>()

const month = ref(startOfMonth(new Date()))
const today = todayString()
const WEEK = { weekStartsOn: 1 as const }

const weekdays = computed(() => {
  const start = startOfWeek(new Date(), WEEK)
  return [...Array(7)].map((_, i) => format(addDays(start, i), 'EEEEE'))
})

const days = computed(() => {
  const start = startOfWeek(startOfMonth(month.value), WEEK)
  const end = endOfWeek(endOfMonth(month.value), WEEK)
  const out: Date[] = []
  for (let d = start; d <= end; d = addDays(d, 1)) out.push(d)
  return out
})

function holidayOn(day: string) {
  return groups.find((g) => g.from <= day && g.to >= day) ?? null
}

function inSelection(day: string) {
  if (!selection) return false
  const to = selection.to ?? selection.from
  const [a, b] = selection.from <= to ? [selection.from, to] : [to, selection.from]
  return day >= a && day <= b
}

const cells = computed(() =>
  days.value.map((date, index) => {
    const day = format(date, 'yyyy-MM-dd')
    const holiday = holidayOn(day)
    const weekday = index % 7
    const selected = inSelection(day)
    // A band's ends are rounded at the holiday's (or selection's) first and
    // last day, and at the edges of each week row.
    const prev = format(addDays(date, -1), 'yyyy-MM-dd')
    const next = format(addDays(date, 1), 'yyyy-MM-dd')
    const band = holiday ? 'holiday' : selected ? 'selection' : null
    const sameBand = (d: string) =>
      band === 'holiday'
        ? holidayOn(d)?.key === holiday?.key
        : band === 'selection' && inSelection(d)
    return {
      day,
      date,
      label: format(date, 'd'),
      outside: !isSameMonth(date, month.value),
      past: day < today,
      today: day === today,
      holiday,
      selected,
      band,
      start: band !== null && (weekday === 0 || !sameBand(prev)),
      end: band !== null && (weekday === 6 || !sameBand(next)),
      aria: `${format(date, 'EEEE d MMMM')}${day === today ? ', today' : ''}${
        holiday ? `, on holiday${holiday.note ? `: ${holiday.note}` : ''}` : ''
      }${selected ? ', selected' : ''}`
    }
  })
)
</script>
<template>
  <div class="calendar">
    <div class="d-flex align-center mb-2">
      <v-btn
        icon="mdi-chevron-left"
        variant="text"
        size="small"
        aria-label="Previous month"
        @click="month = addMonths(month, -1)"
      />
      <div class="flex-grow-1 text-center text-title-medium font-weight-medium" aria-live="polite">
        {{ format(month, 'MMMM yyyy') }}
      </div>
      <v-btn
        icon="mdi-chevron-right"
        variant="text"
        size="small"
        aria-label="Next month"
        @click="month = addMonths(month, 1)"
      />
    </div>
    <div class="calendar__grid">
      <div v-for="(w, i) in weekdays" :key="`wd-${i}`" class="calendar__weekday" aria-hidden="true">
        {{ w }}
      </div>
      <button
        v-for="cell in cells"
        :key="cell.day"
        type="button"
        class="calendar__day"
        :class="{
          'calendar__day--outside': cell.outside,
          'calendar__day--past': cell.past,
          'calendar__day--today': cell.today,
          [`calendar__day--${cell.band}`]: cell.band,
          'calendar__day--start': cell.start,
          'calendar__day--end': cell.end
        }"
        :aria-label="cell.aria"
        :aria-pressed="cell.selected"
        @click="emit('pick', cell.day)"
      >
        <span class="calendar__number">{{ cell.label }}</span>
      </button>
    </div>
    <div class="d-flex justify-center mt-1">
      <v-btn
        v-if="!isSameMonth(month, new Date())"
        size="small"
        variant="text"
        @click="month = startOfMonth(new Date())"
      >
        Back to today
      </v-btn>
    </div>
  </div>
</template>
<style scoped>
.calendar__grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  row-gap: 4px;
}
.calendar__weekday {
  text-align: center;
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  padding-bottom: 4px;
}
.calendar__day {
  position: relative;
  height: 40px;
  border: 0;
  background: transparent;
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  font: inherit;
  font-size: 0.875rem;
  cursor: pointer;
}
.calendar__day:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
  border-radius: 8px;
}
.calendar__number {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
}
.calendar__day--outside {
  color: rgba(var(--v-theme-on-surface), 0.3);
}
.calendar__day--past:not(.calendar__day--holiday) {
  color: rgba(var(--v-theme-on-surface), 0.38);
}
.calendar__day--today .calendar__number {
  box-shadow: inset 0 0 0 2px rgb(var(--v-theme-primary));
  font-weight: 700;
}
/* The band: one continuous strip across a holiday's days. */
.calendar__day--holiday::before,
.calendar__day--selection::before {
  content: '';
  position: absolute;
  inset: 4px 0;
}
.calendar__day--holiday::before {
  background: rgba(var(--v-theme-primary), 0.3);
}
.calendar__day--holiday {
  font-weight: 600;
}
.calendar__day--selection::before {
  background: rgba(var(--v-theme-secondary), 0.45);
}
.calendar__day--start::before {
  left: 4px;
  border-top-left-radius: 16px;
  border-bottom-left-radius: 16px;
}
.calendar__day--end::before {
  right: 4px;
  border-top-right-radius: 16px;
  border-bottom-right-radius: 16px;
}
.calendar__day--past.calendar__day--holiday::before {
  background: rgba(var(--v-theme-primary), 0.15);
}
</style>
