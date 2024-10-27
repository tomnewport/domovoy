<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
function logout() {
  sessionStore.clearSession()
}
</script>
<template>
  <button v-on:click="logout">Logout</button>
</template>
