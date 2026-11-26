import {
  startOfWeek,
  addWeeks,
  format,
  isTomorrow,
  isYesterday,
  isToday,
  isThisWeek,
  isThisYear
} from 'date-fns'

// "Today", "next Wednesday", "9th December" ... relative to `now`.
export function formatNaturalDate(value: Date, now: Date = new Date()): string {
  if (isToday(value)) return 'Today'
  if (isYesterday(value)) return 'Yesterday'
  if (isTomorrow(value)) return 'Tomorrow'
  if (isThisWeek(value, { weekStartsOn: 1 })) return `this ${format(value, 'EEEE')}`
  if (value > now && value < startOfWeek(addWeeks(now, 2), { weekStartsOn: 1 }))
    return `next ${format(value, 'EEEE')}`
  if (value < now && value > startOfWeek(addWeeks(now, -1), { weekStartsOn: 1 }))
    return `last ${format(value, 'EEEE')}`
  if (isThisYear(value)) return format(value, 'do MMMM')
  return format(value, 'do MMMM yyy')
}

// The same, to follow a word: "Due today", "Due this Friday".
export function formatNaturalDateInline(value: Date, now: Date = new Date()): string {
  const text = formatNaturalDate(value, now)
  return /^(Today|Tomorrow|Yesterday)$/.test(text) ? text.toLowerCase() : text
}
