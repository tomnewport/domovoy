<script setup lang="ts">
import { computed, ref, Fragment } from 'vue'
import { useSessionStore } from '@/stores/session'
import Login from '@/components/auth/Login.vue'
import SendEmailLink from './SendEmailLink.vue'
const sessionStore = useSessionStore()

const loginMode = ref<'email' | 'password'>('password')

const loginRequired = computed(() => {
  const sessionExpires = new Date(sessionStore.session?.session_expires || 0)
  const now = new Date()
  const oneHourFromNow = new Date(now.getTime() + 60 * 60 * 1000)
  return sessionExpires < oneHourFromNow
})
</script>
<template>
  <template v-if="loginRequired">
    <v-container class="fill-height d-flex align-center justify-center" fluid>
      <v-card class="pa-5" max-width="400">
        <v-card-title class="text-h5">Please log in</v-card-title>
        <v-card-subtitle
          >Or <RouterLink to="/register">click here</RouterLink> to create a new
          account.</v-card-subtitle
        >
        <Login v-if="loginMode === 'password'" />
        <a href="#" v-if="loginMode === 'password'" v-on:click="loginMode = 'email'"
          >Log in with a link</a
        >

        <SendEmailLink v-if="loginMode === 'email'" />
        <a href="#" v-if="loginMode === 'email'" v-on:click="loginMode = 'password'"
          >Log in with your password</a
        >
      </v-card>
    </v-container>
  </template>
  <template v-else>
    <slot></slot>
  </template>
</template>
