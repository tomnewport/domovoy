<script setup lang="ts">
// The frame for every logged-out screen: logo and name, then the screen's own
// card. `compact` drops the tagline and feature list for secondary screens.
const { compact = false } = defineProps<{ compact?: boolean }>()

const features = [
  { icon: 'mdi-dice-multiple-outline', text: 'Jobs shared out by points and a roll of the dice' },
  { icon: 'mdi-palm-tree', text: 'Chores are scheduled around holidays' },
  { icon: 'mdi-medal-outline', text: 'Bonus points for picking up late jobs' }
]
</script>
<template>
  <div class="auth-layout">
    <div class="auth-layout__inner">
      <header class="auth-layout__brand">
        <img
          class="auth-layout__logo"
          src="/web-app-manifest-192x192.png"
          alt=""
          width="72"
          height="72"
        />
        <h1 class="text-display-small font-weight-bold mt-3">Domovoy</h1>
        <p v-if="!compact" class="text-body-large text-medium-emphasis mt-1">
          Share the chores. Fairly.
        </p>
      </header>

      <v-card class="auth-layout__card" rounded="xl" elevation="8">
        <slot />
      </v-card>

      <slot name="below" />

      <ul v-if="!compact" class="auth-layout__features">
        <li v-for="feature in features" :key="feature.icon">
          <v-icon :icon="feature.icon" size="20" color="primary" />
          <span>{{ feature.text }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>
<style scoped>
.auth-layout {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  justify-content: center;
  padding: 48px 16px 32px;
  background: radial-gradient(
      120% 60% at 50% 0%,
      rgba(var(--v-theme-primary), 0.28) 0%,
      transparent 60%
    ),
    radial-gradient(90% 50% at 100% 100%, rgba(var(--v-theme-secondary), 0.22) 0%, transparent 70%),
    rgb(var(--v-theme-background));
}

.auth-layout__inner {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.auth-layout__brand {
  text-align: center;
}

.auth-layout__logo {
  display: block;
  margin: 0 auto;
  border-radius: 20px;
  filter: drop-shadow(0 8px 24px rgba(var(--v-theme-primary), 0.45));
}

.auth-layout__card {
  width: 100%;
}

.auth-layout__features {
  list-style: none;
  padding: 0 8px;
  margin: 0;
  display: grid;
  gap: 12px;
}

.auth-layout__features li {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-background), var(--v-medium-emphasis-opacity));
}
</style>
