<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
const value = ref<number>(-1)
const route = useRoute()
watch(route, () => {
  value.value = (route.meta.bottomNav || 0) as number
})
</script>
<template>
  <v-layout class="overflow-visible" style="height: 56px">
    <v-bottom-navigation
      bg-color="secondary"
      :active="route.meta.bottomNav !== false"
      grow
      v-model="value"
      mode="shift"
    >
      <v-btn to="/tasks">
        <v-icon>mdi-list-box</v-icon>
        <span>Tasks</span>
      </v-btn>

      <v-btn to="/homes">
        <v-icon>mdi-home-group</v-icon>
        <span>Homes</span>
      </v-btn>

      <v-btn to="/profile">
        <v-icon>mdi-account-circle</v-icon>
        <span>Profile</span>
      </v-btn>
    </v-bottom-navigation>
  </v-layout>
</template>
