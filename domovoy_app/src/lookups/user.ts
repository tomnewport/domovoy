import { useHomesStore } from '@/stores/homes'
import { useSessionStore } from '@/stores/session'
import { computed } from 'vue'

export function useUserLookup({ id }: { id: number }) {
  const homesStore = useHomesStore()
  homesStore.ensureLoaded()

  const users = computed(() => {
    return (
      homesStore.homes?.flatMap((home) =>
        home.memberships
          .filter((membership) => membership.user.id === id)
          .map((membership) => membership.user)
      ) || []
    )
  })

  return computed(() => {
    return users.value.find((user) => user.id === id)
  })
}

export function useCurrentUser() {
  const sessionStore = useSessionStore()
  return computed(() => {
    return sessionStore.session
  })
}
