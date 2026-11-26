<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { format, isToday, isYesterday } from 'date-fns'
import { useHomesStore } from '@/stores/homes'
import { fetchCompletions, type JobCompletion } from '@/services/domovoy/stats'
import { memberColors, textOn } from '@/utils/memberColors'

// Recent jobs done, newest first: one person's (`userId`, on Profile) or one
// home's (`homeId`), with chips to narrow a home's feed to one member.
const { currentUserId, userId, homeId } = defineProps<{
  currentUserId: number
  userId?: number
  homeId?: number
}>()
const homesStore = useHomesStore()

const PAGE = 30
// Narrows a home's feed to one member.
const member = ref<number | 'all'>('all')
const items = ref<JobCompletion[]>([])
const loading = ref(false)
const exhausted = ref(false)
const error = ref<string | null>(null)

const filterUser = computed(() => userId ?? (member.value === 'all' ? undefined : member.value))

// A later answer for an older filter mustn't overwrite the current one.
let requestId = 0

async function load(reset: boolean) {
  const id = ++requestId
  loading.value = true
  error.value = null
  try {
    const page = await fetchCompletions({
      homeId,
      userId: filterUser.value,
      before: reset ? undefined : items.value[items.value.length - 1]?.completed_at,
      limit: PAGE
    })
    if (id !== requestId) return
    items.value = reset ? page : [...items.value, ...page]
    exhausted.value = page.length < PAGE
  } catch {
    if (id === requestId) error.value = 'Could not load activity.'
  } finally {
    if (id === requestId) loading.value = false
  }
}

onMounted(() => {
  homesStore.ensureLoaded()
  load(true)
})
watch([filterUser, () => homeId], () => {
  items.value = []
  load(true)
})

const home = computed(() =>
  homeId === undefined ? undefined : homesStore.homes?.find((h) => h.id === homeId)
)
// Chips for each member, in colour order (by user id, as in the charts).
const memberChips = computed(() =>
  [...(home.value?.memberships ?? [])]
    .map((m) => ({
      id: m.user.id as number,
      name: m.user.id === currentUserId ? 'You' : (m.user.name_short ?? m.user.name_full)
    }))
    .sort((a, b) => a.id - b.id)
)

const people = computed(() => {
  const byId = new Map<number, { short: string; full: string }>()
  for (const each of homesStore.homes ?? []) {
    for (const m of each.memberships) {
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
      (homesStore.homes ?? []).map((each) => [
        each.id as number,
        memberColors(each.memberships.map((m) => m.user.id as number))
      ])
    )
)
const colorOf = (item: JobCompletion) =>
  colorsByHome.value.get(item.home_id)?.get(item.completed_by_id) ?? '#9c9c9c'
const homeName = (id: number) => homesStore.homes?.find((h) => h.id === id)?.name ?? ''
const showHome = computed(() => homeId === undefined && (homesStore.homes?.length ?? 0) > 1)
const who = (item: JobCompletion) =>
  item.completed_by_id === currentUserId
    ? 'You'
    : (people.value.get(item.completed_by_id)?.short ?? 'Someone')

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
    <v-chip-group
      v-if="homeId !== undefined && userId === undefined && memberChips.length > 1"
      v-model="member"
      mandatory
      selected-class="text-primary"
      class="mb-2"
      aria-label="Whose jobs to show"
    >
      <v-chip value="all" filter variant="outlined">Everyone</v-chip>
      <v-chip v-for="chip in memberChips" :key="chip.id" :value="chip.id" filter variant="outlined">
        <span
          class="member-dot mr-2"
          :style="{ background: colorsByHome.get(homeId)?.get(chip.id) }"
          aria-hidden="true"
        ></span>
        {{ chip.name }}
      </v-chip>
    </v-chip-group>

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
      <div class="text-title-medium">Nothing done yet</div>
      <div class="text-body-medium">
        {{ member !== 'all' ? 'Nothing from them yet.' : 'Completed jobs show up here.' }}
      </div>
    </div>

    <v-list v-else bg-color="transparent" class="pa-0">
      <template v-for="group in groups" :key="group.label">
        <v-list-subheader>{{ group.label }}</v-list-subheader>
        <v-list-item v-for="item in group.items" :key="item.id" class="px-1">
          <template #prepend>
            <!-- One person's feed: their initials on every row would say nothing. -->
            <v-avatar v-if="userId !== undefined" size="36" color="primary" variant="tonal">
              <v-icon icon="mdi-check" size="20" />
            </v-avatar>
            <v-avatar
              v-else
              size="36"
              :style="{
                background: colorOf(item),
                color: textOn(colorOf(item))
              }"
              class="text-body-small font-weight-bold"
            >
              {{ initials(people.get(item.completed_by_id)?.full ?? '?') }}
            </v-avatar>
          </template>
          <v-list-item-title class="text-wrap">
            <template v-if="userId !== undefined">{{ item.job_name }}</template>
            <template v-else>
              <span :class="{ 'font-weight-bold': item.completed_by_id === currentUserId }">
                {{ who(item) }}
              </span>
              did {{ item.job_name }}
            </template>
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ format(new Date(item.completed_at), 'HH:mm') }}
            <template v-if="showHome"> · {{ homeName(item.home_id) }}</template>
            <template v-if="item.on_time === false">
              · <v-icon icon="mdi-clock-alert-outline" size="14" /> late
            </template>
          </v-list-item-subtitle>
          <template #append>
            <span class="text-body-medium font-weight-medium">+{{ item.value }}</span>
          </template>
        </v-list-item>
      </template>
    </v-list>

    <div v-if="items.length && !exhausted" class="d-flex justify-center mt-2">
      <v-btn variant="text" :loading="loading" @click="load(false)">Load more</v-btn>
    </div>
  </div>
</template>
<style scoped>
.member-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
</style>
