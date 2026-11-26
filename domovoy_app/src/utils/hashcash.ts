import { useHashcashConfigStore } from '@/stores/hashcash-config'

const crypto = window.crypto

export async function makeHeader(
  s: string,
  n: number,
  nonce: string,
  charset = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
  isCancelled: () => boolean = () => false
): Promise<string> {
  const now =
    new Date().toISOString().slice(2, 10).replace(/-/g, '') +
    new Date().toISOString().slice(11, 16).replace(/:/g, '')
  const base = `1:${n}:${now}:${s}::${nonce}:`
  const encoder = new TextEncoder()
  const baseEncoded = encoder.encode(base)
  for await (const token of allStrings(charset)) {
    if (isCancelled()) return ''
    const value = new Uint8Array([...baseEncoded, ...encoder.encode(token)])
    if (trailingZeros(await hash(value)) >= n) {
      return base + token
    }
  }
  return ''
}

// Stamps are tied to their subject (the email address) and a timestamp the
// server accepts for an hour; reuse one for half that.
const STAMP_MAX_AGE_MS = 30 * 60 * 1000

interface StampJob {
  subject: string
  startedAt: number
  promise: Promise<string>
  cancel: () => void
}

// Solving a stamp takes a few seconds on a phone. `prepare` starts on it in the
// background as soon as the email is known (e.g. while the rest of the form is
// filled in), so `stampFor` at submit time is usually instant.
export function useHashcash() {
  const hashcashStore = useHashcashConfigStore()
  let current: StampJob | null = null

  const isCurrent = (subject: string) =>
    current?.subject === subject && Date.now() - current.startedAt < STAMP_MAX_AGE_MS

  function start(subject: string): StampJob | null {
    const config = hashcashStore.hashcashConfig
    if (!config) return null
    current?.cancel()
    let cancelled = false
    current = {
      subject,
      startedAt: Date.now(),
      promise: makeHeader(subject, config.difficulty, config.nonces[0], undefined, () => cancelled),
      cancel: () => {
        cancelled = true
      }
    }
    return current
  }

  function prepare(subject: string) {
    if (!isCurrent(subject)) start(subject)
  }

  async function stampFor(subject: string): Promise<string> {
    if (isCurrent(subject) && current) return current.promise
    if (!hashcashStore.hashcashConfig) await hashcashStore.load()
    const job = start(subject)
    if (!job) throw new Error('Could not reach the server. Please try again.')
    return job.promise
  }

  function cancel() {
    current?.cancel()
    current = null
  }

  return { prepare, stampFor, cancel }
}

function trailingZeros(n: bigint) {
  if (n <= 0) return 0
  let count = 0
  while ((n & 1n) === 0n) {
    count++
    n >>= 1n // Right shift by 1 for BigInt
  }
  return count
}

// Generates a range of integers.
function* irange(n: number) {
  let i = 0
  while (i < n) {
    yield i++
  }
}

// Yields all strings in given character set, sorted by length.
async function* allStrings(charset = '0123456789ABCDEF') {
  const m = charset.length
  let n = 0
  while (true) {
    for (const i of irange(m ** n)) {
      yield [...Array(n)].map((_, j) => charset[Math.floor(i / m ** j) % m]).join('')
    }
    n++
  }
}

async function hash(s: string | Uint8Array<ArrayBuffer>) {
  const encoder = new TextEncoder()
  const data = typeof s == 'string' ? encoder.encode(s) : s
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
  return BigInt('0x' + hashHex)
}
