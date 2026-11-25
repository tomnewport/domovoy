// Series colours for charts that compare housemates.
//
// The categorical palette's dark steps, in its fixed order. Validated against
// the app's surface (#003b4e) with the dataviz palette validator: lightness,
// chroma, colour-blind separation of neighbours, normal-vision separation and
// 3:1 contrast all pass.
export const SERIES_COLORS = [
  '#338ced', // blue
  '#e76624', // orange
  '#00a888', // aqua
  '#d28e05', // yellow
  '#e24d8b', // magenta
  '#0aac23', // green
  '#9887ef', // violet
  '#eb6263' // red
]

// Beyond eight people the palette can't stay distinguishable; the rest share
// a neutral grey and are told apart by the legend and tooltip.
export const OVERFLOW_COLOR = '#9c9c9c'

/**
 * A colour per member of one home, stable across screens and refreshes:
 * members are ordered by user id (never by score), so a person keeps their
 * colour whoever is winning.
 */
export function memberColors(userIds: number[]): Map<number, string> {
  const ordered = [...new Set(userIds)].sort((a, b) => a - b)
  return new Map(ordered.map((id, index) => [id, SERIES_COLORS[index] ?? OVERFLOW_COLOR]))
}

function luminance(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** White or near-black, whichever reads better on `hex` (e.g. initials on an avatar). */
export function textOn(hex: string): string {
  const l = luminance(hex)
  const onWhite = 1.05 / (l + 0.05)
  const onDark = (l + 0.05) / (luminance('#191919') + 0.05)
  return onDark > onWhite ? '#191919' : '#ffffff'
}
