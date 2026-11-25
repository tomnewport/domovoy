<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import AuthLayout from './AuthLayout.vue'
import Login from './Login.vue'
import SendEmailLink from './SendEmailLink.vue'

const sessionStore = useSessionStore()
const route = useRoute()

// `/?login=email` opens on the email-link tab (used by the link-error page).
const loginMode = ref<'password' | 'email'>(route.query.login === 'email' ? 'email' : 'password')
</script>
<template>
  <!-- A stored key is being checked and nothing is cached: brief splash, not a login form. -->
  <AuthLayout v-if="sessionStore.checking" compact>
    <div class="d-flex flex-column align-center pa-8" role="status">
      <v-progress-circular indeterminate color="primary" size="40" />
      <div class="text-body-2 text-medium-emphasis mt-4">Opening your homes…</div>
    </div>
  </AuthLayout>

  <AuthLayout v-else-if="!sessionStore.loggedIn">
    <v-tabs v-model="loginMode" grow color="primary">
      <v-tab value="password" prepend-icon="mdi-lock-outline">Password</v-tab>
      <v-tab value="email" prepend-icon="mdi-email-fast-outline">Email link</v-tab>
    </v-tabs>
    <v-card-text class="pa-6">
      <v-window v-model="loginMode">
        <v-window-item value="password"><Login /></v-window-item>
        <v-window-item value="email"><SendEmailLink /></v-window-item>
      </v-window>
    </v-card-text>
    <template #below>
      <div class="text-center text-body-2">
        New to Domovoy?
        <v-btn to="/register" variant="text" color="primary" class="px-2">Create an account</v-btn>
      </div>
    </template>
  </AuthLayout>

  <slot v-else></slot>
</template>
