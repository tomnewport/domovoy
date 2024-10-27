import { computed, useSlots } from 'vue'

export function useSlotTextContent() {
  const slots = useSlots()

  const user = computed(() => {
    if (!slots.default) return undefined
    const value = slots.default()[0]
    if (typeof value.children !== 'string') return undefined
    return value.children.trim()
  })
  return user
}
