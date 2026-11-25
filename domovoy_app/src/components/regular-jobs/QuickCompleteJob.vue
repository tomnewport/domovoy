<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRegularJobStore, type RegularJobDefinition } from '@/stores/regular-job'
import CompleteJobCard from '@/components/regular-jobs/CompleteJobCard.vue'
import CongratulateCard from '@/components/regular-jobs/CongratulateCard.vue'

const regularJobStore = useRegularJobStore()
const menu = ref<boolean>(false)
const jobDefinitionId = ref<number | undefined>(undefined)
const jobDefinition = ref<RegularJobDefinition | undefined>(undefined)

onMounted(async () => {
  await regularJobStore.reload()
})

watch(menu, () => {
  jobDefinitionId.value = undefined
})

watch(jobDefinitionId, () => {
  jobDefinition.value = regularJobStore.definitions.find(({ id }) => id === jobDefinitionId.value)
})
</script>
<template>
  <v-dialog v-model="menu">
    <template v-slot:activator="{ props: activatorProps }">
      <v-fab
        v-bind="activatorProps"
        class="me-4 mb-14"
        icon="mdi-check"
        aria-label="Complete a job"
        color="primary"
        location="bottom end"
        fixed
        appear
        app
      ></v-fab>
    </template>
    <template v-slot:default>
      <v-card v-if="jobDefinition === undefined">
        <v-card-title>Complete a job</v-card-title>
        <v-autocomplete
          v-model="jobDefinitionId"
          :items="regularJobStore.definitions"
          item-title="name"
          item-value="id"
          label="Select"
          :loading="!regularJobStore.fresh && regularJobStore.loading"
          :no-data-text="regularJobStore.hasData ? 'No matching jobs' : 'Loading jobs…'"
          closable-chips
          autofocus
          disable-gutters
        ></v-autocomplete>
        <v-card-actions>
          <v-btn>Cancel</v-btn>
          <v-spacer></v-spacer>
        </v-card-actions>
      </v-card>
      <CompleteJobCard
        v-if="jobDefinition"
        :onClose="
          () => {
            menu = false
          }
        "
        :jobDefinition="jobDefinition"
      />
    </template>
  </v-dialog>
  <CongratulateCard />
</template>
