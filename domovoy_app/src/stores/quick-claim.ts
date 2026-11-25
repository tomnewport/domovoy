import { defineStore } from 'pinia'
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { AlreadyDoneError, useRegularJobStore, type RegularJobDefinition } from './regular-job'

// How long a job ticked off the list waits before it's sent, so a mis-tap
// can be undone. (Undoing a claim the server has already recorded would
// mean reversing scores and the next assignment, so it isn't sent yet.)
export const UNDO_SECONDS = 5

interface Pending {
  definition: RegularJobDefinition // as it was when ticked, naming that occurrence
  timer: number
  toastId: string
}

// Jobs ticked off straight from the task list: shown as done at once, sent
// after the undo window (or as soon as the app is hidden, so closing it
// doesn't lose them).
export const useQuickClaimStore = defineStore('quick-claim', () => {
  const regularJobStore = useRegularJobStore()
  const pending = new Map<number, Pending>()
  // Ids of jobs waiting to be sent, for the list to show them as done.
  const pendingIds = ref<number[]>([])

  function forget(id: number) {
    const entry = pending.get(id)
    if (entry) clearTimeout(entry.timer)
    pending.delete(id)
    pendingIds.value = pendingIds.value.filter((p) => p !== id)
  }

  async function send(id: number) {
    const entry = pending.get(id)
    if (!entry) return
    clearTimeout(entry.timer)
    const { definition, toastId } = entry
    // The Undo message becomes the outcome. (vue-sonner 1.2 can't dismiss a
    // message by id, but it can replace one, which starts its timer afresh.)
    try {
      const result = await regularJobStore.claim({ definition, celebrate: false })
      toast.success(`${definition.name}: +${result.value} points`, {
        id: toastId,
        duration: 6000,
        action: { label: 'See scores', onClick: () => regularJobStore.openMotivation() }
      })
    } catch (err) {
      if (err instanceof AlreadyDoneError)
        toast.info(`${definition.name} was already done, so nothing changed.`, {
          id: toastId,
          duration: 6000,
          action: undefined
        })
      else
        toast.error(`${definition.name} wasn't marked done. Try again.`, {
          id: toastId,
          duration: 8000,
          action: undefined
        })
    } finally {
      forget(id)
    }
  }

  function tick(definition: RegularJobDefinition) {
    const id = definition.id
    if (!id || pending.has(id)) return
    const toastId = `quick-claim-${id}`
    pending.set(id, {
      definition,
      toastId,
      timer: window.setTimeout(() => send(id), UNDO_SECONDS * 1000)
    })
    pendingIds.value = [...pendingIds.value, id]
    // No timer of its own: it stays until it's replaced by the outcome, or
    // by "undone" (so it can't close a moment before the claim is sent).
    toast(`${definition.name} done`, {
      id: toastId,
      duration: Infinity,
      action: { label: 'Undo', onClick: () => undo(id) }
    })
  }

  function undo(id: number) {
    const entry = pending.get(id)
    if (!entry) return
    forget(id)
    toast(`${entry.definition.name}: undone`, {
      id: entry.toastId,
      duration: 2500,
      action: undefined
    })
  }

  function flush() {
    for (const id of [...pending.keys()]) void send(id)
  }

  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') flush()
    })
    window.addEventListener('pagehide', flush)
  }

  const isPending = (id: number | null | undefined) => !!id && pendingIds.value.includes(id)

  return { pendingIds, isPending, tick, undo, flush }
})
