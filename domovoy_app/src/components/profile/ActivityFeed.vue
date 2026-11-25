<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { format, isToday, isYesterday } from 'date-fns'
import { useHomesStore } from '@/stores/homes'
import { fetchCompletions, type JobCompletion } from '@/services/domovoy/stats'
import { memberColors, textOn } from '@/utils/memberColors'

// Recent jobs done across your homes: everyone's, or just yours.
const { userId } = defineProps<{ userId: number }>()
const homesStore = useHomesStore()

const PAGE = 30
const who = ref<'everyone' | 'you'>('everyone')
const items = ref<JobCompletion[]>([])
const loading = ref(false)
const exhausted = ref(false)
const error = ref<string | null>(null)

async function load(reset: boolean) {
  loading.value = true
  error.value = null
  try {
    const page = await fetchCompletions({
      userId: who.value === 'you' ? userId : undefined,
      before: reset ? undefined : items.value[items.value.length - 1]?.completed_at,
      limit: PAGE
    })
    items.value = reset ? page : [...items.value, ...page]
    exhausted.value = page.length < PAGE
  } catch {
    error.value = 'Could not load activity.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  homesStore.ensureLoaded()
  load(true)
})
watch(who, () => {
  items.value = []
  load(true)
})

const people = computed(() => {
  const byId = new Map<number, { short: string; full: string }>()
  for (const home of homesStore.homes ?? []) {
    for (const m of home.memberships) {
      byId.set(m.user.id as number, {
        short: m.user.name_short ?? m.user.name_full,
        full: m.user.name_full
      })
    }
  }
  return byId
})
// Same colour per person as in the charts (ordered by user id within a home).
const colorsByHome = computed(
  () =>
    new Map(
      (homesStore.homes ?? []).map((home) => [
        home.id as number,
        memberColors(home.memberships.map((m) => m.user.id as number))
      ])
    )
)
const colorOf = (item: JobCompletion) =>
  colorsByHome.value.get(item.home_id)?.get(item.completed_by_id) ?? '#9c9c9c'
const homeName = (id: number) => homesStore.homes?.find((h) => h.id === id)?.name ?? ''
const showHome = computed(() => (homesStore.homes?.length ?? 0) > 1)

function dayLabel(date: Date) {
  if (isToday(date)) return 'Today'
  if (isYesterday(date)) return 'Yesterday'
  return format(date, 'EEEE d MMMM')
}

const groups = computed(() => {
  const out: { label: string; items: JobCompletion[] }[] = []
  for (const item of items.value) {
    const label = dayLabel(new Date(item.completed_at))
    const last = out[out.length - 1]
    if (last?.label === label) last.items.push(item)
    else out.push({ label, items: [item] })
  }
  return out
})

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
</script>
<template>
  <div>
    <v-btn-toggle
      v-model="who"
      mandatory
      density="comfortable"
      variant="outlined"
      divided
      class="mb-3"
    >
      <v-btn value="everyone">Everyone</v-btn>
      <v-btn value="you">Just me</v-btn>
    </v-btn-toggle>

    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-3"
      :text="error"
    />

    <template v-if="!items.length && loading">
      <v-skeleton-loader
        v-for="n in 5"
        :key="n"
        type="list-item-avatar-two-line"
        color="transparent"
        aria-hidden="true"
      />
    </template>
    <div
      v-else-if="!items.length && !error"
      class="d-flex flex-column align-center text-center pa-8 text-medium-emphasis"
    >
      <v-icon size="48" class="mb-3">mdi-history</v-icon>
      <div class="text-subtitle-1">Nothing done yet</div>
      <div class="text-body-2">Completed jobs show up here.</div>
    </div>

    <v-list v-else bg-color="transparent" class="pa-0">
      <template v-for="group in groups" :key="group.label">
        <v-list-subheader>{{ group.label }}</v-list-subheader>
        <v-list-item v-for="item in group.items" :key="item.id" class="px-1">
          <template #prepend>
            <v-avatar
              size="36"
              :style="{
                background: colorOf(item),
                color: textOn(colorOf(item))
              }"
              class="text-caption font-weight-bold"
            >
              {{ initials(people.get(item.completed_by_id)?.full ?? '?') }}
            </v-avatar>
          </template>
          <v-list-item-title class="text-wrap">
            <span :class="{ 'font-weight-bold': item.completed_by_id === userId }">
              {{
                item.completed_by_id === userId
                  ? 'You'
                  : (people.get(item.completed_by_id)?.short ?? 'Someone')
              }}
            </span>
            did {{ item.job_name }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ format(new Date(item.completed_at), 'HH:mm') }}
            <template v-if="showHome"> · {{ homeName(item.home_id) }}</template>
            <template v-if="item.on_time === false">
              · <v-icon icon="mdi-clock-alert-outline" size="14" /> late
            </template>
          </v-list-item-subtitle>
          <template #append>
            <span class="text-body-2 font-weight-medium">+{{ item.value }}</span>
          </template>
        </v-list-item>
      </template>
    </v-list>

    <div v-if="items.length && !exhausted" class="d-flex justify-center mt-2">
      <v-btn variant="text" :loading="loading" @click="load(false)">Load more</v-btn>
    </div>
  </div>
</template>
