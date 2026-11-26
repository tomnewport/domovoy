import type { GetSessionResponse } from '@/services/domovoy/usersV1'
import type { RegularJobDefinition } from '@/stores/regular-job'

export enum JobClassification {
  UNSCHEDULED = 'Unscheduled',
  FUTURE = 'Future',
  IN_HOME = 'In home',
  ASSIGNED = 'Assigned',
  OVERDUE = 'Overdue',
  PRIORITY = 'Priority',
  URGENT = 'Urgent'
}

export function getJobClassification(job: RegularJobDefinition, you: null | GetSessionResponse) {
  if (!job.next_assigned_due_date) return JobClassification.UNSCHEDULED
  const now = new Date()
  const due = new Date(job.next_assigned_due_date)
  const assigned = new Date(job.next_assigned_date || 0)
  const yours = you?.id === job.next_assigned_to

  const hoursSinceAssigned = (now.valueOf() - assigned.valueOf()) / (1000 * 60 * 60)
  const daysToDue = (due.valueOf() - now.valueOf()) / (1000 * 24 * 60 * 60)
  const remainingTime = daysToDue / job.open_for_days

  if (remainingTime > 1) return JobClassification.FUTURE
  if (hoursSinceAssigned < 12 && daysToDue > 1) return JobClassification.FUTURE
  if (hoursSinceAssigned < 1) return JobClassification.FUTURE

  if (job.criticality === 'H') {
    if (remainingTime < 0.2) return JobClassification.URGENT
    if (yours) return JobClassification.PRIORITY
  }

  if (daysToDue < 0) return JobClassification.OVERDUE

  if (yours) return JobClassification.ASSIGNED

  return JobClassification.IN_HOME
}
