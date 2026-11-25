import { computed, ref } from 'vue'
import { differenceInCalendarDays, format, parseISO } from 'date-fns'
import { client, getHeaders } from '@/services/domovoy'
import type { components } from '@/services/domovoy/schema.d.ts'

type Holiday = components['schemas']['HolidaySchema']

// Holidays are stored per home (per membership), but you're away from all of
// them at once: the same dates and note in several homes show as one holiday.
export interface HolidayGroup {
  key: string
  from: string // YYYY-MM-DD, first day away
  to: string // YYYY-MM-DD, last day away
  note: string
  homeIds: number[]
  records: Holiday[]
}

export interface HolidayDraft {
  from: string
  to: string
  note: string
  homeIds: number[]
}

// Dates are whole days. The server stores midnight UTC of each day; reading
// only the date part keeps them from shifting with the viewer's time zone.
const day = (value: string) => value.slice(0, 10)
const toServer = (date: string) => `${date}T00:00:00Z`

export function todayString() {
  return format(new Date(), 'yyyy-MM-dd')
}

export function describeRange(from: string, to: string) {
  const a = parseISO(from)
  const b = parseISO(to)
  const days = differenceInCalendarDays(b, a) + 1
  const sameYear = a.getFullYear() === b.getFullYear()
  const start = format(a, sameYear ? 'EEE d MMM' : 'EEE d MMM yyyy')
  const end = format(b, 'EEE d MMM yyyy')
  return { text: from === to ? end : `${start} – ${end}`, days }
}

export function useHolidays() {
  const records = ref<Holiday[]>([])
  const loaded = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    error.value = null
    const { data } = await client.GET('/api/homes/v1/holidays', {
      headers: getHeaders(),
      params: { query: { include_past: true } }
    })
    if (data) records.value = data
    else error.value = 'Could not load your holidays.'
    loaded.value = true
  }

  const groups = computed<HolidayGroup[]>(() => {
    const byKey = new Map<string, HolidayGroup>()
    for (const h of records.value) {
      const from = day(h.from_date)
      const to = day(h.to_date)
      const key = `${from}|${to}|${h.note}`
      const group = byKey.get(key) ?? { key, from, to, note: h.note, homeIds: [], records: [] }
      group.homeIds.push(h.membership.home.id as number)
      group.records.push(h)
      byKey.set(key, group)
    }
    return [...byKey.values()].sort((a, b) => a.from.localeCompare(b.from))
  })

  const today = todayString()
  const current = computed(() => groups.value.find((g) => g.from <= today && g.to >= today) ?? null)
  const upcoming = computed(() => groups.value.filter((g) => g.to >= today))
  const past = computed(() => groups.value.filter((g) => g.to < today).reverse())

  async function check(result: { error?: unknown; response: Response }) {
    if (result.error || !result.response.ok) {
      const detail = (result.error as { detail?: string } | undefined)?.detail
      throw new Error(typeof detail === 'string' ? detail : 'Could not save the holiday.')
    }
  }

  async function create(draft: HolidayDraft) {
    const body = { from_date: toServer(draft.from), to_date: toServer(draft.to), note: draft.note }
    try {
      await Promise.all(
        draft.homeIds.map(async (homeId) =>
          check(
            await client.POST('/api/homes/v1/holidays/', {
              headers: getHeaders(),
              body: { ...body, home_id: homeId }
            })
          )
        )
      )
    } finally {
      await load()
    }
  }

  // Dates and note change on every home's record; homes added or removed
  // gain or lose a record.
  async function update(group: HolidayGroup, draft: HolidayDraft) {
    const body = { from_date: toServer(draft.from), to_date: toServer(draft.to), note: draft.note }
    const tasks: Promise<void>[] = []
    for (const record of group.records) {
      const homeId = record.membership.home.id as number
      const path = { holiday_id: String(record.id) }
      if (draft.homeIds.includes(homeId)) {
        tasks.push(
          client
            .PATCH('/api/homes/v1/holidays/{holiday_id}', {
              headers: getHeaders(),
              params: { path },
              body
            })
            .then(check)
        )
      } else {
        tasks.push(
          client
            .DELETE('/api/homes/v1/holidays/{holiday_id}', {
              headers: getHeaders(),
              params: { path }
            })
            .then(check)
        )
      }
    }
    for (const homeId of draft.homeIds.filter((id) => !group.homeIds.includes(id))) {
      tasks.push(
        client
          .POST('/api/homes/v1/holidays/', {
            headers: getHeaders(),
            body: { ...body, home_id: homeId }
          })
          .then(check)
      )
    }
    try {
      await Promise.all(tasks)
    } finally {
      await load()
    }
  }

  async function remove(group: HolidayGroup) {
    try {
      await Promise.all(
        group.records.map((record) =>
          client
            .DELETE('/api/homes/v1/holidays/{holiday_id}', {
              headers: getHeaders(),
              params: { path: { holiday_id: String(record.id) } }
            })
            .then(check)
        )
      )
    } finally {
      await load()
    }
  }

  return { load, loaded, error, groups, current, upcoming, past, create, update, remove }
}
