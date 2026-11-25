<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthWall from '@/components/auth/AuthWall.vue'
import ActivityFeed from '@/components/activity/ActivityFeed.vue'
import HomeOverview from '@/components/homes/HomeOverview.vue'
import HomeSettings from '@/components/homes/HomeSettings.vue'
import { useHomesStore } from '@/stores/homes'
import { useRegularJobStore } from '@/stores/regular-job'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const homesStore = useHomesStore()
const regularJobStore = useRegularJobStore()
const sessionStore = useSessionStore()

// Reactive, so a cached home shows at once and updates when the list refreshes.
const home = computed(() =>
  homesStore.homes?.find((home) => home.id?.toString() === route.params.homeId)
)
const me = computed(() => sessionStore.session?.id ?? null)

type Tab = 'overview' | 'activity' | 'settings'
const TABS: Tab[] = ['overview', 'activity', 'settings']
const tab = ref<Tab>(TABS.includes(route.query.tab as Tab) ? (route.query.tab as Tab) : 'overview')
watch(tab, (value) => router.replace({ query: { ...route.query, tab: value } }))

onMounted(() => {
  homesStore.ensureLoaded()
  // Overdue jobs (overview) and the job count (settings) come from the job list.
  if (!regularJobStore.fresh) regularJobStore.reload()
})
</script>
<template>
  <AuthWall>
    <v-toolbar color="secondary" app>
      <v-btn icon to="/homes" aria-label="Back to homes">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <v-toolbar-title v-if="home">{{ home.name }}</v-toolbar-title>
      <v-toolbar-title v-else-if="homesStore.initialized">Home not found</v-toolbar-title>
      <v-toolbar-title v-else><span class="dmv-placeholder"></span></v-toolbar-title>
      <template v-if="home" #extension>
        <v-tabs v-model="tab" grow>
          <v-tab value="overview">Overview</v-tab>
          <v-tab value="activity">Activity</v-tab>
          <v-tab value="settings">Settings</v-tab>
        </v-tabs>
      </template>
    </v-toolbar>

    <v-container class="home-page pb-16">
      <v-window v-if="home" v-model="tab" :touch="false">
        <v-window-item value="overview">
          <HomeOverview :home-id="home.id as number" :home-name="home.name" />
        </v-window-item>
        <v-window-item value="activity">
          <ActivityFeed v-if="me" :current-user-id="me" :home-id="home.id as number" />
        </v-window-item>
        <v-window-item value="settings">
          <HomeSettings :home="home" :current-user-id="me" />
        </v-window-item>
      </v-window>
      <v-skeleton-loader
        v-else-if="!homesStore.initialized"
        type="heading, text, image"
        color="transparent"
        aria-hidden="true"
      />
      <div v-else class="d-flex flex-column align-center text-center pa-8 text-medium-emphasis">
        <v-icon size="48" class="mb-3">mdi-home-off-outline</v-icon>
        <div class="text-subtitle-1">This home isn't one of yours</div>
        <v-btn to="/homes" variant="text" class="mt-2">Back to homes</v-btn>
      </div>
    </v-container>
  </AuthWall>
</template>
<style scoped>
.home-page {
  max-width: 760px;
}
</style>
