<script setup lang="ts">
import QuickCompleteJob from '@/components/regular-jobs/QuickCompleteJob.vue'
import AuthWall from '@/components/auth/AuthWall.vue'
import TodoList from '@/components/regular-jobs/TodoList.vue'
</script>
<template>
  <AuthWall>
    <TodoList />
    <QuickCompleteJob />
  </AuthWall>
</template>
