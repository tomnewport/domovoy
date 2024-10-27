<script setup lang="ts">
import { client, getHeaders } from '@/services/domovoy'
import { useHomesStore } from '@/stores/homes'
import { ref, onMounted } from 'vue'
const { onChange } = defineProps<{ onChange: () => void }>()
const open = ref<boolean>(false)
const homesStore = useHomesStore()

const fromDate = ref<string>('')
const toDate = ref<string>('')
const note = ref<string>('')
const homeIds = ref<number[]>([])

async function save() {
  await Promise.all(
    homeIds.value.map((homeId) =>
      client.POST('/api/homes/v1/holidays/', {
        headers: getHeaders(),
        body: {
          from_date: fromDate.value,
          to_date: toDate.value,
          note: note.value,
          home_id: homeId
        }
      })
    )
  )
  onChange()
  open.value = false
}

onMounted(() => {
  homesStore.reloadHomes()
})
</script>
<template>
  <v-dialog v-model="open">
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn v-bind="activatorProps"> <v-icon>mdi-plus</v-icon> Create </v-btn>
    </template>
    <template v-slot:default="{ isActive }">
      <v-card>
        <v-toolbar color="secondary">
          <v-btn @click="isActive.value = false" icon> <v-icon>mdi-close</v-icon> </v-btn
          ><v-toolbar-title>Add holiday</v-toolbar-title></v-toolbar
        >
        <v-card-text>
          <v-select
            v-model="homeIds"
            label="Home"
            item-title="name"
            item-value="id"
            :items="homesStore.homes || []"
            multiple
            chips
          ></v-select>
          <v-text-field v-model="note" label="Note" type="text"></v-text-field>
          <v-text-field v-model="fromDate" label="Start date" type="date"></v-text-field>
          <v-text-field v-model="toDate" label="End date" type="date"></v-text-field>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>

          <v-btn text="Save" color="primary" @click="save"></v-btn>
        </v-card-actions>
      </v-card>
    </template>
  </v-dialog>
</template>
