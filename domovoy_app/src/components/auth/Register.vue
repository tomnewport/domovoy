<script setup lang="ts">
import type { VForm } from 'vuetify/components'
import { onBeforeUnmount, ref, watch } from 'vue'
import API from '@/services/domovoy'
import { useHashcash } from '@/utils/hashcash'
import AuthLayout from './AuthLayout.vue'
import { emailRules, isEmail, required } from './rules'

const hashcash = useHashcash()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const shortName = ref('')
const fullName = ref('')
const form = ref<VForm | null>(null)
const submitting = ref<boolean>(false)
const error = ref<string | null>(null)
const complete = ref<boolean>(false)

// The proof-of-work is for the email address; solve it while the rest of the
// form is being filled in.
let debounce: ReturnType<typeof setTimeout> | undefined
watch(email, (value) => {
  clearTimeout(debounce)
  if (isEmail(value)) debounce = setTimeout(() => hashcash.prepare(value), 400)
})
onBeforeUnmount(() => {
  clearTimeout(debounce)
  hashcash.cancel()
})

async function register() {
  if (submitting.value) return
  // Validate on submit (showing what's missing) rather than greying out the button.
  const { valid } = (await form.value?.validate()) ?? { valid: false }
  if (!valid) return
  submitting.value = true
  error.value = null
  try {
    const stamp = await hashcash.stampFor(email.value)
    const response = await API.usersV1.postNew(
      {
        email: email.value,
        username: email.value,
        password: password.value,
        name_short: shortName.value,
        name_full: fullName.value
      },
      stamp
    )
    if (response.response.status === 400) {
      error.value = 'There’s already an account with that email. Try logging in instead.'
    } else if (!response.response.ok) {
      error.value = 'We couldn’t create your account. Please try again.'
    } else {
      complete.value = true
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'We couldn’t create your account.'
  } finally {
    submitting.value = false
  }
}
</script>
<template>
  <AuthLayout compact>
    <v-card-text v-if="complete" class="pa-6 text-center">
      <v-icon icon="mdi-email-check-outline" size="56" color="primary" class="mb-3" />
      <h2 class="text-title-large">Check your inbox</h2>
      <p class="text-body-medium text-medium-emphasis mt-2">
        We sent a link to <strong>{{ email }}</strong> to confirm your address. Open it to finish
        signing in.
      </p>
      <v-btn to="/" variant="text" color="primary" class="mt-4">Back to log in</v-btn>
    </v-card-text>

    <template v-else>
      <v-card-item class="px-6 pt-6">
        <v-card-title class="text-title-large">Create your account</v-card-title>
        <v-card-subtitle>It only takes a minute.</v-card-subtitle>
      </v-card-item>
      <v-card-text class="px-6 pb-6">
        <v-form @submit.prevent="register" ref="form">
          <v-alert
            v-if="error"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-4"
            :text="error"
          />
          <v-text-field
            v-model="email"
            label="Email"
            type="email"
            autocomplete="email"
            inputmode="email"
            prepend-inner-icon="mdi-email-outline"
            variant="outlined"
            :rules="emailRules"
          />
          <v-text-field
            v-model="fullName"
            label="Full name"
            autocomplete="name"
            prepend-inner-icon="mdi-account-outline"
            variant="outlined"
            :rules="[required]"
          />
          <v-text-field
            v-model="shortName"
            label="Short name"
            hint="What your housemates call you, shown on the task list"
            persistent-hint
            autocomplete="nickname"
            prepend-inner-icon="mdi-account-circle-outline"
            variant="outlined"
            :rules="[required]"
            class="mb-2"
          />
          <v-text-field
            v-model="password"
            label="Password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="new-password"
            prepend-inner-icon="mdi-lock-outline"
            variant="outlined"
            :rules="[required]"
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
          <v-btn
            :loading="submitting"
            type="submit"
            class="mt-2"
            color="primary"
            size="large"
            block
          >
            Create account
          </v-btn>
        </v-form>
      </v-card-text>
    </template>

    <template #below>
      <div v-if="!complete" class="text-center text-body-medium">
        Already have an account?
        <v-btn to="/" variant="text" color="primary" class="px-2">Log in</v-btn>
      </div>
    </template>
  </AuthLayout>
</template>
