<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

import { Toaster } from 'vue-sonner'
import BottomMenu from '@/components/layout/BottomMenu.vue'
import NetworkActivityBar from '@/components/layout/NetworkActivityBar.vue'

import { useHashcashConfigStore } from '@/stores/hashcash-config'
import { useSessionStore } from '@/stores/session'
import { useHomesStore } from '@/stores/homes'
import { useRegularJobStore } from './stores/regular-job'

const hashcashConfigStore = useHashcashConfigStore()
const sessionStore = useSessionStore()
const homesStore = useHomesStore()
const regularJobStore = useRegularJobStore()
const route = useRoute()

const showBottomMenu = computed(() => sessionStore.loggedIn && route.meta.bottomNav !== false)

let intervals: number[] = []

// Route views are separate chunks; fetch them once the first screen is up so
// the first tap on another tab doesn't wait for a download.
function prefetchViews() {
  const load = () => {
    import('@/views/HomesView.vue')
    import('@/views/HomeDetailView.vue')
    import('@/views/HomeJobsView.vue')
    import('@/views/ProfileView.vue')
  }
  if ('requestIdleCallback' in window) window.requestIdleCallback(load, { timeout: 3000 })
  else setTimeout(load, 1500)
}

onMounted(() => {
  // Ask for everything the first screen needs at once rather than one after
  // another: the session check, the tasks and the homes (names for users and
  // homes) go out together. With no stored key, only the session state and
  // the hashcash config (needed to log in) are loaded.
  hashcashConfigStore.load()
  sessionStore.reloadSession()
  if (sessionStore.sessionId) {
    regularJobStore.reload()
    homesStore.reloadHomes()
  }
  prefetchViews()
  intervals.push(setInterval(hashcashConfigStore.load, 4 * 60 * 60 * 1000))
  intervals.push(setInterval(sessionStore.reloadSession, 5 * 60 * 1000))
  intervals.push(setInterval(regularJobStore.reload, 5 * 60 * 1000))
})

onBeforeUnmount(() => {
  intervals.forEach((ptr) => {
    clearInterval(ptr)
  })
})
</script>

<template>
  <Toaster position="top-center" closeButton richColors />
  <v-app>
    <NetworkActivityBar />
    <v-main>
      <RouterView />
    </v-main>
    <v-footer v-if="showBottomMenu" app class="pa-0">
      <BottomMenu />
    </v-footer>
  </v-app>
</template>

<style scoped></style>
