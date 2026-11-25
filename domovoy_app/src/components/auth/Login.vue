<script setup lang="ts">
import type { VForm } from 'vuetify/components'
import { ref } from 'vue'
import API from '@/services/domovoy'
import { useSessionStore } from '@/stores/session'
import { toast } from 'vue-sonner'
import { emailRules, required } from './rules'
const sessionStore = useSessionStore()

const username = ref<string>('')
const password = ref<string>('')
const showPassword = ref<boolean>(false)
const form = ref<VForm | null>(null)
const loading = ref<boolean>(false)
const error = ref<string | null>(null)

async function login() {
  if (loading.value) return
  // Validate on submit (showing what's missing) rather than greying out the button.
  const { valid } = (await form.value?.validate()) ?? { valid: false }
  if (!valid) return
  loading.value = true
  error.value = null
  try {
    const loginResponse = await API.usersV1.postSession({
      email: username.value,
      factors: [
        {
          factor_type: 'password',
          password: password.value
        }
      ]
    })
    if (!loginResponse.response.ok) {
      error.value = 'That email and password didn’t work. Check them, or log in with an email link.'
      return
    }
    await sessionStore.setSessionId(loginResponse.data)
    toast.success(`Welcome back, ${sessionStore.session?.name_short ?? 'friend'}`)
  } catch {
    error.value = 'Could not reach Domovoy. Check your connection and try again.'
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <v-form @submit.prevent="login" ref="form">
    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-4"
      :text="error"
    />
    <v-text-field
      v-model="username"
      label="Email"
      type="email"
      autocomplete="username"
      inputmode="email"
      prepend-inner-icon="mdi-email-outline"
      variant="outlined"
      :rules="emailRules"
      required
    />
    <v-text-field
      v-model="password"
      label="Password"
      :type="showPassword ? 'text' : 'password'"
      autocomplete="current-password"
      prepend-inner-icon="mdi-lock-outline"
      variant="outlined"
      :rules="[required]"
      required
    >
      <template #append-inner>
        <v-btn
          :icon="showPassword ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
          :aria-label="showPassword ? 'Hide password' : 'Show password'"
          variant="text"
          size="small"
          density="comfortable"
          v-on:click="showPassword = !showPassword"
        />
      </template>
    </v-text-field>
    <v-btn :loading="loading" type="submit" class="mt-2" color="primary" size="large" block>
      Log in
    </v-btn>
  </v-form>
</template>
