<script setup lang="ts">
import { useHashcash } from '@/utils/hashcash'
import { ref } from 'vue'
import API from '@/services/domovoy'
import { toast } from 'vue-sonner'

const hashcash = useHashcash()
const valid = ref(false)

const email = ref('')
async function doSend() {
  const hashcashHeader = await hashcash(email.value)
  const response = await API.usersV1.postEmailCode(email.value, hashcashHeader)
  if (!response.response.ok) throw new Error('Could not send email')
}
const rules = {
  required: (value: string) => !!value || 'This field is required',
  email: (value: string) => /.+@.+\..+/.test(value) || 'E-mail must be valid'
}
function send() {
  toast.promise(doSend(), {
    loading: 'Sending email',
    success: () => {
      return `Please check your inbox`
    },
    error: (data: any) => data.toString()
  })
}
</script>
<template>
  <v-form @submit.prevent="send" v-model="valid">
    <v-text-field
      v-model="email"
      label="Email"
      variant="underlined"
      type="email"
      :rules="[rules.required, rules.email]"
      required
    />
    <v-btn :disabled="!valid" type="submit" class="mt-3" color="primary" block> Log in </v-btn>
  </v-form>
</template>
