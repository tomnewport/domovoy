<script setup lang="ts">
import { computed, ref } from 'vue'
import API from '@/services/domovoy'
import { useSessionStore } from '@/stores/session'
import { toast } from 'vue-sonner'
const sessionStore = useSessionStore()

const username = ref<string>('')
const password = ref<string>('')
const valid = ref<boolean>(false)
const loading = ref<boolean>(false)

const rules = {
  required: (value: string) => !!value || 'This field is required',
  email: (value: string) => /.+@.+\..+/.test(value) || 'E-mail must be valid'
}

async function runLogin() {
  loading.value = true
  const loginResponse = await API.usersV1.postSession({
    email: username.value,
    factors: [
      {
        factor_type: 'password',
        password: password.value
      }
    ]
  })
  if (!loginResponse.response.ok) throw new Error('Email or password incorrect')
  await sessionStore.setSessionId(loginResponse.data)
  loading.value = false
}

function login() {
  toast.promise(runLogin(), {
    loading: 'Logging you in',
    success: () => {
      return `Welcome ${sessionStore.session?.name_short}`
    },
    error: (data: any) => data.toString()
  })
}
</script>
<template>
  <v-form @submit.prevent="login" v-model="valid">
    <v-text-field
      v-model="username"
      label="Email"
      variant="underlined"
      type="email"
      :rules="[rules.required, rules.email]"
      required
    />
    <v-text-field
      v-model="password"
      label="Password"
      type="password"
      variant="underlined"
      :rules="[rules.required]"
      required
    />
    <v-btn :disabled="!valid" type="submit" class="mt-3" color="primary" block> Log in </v-btn>
  </v-form>
</template>
