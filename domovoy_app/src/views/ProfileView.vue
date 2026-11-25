<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { startOfDay, subDays } from 'date-fns'
import AuthWall from '@/components/auth/AuthWall.vue'
import Logout from '@/components/auth/Logout.vue'
import ProgressTiles from '@/components/profile/ProgressTiles.vue'
import HomeContributions from '@/components/profile/HomeContributions.vue'
import TopJobs from '@/components/profile/TopJobs.vue'
import ActivityFeed from '@/components/activity/ActivityFeed.vue'
import HolidayPlanner from '@/components/profile/HolidayPlanner.vue'
import { useSessionStore } from '@/stores/session'
import { useHomesStore } from '@/stores/homes'
import {
  fetchAllCompletions,
  fetchStatistics,
  type HomeStatistics,
  type JobCompletion
} from '@/services/domovoy/stats'
import { completionsByPeriod, currentStreak, pointsByPeriod, type Period } from '@/utils/progress'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const homesStore = useHomesStore()

type Tab = 'progress' | 'activity' | 'holidays'
const TABS: Tab[] = ['progress', 'activity', 'holidays']
const tab = ref<Tab>(TABS.includes(route.query.tab as Tab) ? (route.query.tab as Tab) : 'progress')
watch(tab, (value) => router.replace({ query: { ...route.query, tab: value } }))

const period = ref<Period>(7)
const me = computed(() => sessionStore.session?.id ?? null)

// Your own numbers: each home's statistics (for your points and share) and
// your completions, both over two periods so this one can be compared with
// the one before. How each home is doing is on the home's page.
const stats = ref<{ homeId: number; stats: HomeStatistics }[] | null>(null)
const mine = ref<JobCompletion[] | null>(null)
const loadError = ref<string | null>(null)

async function loadOverview() {
  if (!me.value) return
  loadError.value = null
  stats.value = null
  mine.value = null
  try {
    await homesStore.ensureLoaded()
    const homes = homesStore.homes ?? []
    const since = subDays(startOfDay(new Date()), period.value * 2 - 1)
    const [homeStats, completions] = await Promise.all([
      Promise.all(
        homes.map(async (home) => ({
          homeId: home.id as number,
          stats: await fetchStatistics(home.id as number, period.value * 2)
        }))
      ),
      fetchAllCompletions({ userId: me.value, since })
    ])
    stats.value = homeStats
    mine.value = completions
  } catch {
    loadError.value = 'Could not load your progress.'
  }
}

onMounted(loadOverview)
watch([period, me], loadOverview)

const points = computed(() =>
  stats.value && me.value
    ? pointsByPeriod(
        stats.value.map((s) => s.stats),
        me.value,
        period.value
      )
    : null
)
const totals = computed(() => (mine.value ? completionsByPeriod(mine.value, period.value) : null))
const streak = computed(() => (mine.value ? currentStreak(mine.value) : 0))
// Only worth naming a job's home when you're in more than one.
const homeLabel = (id: number) =>
  (homesStore.homes?.length ?? 0) > 1
    ? (homesStore.homes?.find((h) => h.id === id)?.name ?? '')
    : ''
const contributions = computed(() =>
  (stats.value ?? []).flatMap((entry) => {
    const home = homesStore.homes?.find((h) => h.id === entry.homeId)
    return home ? [{ home, stats: entry.stats }] : []
  })
)
</script>
<template>
  <AuthWall>
    <v-toolbar color="secondary" title="Profile" app>
      <v-spacer></v-spacer>
      <Logout />
      <template #extension>
        <v-tabs v-model="tab" grow>
          <v-tab value="progress">Progress</v-tab>
          <v-tab value="activity">Activity</v-tab>
          <v-tab value="holidays">Holidays</v-tab>
        </v-tabs>
      </template>
    </v-toolbar>

    <v-container class="profile pb-16">
      <v-window v-model="tab" :touch="false">
        <v-window-item value="progress">
          <div class="d-flex align-center justify-space-between mb-3">
            <div>
              <div class="text-h6">{{ sessionStore.session?.name_short }}</div>
              <div class="text-body-2 text-medium-emphasis">Your progress</div>
            </div>
            <v-btn-toggle v-model="period" mandatory density="compact" variant="outlined" divided>
              <v-btn :value="7">7 days</v-btn>
              <v-btn :value="30">30 days</v-btn>
            </v-btn-toggle>
          </div>

          <v-alert v-if="loadError" type="error" variant="tonal" class="mb-4">
            {{ loadError }}
            <template #append>
              <v-btn variant="text" @click="loadOverview">Retry</v-btn>
            </template>
          </v-alert>

          <template v-else-if="!points || !totals">
            <div class="skeleton-tiles mb-4" aria-hidden="true">
              <v-skeleton-loader v-for="n in 4" :key="n" type="heading, text" />
            </div>
            <v-skeleton-loader type="heading, list-item, list-item, image" aria-hidden="true" />
          </template>

          <template v-else>
            <ProgressTiles
              :period="period"
              :points="points"
              :totals="totals"
              :streak="streak"
              class="mb-4"
            />
            <HomeContributions
              v-if="contributions.length && me"
              :entries="contributions"
              :period="period"
              :user-id="me"
              class="mb-4"
            />
            <div v-else class="text-center pa-6 text-medium-emphasis text-body-2">
              Join or create a home to see your share of the housework.
            </div>
            <TopJobs :completions="mine ?? []" :period="period" :home-label="homeLabel" />
          </template>
        </v-window-item>

        <v-window-item value="activity">
          <ActivityFeed v-if="me" :current-user-id="me" :user-id="me" />
        </v-window-item>

        <v-window-item value="holidays">
          <HolidayPlanner />
        </v-window-item>
      </v-window>
    </v-container>
  </AuthWall>
</template>
<style scoped>
.profile {
  max-width: 760px;
}
.skeleton-tiles {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
</style>
