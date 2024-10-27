<script setup lang="ts">
import { ref } from 'vue'
import { client, getHeaders } from '@/services/domovoy'
import { useHomesStore } from '@/stores/homes'

const homesStore = useHomesStore()

const name = ref<string>('')
const description = ref<string>('')
const dialog = ref<boolean>(false)

async function create() {
  try {
    const { error } = await client.POST('/api/homes/v1/homes', {
      body: { name: name.value, description: description.value },
      headers: getHeaders()
    })
    if (!error) {
      homesStore.reloadHomes()
      dialog.value = false
    }
  } catch (error) {
    console.error('Failed to create home:', error)
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

    <template v-slot:default="{ isActive }">
      <v-card>
        <v-toolbar color="secondary">
          <v-btn icon="mdi-close" @click="dialog = false"></v-btn>
          <v-toolbar-title>Create home</v-toolbar-title>
        </v-toolbar>
        <v-card-item>
          <v-form @submit.prevent="create">
            <v-text-field v-model="name" label="Name" variant="underlined" />
            <v-textarea v-model="description" label="Description" variant="underlined" />
            <v-col class="d-flex justify-end">
              <v-btn type="submit" variant="text">Create</v-btn>
            </v-col>
          </v-form>
        </v-card-item>
      </v-card>
    </template>
  </v-dialog>
</template>
