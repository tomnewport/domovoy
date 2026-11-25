<script setup lang="ts">
import type { VForm } from 'vuetify/components'
import { onBeforeUnmount, ref, watch } from 'vue'
import API from '@/services/domovoy'
import { useHashcash } from '@/utils/hashcash'
import { emailRules, isEmail } from './rules'

const hashcash = useHashcash()
const form = ref<VForm | null>(null)
const email = ref('')
const sending = ref(false)
const sentTo = ref<string | null>(null)
const error = ref<string | null>(null)

// Start the proof-of-work for an address once it looks complete, so pressing
// the button only has to send the request.
let debounce: ReturnType<typeof setTimeout> | undefined
watch(email, (value) => {
  clearTimeout(debounce)
  if (isEmail(value)) debounce = setTimeout(() => hashcash.prepare(value), 400)
})
onBeforeUnmount(() => {
  clearTimeout(debounce)
  hashcash.cancel()
})

async function send() {
  if (sending.value) return
  // Validate on submit (showing what's missing) rather than greying out the button.
  const { valid } = (await form.value?.validate()) ?? { valid: false }
  if (!valid) return
  sending.value = true
  error.value = null
  try {
    const stamp = await hashcash.stampFor(email.value)
    const response = await API.usersV1.postEmailCode(email.value, stamp)
    if (response.response.status === 401) {
      error.value = 'We couldn’t find an account with that email.'
    } else if (!response.response.ok) {
      error.value = 'Could not send the link. Please try again.'
    } else {
      sentTo.value = email.value
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Could not send the link.'
  } finally {
    sending.value = false
  }
}

function startOver() {
  sentTo.value = null
  error.value = null
}
</script>
<template>
  <div v-if="sentTo" class="text-center py-2">
    <v-icon icon="mdi-email-check-outline" size="56" color="primary" class="mb-3" />
    <h2 class="text-h6">Check your inbox</h2>
    <p class="text-body-2 text-medium-emphasis mt-2">
      We sent a login link to <strong>{{ sentTo }}</strong
      >. It works once and expires in 30 minutes.
    </p>
    <p class="text-body-2 text-medium-emphasis mt-2">
      Nothing there? Check your spam folder, or send another after a minute.
    </p>
    <v-btn variant="text" class="mt-3" v-on:click="startOver">Use a different email</v-btn>
  </div>
  <v-form v-else @submit.prevent="send" ref="form">
    <p class="text-body-2 text-medium-emphasis mb-4">
      We’ll email you a link that logs you straight in, no password needed.
    </p>
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
      required
    />
    <v-btn :loading="sending" type="submit" class="mt-2" color="primary" size="large" block>
      Email me a link
    </v-btn>
  </v-form>
</template>
