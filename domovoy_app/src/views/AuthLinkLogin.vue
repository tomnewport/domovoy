<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import { routerKey, useRoute, useRouter } from 'vue-router'
import API from '@/services/domovoy'
import { onMounted } from 'vue'

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
    sessionStore.setSessionId(result.data)
    router.push({ path: '/' })
  } catch (err) {
    console.error(err)
    router.push({ path: '/auth_link/error' })
  }
})
</script>
<template>
  <v-container>
    <v-card>
      <v-card-title>Logging you in...</v-card-title>
      <v-card-item class="d-flex justify-center"
        ><v-progress-circular color="primary" indeterminate></v-progress-circular
      ></v-card-item>
      <v-card-text>Please wait while your link is checked.</v-card-text>
    </v-card>
  </v-container>
</template>
