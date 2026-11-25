<script setup lang="ts">
import HolidayList from '@/components/profile/HolidayList.vue'
import AuthWall from '@/components/auth/AuthWall.vue'
import Logout from '@/components/auth/Logout.vue'
</script>
<template>
  <AuthWall>
    <v-toolbar color="secondary" title="Profile" app>
      <v-spacer></v-spacer>
      <Logout />
    </v-toolbar>
    <HolidayList />
  </AuthWall>
</template>
