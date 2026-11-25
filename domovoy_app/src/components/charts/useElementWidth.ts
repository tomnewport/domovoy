import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

// The element's current width in CSS pixels, so a chart can draw in real
// pixels (round dots, crisp text) instead of stretching a fixed viewBox.
export function useElementWidth(element: Ref<HTMLElement | null>, fallback = 300) {
  const width = ref(fallback)
  let observer: ResizeObserver | undefined

  onMounted(() => {
    if (!element.value) return
    width.value = element.value.clientWidth || fallback
    observer = new ResizeObserver(([entry]) => {
      width.value = Math.max(1, Math.round(entry.contentRect.width))
    })
    observer.observe(element.value)
  })
  onBeforeUnmount(() => observer?.disconnect())

  return width
}
