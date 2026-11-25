<script setup lang="ts">
import { ref } from 'vue'
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
const busy = ref(false)

async function logout() {
  busy.value = true
  try {
    await sessionStore.clearSession()
  } finally {
    // A full reload drops every store's in-memory data along with the session.
    window.location.assign('/')
  }
}
</script>
<template>
  <v-btn variant="text" prepend-icon="mdi-logout" :loading="busy" v-on:click="logout">
    Log out
  </v-btn>
</template>
