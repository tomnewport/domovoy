<script setup lang="ts">
import AuthLayout from '@/components/auth/AuthLayout.vue'
</script>
<template>
  <AuthLayout compact>
    <div class="d-flex flex-column align-center text-center pa-6">
      <v-icon icon="mdi-link-variant-off" size="56" color="warning" class="mb-3" />
      <h2 class="text-h6">That link didn’t work</h2>
      <p class="text-body-2 text-medium-emphasis mt-2">
        Login links work once and expire after 30 minutes. If you asked for more than one, only the
        newest works.
      </p>
      <v-btn
        to="/?login=email"
        color="primary"
        size="large"
        block
        class="mt-5"
        prepend-icon="mdi-email-fast-outline"
      >
        Email me a new link
      </v-btn>
      <v-btn to="/" variant="text" block class="mt-2">Log in with a password</v-btn>
    </div>
  </AuthLayout>
</template>
