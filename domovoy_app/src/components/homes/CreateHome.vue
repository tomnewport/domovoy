<script setup lang="ts">
import { ref } from 'vue'
import type { SubmitEventPromise } from 'vuetify'
import { client, getHeaders } from '@/services/domovoy'
import { apiErrorMessage } from '@/services/domovoy/errors'
import { useHomesStore } from '@/stores/homes'

const homesStore = useHomesStore()

const name = ref<string>('')
const description = ref<string>('')
const dialog = ref<boolean>(false)
const saving = ref(false)
const error = ref<string | null>(null)
const required = (v: string) => !!v.trim() || 'Give the home a name'

async function create(event: SubmitEventPromise) {
  if (saving.value || !(await event).valid) return
  saving.value = true
  error.value = null
  try {
    const result = await client.POST('/api/homes/v1/homes', {
      body: { name: name.value.trim(), description: description.value },
      headers: getHeaders()
    })
    if (!result.response.ok) {
      error.value = apiErrorMessage(result.error, 'Could not create the home.')
      return
    }
    await homesStore.reloadHomes()
    name.value = ''
    description.value = ''
    dialog.value = false
  } catch {
    error.value = 'Could not reach the server. Check your connection and try again.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <v-dialog v-model="dialog" fullscreen transition="dialog-top-transition">
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn icon text="Create home" v-bind="activatorProps">
        <v-icon>mdi-plus</v-icon>
      </v-btn>
    </template>

    <template v-slot:default>
      <v-card>
        <v-toolbar color="secondary">
          <v-btn icon="mdi-close" @click="dialog = false"></v-btn>
          <v-toolbar-title>Create home</v-toolbar-title>
        </v-toolbar>
        <v-card-item>
          <v-form @submit.prevent="create">
            <v-text-field
              v-model="name"
              label="Name"
              variant="underlined"
              :rules="[required]"
              validate-on="submit"
            />
            <v-textarea v-model="description" label="Description" variant="underlined" />
            <v-alert v-if="error" type="error" variant="tonal" density="compact" :text="error" />
            <v-col class="d-flex justify-end">
              <v-btn type="submit" variant="text" :loading="saving">Create</v-btn>
            </v-col>
          </v-form>
        </v-card-item>
      </v-card>
    </template>
  </v-dialog>
</template>
