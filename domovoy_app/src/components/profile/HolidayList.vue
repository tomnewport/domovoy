<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { client, getHeaders } from '@/services/domovoy'
import type { components } from '@/services/domovoy/schema'
import CreateHoliday from '@/components/profile/CreateHoliday.vue'

const holidays = ref<components['schemas']['HolidaySchema'][]>([])

async function reload() {
  const result = await client.GET('/api/homes/v1/holidays', {
    headers: getHeaders()
  })
  holidays.value = result.data || []
}

onMounted(() => {
  reload()
})

async function deleteHoliday(id: number | null | undefined) {
  if (!id) throw new Error('No ID to delete')
  await client.DELETE('/api/homes/v1/holidays/{holiday_id}', {
    headers: getHeaders(),
    params: {
      path: { holiday_id: id.toString() }
    }
  })
  reload()
}
</script>
<template>
  <v-toolbar color="secondary" title="Profile" app><v-spacer></v-spacer></v-toolbar>
  <v-container>
    <v-card>
      <v-card-title>Holidays</v-card-title>
      <v-list>
        <v-list-item v-for="holiday of holidays" :key="holiday.id || -1">
          <v-list-item-title>
            {{ holiday.membership.user.name_full }} away from
            {{ holiday.membership.home.name }}
          </v-list-item-title>
          <v-list-item-subtitle
            >{{ new Date(holiday.from_date).toLocaleDateString() }} -
            {{ new Date(holiday.to_date).toLocaleDateString() }}
          </v-list-item-subtitle>
          <v-list-item-subtitle>{{ holiday.note }}</v-list-item-subtitle>
          <template v-slot:append>
            <v-btn icon variant="plain" v-on:click="deleteHoliday(holiday.id)"
              ><v-icon>mdi-trash-can</v-icon></v-btn
            >
          </template>
        </v-list-item>
      </v-list>
      <v-card-actions><v-spacer></v-spacer><CreateHoliday :onChange="reload" /></v-card-actions>
    </v-card>
  </v-container>
</template>
