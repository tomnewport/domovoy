<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import { useRoute, useRouter } from 'vue-router'
import API from '@/services/domovoy'
import { onMounted } from 'vue'
import AuthLayout from '@/components/auth/AuthLayout.vue'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
onMounted(async () => {
  try {
    const email = atob(route.params.emailB64.toString())
    const emailCode = route.params.emailCode.toString()
    const result = await API.usersV1.postSession({
      email,
      factors: [{ factor_type: 'email_code', email_code: emailCode }]
    })
    if (!result.response.ok) {
      throw new Error('Link failed')
    }
    await sessionStore.setSessionId(result.data)
    router.replace({ path: '/' })
  } catch (err) {
    console.error(err)
    router.replace({ path: '/auth_link/error' })
  }
})
</script>
<template>
  <AuthLayout compact>
    <div class="d-flex flex-column align-center text-center pa-8" role="status">
      <v-progress-circular indeterminate color="primary" size="40" />
      <h2 class="text-title-large mt-5">Logging you in…</h2>
      <p class="text-body-medium text-medium-emphasis mt-1">Checking your link.</p>
    </div>
  </AuthLayout>
</template>
