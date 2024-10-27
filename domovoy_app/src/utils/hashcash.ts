import { useHashcashConfigStore } from '@/stores/hashcash-config'

const crypto = window.crypto

export async function makeHeader(
  s: string,
  n: number,
  nonce: string,
  charset = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
): Promise<string> {
  const now =
    new Date().toISOString().slice(2, 10).replace(/-/g, '') +
    new Date().toISOString().slice(11, 16).replace(/:/g, '')
  const base = `1:${n}:${now}:${s}::${nonce}:`
  const encoder = new TextEncoder()
  const baseEncoded = encoder.encode(base)
  for await (const token of allStrings(charset)) {
    const value = new Uint8Array([...baseEncoded, ...encoder.encode(token)])
    if (trailingZeros(await hash(value)) >= n) {
      return base + token
    }
  }
  return ''
}

export function useHashcash() {
  const hashcashStore = useHashcashConfigStore()
  return async (subject: string) => {
    const { hashcashConfig } = hashcashStore
    if (!hashcashConfig) {
      throw new Error('Hashcash config not loaded')
    }
    const value = await makeHeader(subject, hashcashConfig.difficulty, hashcashConfig.nonces[0])
    return value
  }
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

async function hash(s: string | Uint8Array) {
  const encoder = new TextEncoder()
  const data = typeof s == 'string' ? encoder.encode(s) : s
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
  return BigInt('0x' + hashHex)
}
