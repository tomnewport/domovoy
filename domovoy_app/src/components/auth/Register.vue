<script setup lang="ts">
import { useHashcash } from '@/utils/hashcash'
import { ref } from 'vue'
import API from '@/services/domovoy'
import { toast } from 'vue-sonner'
const hashcash = useHashcash()

const email = ref('')
const password = ref('')
const shortName = ref('')
const fullName = ref('')
const valid = ref<boolean>(false)
const complete = ref<boolean>(false)

async function doRegister() {
  const hashcashHeader = await hashcash(email.value)
  const response = await API.usersV1.postNew(
    {
      email: email.value,
      username: email.value,
      password: password.value,
      name_short: shortName.value,
      name_full: fullName.value
    },
    hashcashHeader
  )
  if (!response.response.ok) throw new Error('There was an issue creating your user')
  complete.value = true
}

function register() {
  toast.promise(doRegister(), {
    loading: 'Creating your account',
    success: () => {
      return `Success! Please check your inbox`
    },
    error: (data: any) => data.toString()
  })
}

const rules = {
  required: (value: string) => !!value || 'This field is required',
  email: (value: string) => /.+@.+\..+/.test(value) || 'E-mail must be valid'
}
</script>
<template>
  <template v-if="!complete">
    <v-container class="fill-height d-flex align-center justify-center" fluid>
      <v-card class="pa-5" max-width="400">
        <v-card-title class="text-h5">Register a new account</v-card-title>
        <v-card-subtitle>Or <RouterLink to="/">click here</RouterLink> log in.</v-card-subtitle>
        <v-form @submit.prevent="register" v-model="valid">
          <v-text-field
            :rules="[rules.required, rules.email]"
            label="Email"
            variant="underlined"
            v-model="email"
          />
          <v-text-field
            :rules="[rules.required]"
            label="Short name"
            variant="underlined"
            v-model="shortName"
          />
          <v-text-field
            :rules="[rules.required]"
            label="Full name"
            variant="underlined"
            v-model="fullName"
          />
          <v-text-field
            :rules="[rules.required]"
            type="password"
            label="Password"
            variant="underlined"
            v-model="password"
          />
        </v-form>
        <v-btn class="mt-3" color="primary" v-on:click="register" block>Register</v-btn>
      </v-card>
    </v-container>
  </template>
  <template v-if="complete">
    <v-container class="fill-height d-flex align-center justify-center" fluid>
      <v-card class="pa-5" max-width="400">
        <v-card-title class="text-h5">Registration complete</v-card-title>
        <v-card-subtitle> </v-card-subtitle>
        <v-card-item class="d-flex justify-center">
          <v-icon color="success" icon="mdi-check-circle" size="x-large"></v-icon>
        </v-card-item>
        <v-card-text> Please check your email for more information. </v-card-text>
      </v-card>
    </v-container>
  </template>
</template>
