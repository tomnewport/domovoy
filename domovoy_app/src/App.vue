<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

import { Toaster } from 'vue-sonner'
import BottomMenu from '@/components/layout/BottomMenu.vue'

import { useHashcashConfigStore } from '@/stores/hashcash-config'
import { useSessionStore } from '@/stores/session'

const hashcashConfigStore = useHashcashConfigStore()
const sessionStore = useSessionStore()

let intervals: number[] = []

onMounted(() => {
  // Things to do when the app loads
  hashcashConfigStore.load()
  sessionStore.reloadSession()
  intervals.push(setInterval(hashcashConfigStore.load, 4 * 60 * 60 * 1000))
  intervals.push(setInterval(sessionStore.reloadSession, 5 * 60 * 1000))
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
    <v-main>
      <RouterView />
    </v-main>
    <v-footer app class="pa-0">
      <BottomMenu />
    </v-footer>
  </v-app>
</template>

<style scoped></style>
