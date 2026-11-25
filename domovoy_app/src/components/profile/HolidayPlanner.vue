<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { differenceInCalendarDays, format, parseISO } from 'date-fns'
import { useHomesStore } from '@/stores/homes'
import HolidayCalendar from './HolidayCalendar.vue'
import HolidayForm from './HolidayForm.vue'
import {
  describeRange,
  todayString,
  useHolidays,
  type HolidayDraft,
  type HolidayGroup
} from './holidays'

// Your holidays: where you stand today, a calendar to see and pick dates,
// and the list of upcoming and past ones.
const homesStore = useHomesStore()
const holidays = useHolidays()
const today = todayString()

onMounted(() => {
  homesStore.ensureLoaded()
  holidays.load()
})

const allHomeIds = computed(() => (homesStore.homes ?? []).map((h) => h.id as number))
const showHomes = computed(() => allHomeIds.value.length > 1)
const homeName = (id: number) => homesStore.homes?.find((h) => h.id === id)?.name ?? ''

// Picking a range on the calendar: first tap sets the start, second the end.
const selection = ref<{ from: string; to?: string } | null>(null)

const formOpen = ref(false)
const editing = ref<HolidayGroup | null>(null)
const initial = ref<HolidayDraft>({ from: today, to: today, note: '', homeIds: [] })

function openNew(from = today, to = from) {
  editing.value = null
  initial.value = { from, to, note: '', homeIds: allHomeIds.value }
  formOpen.value = true
}

function openExisting(group: HolidayGroup) {
  selection.value = null
  editing.value = group
  initial.value = { from: group.from, to: group.to, note: group.note, homeIds: [...group.homeIds] }
  formOpen.value = true
}

function onPick(day: string) {
  const existing = holidays.groups.value.find((g) => g.from <= day && g.to >= day)
  if (existing && !selection.value) return openExisting(existing)
  if (!selection.value) {
    if (day < today) return
    selection.value = { from: day }
    return
  }
  const [from, to] =
    day < selection.value.from ? [day, selection.value.from] : [selection.value.from, day]
  selection.value = { from, to }
  openNew(from, to)
}

function onFormToggle(open: boolean) {
  formOpen.value = open
  if (!open) selection.value = null
}

async function save(draft: HolidayDraft) {
  if (editing.value) await holidays.update(editing.value, draft)
  else await holidays.create(draft)
}

const status = computed(() => {
  const now = holidays.current.value
  if (now) {
    return {
      icon: 'mdi-palm-tree',
      title: `On holiday until ${format(parseISO(now.to), 'EEEE d MMMM')}`,
      detail: now.note || 'No jobs will be scheduled for you until then.'
    }
  }
  const next = holidays.upcoming.value[0]
  if (next) {
    const days = differenceInCalendarDays(parseISO(next.from), parseISO(today))
    return {
      icon: 'mdi-home-outline',
      title: "You're at home",
      detail: `Next holiday ${days === 1 ? 'tomorrow' : `in ${days} days`}: ${describeRange(next.from, next.to).text}`
    }
  }
  return { icon: 'mdi-home-outline', title: "You're at home", detail: 'No holidays planned.' }
})

const range = (g: HolidayGroup) => describeRange(g.from, g.to)
function when(g: HolidayGroup) {
  if (g.from <= today && g.to >= today) return 'Now'
  const days = differenceInCalendarDays(parseISO(g.from), parseISO(today))
  return days === 1 ? 'Tomorrow' : `In ${days} days`
}
</script>
<template>
  <div>
    <v-card variant="tonal" class="pa-4 mb-4">
      <template v-if="!holidays.loaded.value">
        <v-skeleton-loader
          type="list-item-avatar-two-line"
          color="transparent"
          aria-hidden="true"
        />
      </template>
      <div v-else class="d-flex align-center ga-3">
        <v-avatar color="primary" variant="tonal" size="44">
          <v-icon :icon="status.icon" />
        </v-avatar>
        <div>
          <div class="text-subtitle-1 font-weight-medium">{{ status.title }}</div>
          <div class="text-body-2 text-medium-emphasis">{{ status.detail }}</div>
        </div>
      </div>
    </v-card>

    <v-alert
      v-if="holidays.error.value"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-4"
      :text="holidays.error.value"
    />

    <v-card variant="tonal" class="pa-3 mb-2">
      <HolidayCalendar :groups="holidays.groups.value" :selection="selection" @pick="onPick" />
    </v-card>
    <div class="d-flex align-center justify-space-between mb-5 px-1">
      <span class="text-caption text-medium-emphasis">
        <template v-if="selection">Now tap the last day you're away.</template>
        <template v-else>Tap a day to start a holiday, or a shaded day to edit one.</template>
      </span>
      <v-btn v-if="selection" size="small" variant="text" @click="selection = null"> Cancel </v-btn>
      <v-btn
        v-else
        size="small"
        variant="tonal"
        color="primary"
        prepend-icon="mdi-plus"
        @click="openNew()"
      >
        Add
      </v-btn>
    </div>

    <div class="text-subtitle-2 mb-2">Upcoming</div>
    <template v-if="!holidays.loaded.value">
      <v-skeleton-loader
        v-for="n in 2"
        :key="n"
        type="list-item-two-line"
        color="transparent"
        aria-hidden="true"
      />
    </template>
    <div
      v-else-if="!holidays.upcoming.value.length"
      class="text-body-2 text-medium-emphasis mb-4 px-1"
    >
      Nothing planned. Add one so you aren't given jobs while you're away.
    </div>
    <v-list v-else bg-color="transparent" class="pa-0 mb-4">
      <v-list-item
        v-for="g in holidays.upcoming.value"
        :key="g.key"
        class="holiday px-3 mb-2"
        rounded="lg"
        @click="openExisting(g)"
      >
        <v-list-item-title class="font-weight-medium">{{ range(g).text }}</v-list-item-title>
        <v-list-item-subtitle>
          {{ range(g).days }} {{ range(g).days === 1 ? 'day' : 'days'
          }}<template v-if="g.note"> · {{ g.note }}</template>
        </v-list-item-subtitle>
        <div v-if="showHomes" class="d-flex flex-wrap ga-1 mt-1">
          <v-chip v-for="id in g.homeIds" :key="id" size="x-small" variant="outlined">{{
            homeName(id)
          }}</v-chip>
        </div>
        <template #append>
          <v-chip size="small" :color="when(g) === 'Now' ? 'primary' : undefined" variant="tonal">
            {{ when(g) }}
          </v-chip>
        </template>
      </v-list-item>
    </v-list>

    <v-expansion-panels v-if="holidays.past.value.length" variant="accordion" flat>
      <v-expansion-panel bg-color="transparent">
        <v-expansion-panel-title class="px-1 text-subtitle-2">
          Past holidays ({{ holidays.past.value.length }})
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list bg-color="transparent" class="pa-0" density="compact">
            <v-list-item
              v-for="g in holidays.past.value"
              :key="g.key"
              class="px-1"
              @click="openExisting(g)"
            >
              <v-list-item-title>{{ range(g).text }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ range(g).days }} {{ range(g).days === 1 ? 'day' : 'days'
                }}<template v-if="g.note"> · {{ g.note }}</template>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <HolidayForm
      :model-value="formOpen"
      :initial="initial"
      :group="editing"
      :save="save"
      :remove="holidays.remove"
      @update:model-value="onFormToggle"
    />
  </div>
</template>
<style scoped>
.holiday {
  background: rgba(var(--v-theme-on-surface), 0.05);
}
</style>
