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
  <!-- Opened by hand rather than through the dialog's activator slot: the
       activator's attributes, aria-label included, land on v-fab's wrapper
       div, which would leave the button itself without a name. -->
  <v-fab
    class="me-4 mb-14"
    color="primary"
    location="bottom end"
    fixed
    appear
    app
    icon
    @click="menu = true"
  >
    <v-icon icon="mdi-check" />
    <span class="d-sr-only">Complete a job</span>
  </v-fab>
  <v-dialog v-model="menu">
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
          <v-btn @click="menu = false">Cancel</v-btn>
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
