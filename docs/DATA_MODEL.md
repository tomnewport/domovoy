# Data model reference

The backend has six models across three apps. All persistence is via the Django
ORM (SQLite today). This describes the schema **as it is today**; see
[ARCHITECTURE.md](ARCHITECTURE.md) for how the behaviour around these models
works.

## Entity overview

```
DmvUser ──< Membership >── Home ──< RegularJobDefinition ──< RegularJobInstance
   │            │                          │
   │            └──< Holiday               └─ next_assigned_to ──> DmvUser
   └─ (completed_by) ──< RegularJobInstance
```

- A **User** belongs to many **Homes** through **Membership** (which carries
  their score).
- A **Membership** can have many **Holidays**.
- A **Home** has many **Regular Job Definitions**.
- Each completion of a job is a **Regular Job Instance**.

---

## `dmv_user.DmvUser`

Extends Django's `AbstractUser` (so it inherits `username`, `password`, `email`,
`is_staff`, `is_active`, `date_joined`, …). Set as `AUTH_USER_MODEL`.

| Field | Type | Notes |
| --- | --- | --- |
| `name_short` | char(16), nullable | Display first-name/nickname |
| `name_full` | char(128), nullable | Full display name |
| `email_verified` | bool | Set true once an email link is verified |
| `email_link_hash` | char(256), nullable | Hashed one-time login code |
| `email_link_sent` | datetime, nullable | When the last link was issued (drives expiry + backoff) |

Key methods: `send_email_code()` (issue + email a magic link, 1-min backoff),
`verify_email_code(code)` (validate, 30-min expiry, marks `email_verified`).

> The magic-link fields/methods become redundant under the hosted-auth migration
> (issue #17).

---

## `dmv_home.Home`

A household. Also holds the gamification configuration.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `name` | char(128), **unique** | | |
| `description` | text, nullable | | |
| `members` | M2M → DmvUser (through `Membership`) | | |
| `base_score` | uint | 0 | Absorbs the offset from score re-normalisation |
| `d6_cost` | uint16 | 60 | Score (≈ minutes) needed to earn one extra die |
| `d6_min` | uint16 | 1 | Minimum dice every member rolls |
| `d6_max` | uint16 | 6 | Maximum dice a member can roll |
| `overdue_bounty` | uint16 | 50 | % factor in the overdue bonus formula |

## `dmv_home.Membership`

A user's place in a home and their running score.

| Field | Type | Notes |
| --- | --- | --- |
| `user` | FK → DmvUser (CASCADE) | `related_name="memberships"` |
| `home` | FK → Home (CASCADE) | `related_name="memberships"` |
| `score` | uint | Relative standing; periodically re-normalised so the lowest member is 0 |

Method: `filter_available_dates(candidates)` — yields only candidate dates that
don't fall inside one of the member's holidays.

## `dmv_home.Holiday`

A date range a member is unavailable.

| Field | Type | Notes |
| --- | --- | --- |
| `membership` | FK → Membership (CASCADE) | |
| `note` | char(256) | |
| `from_date` | datetime | |
| `to_date` | datetime | |

---

## `regular_job.RegularJobDefinition`

A recurring chore, including its schedule rules and its *currently scheduled*
assignment.

| Field | Type | Notes |
| --- | --- | --- |
| `home` | FK → Home (CASCADE) | `related_name="regular_jobs"` |
| `name` | char(128) | |
| `description` | text, nullable | |
| `value_min` / `value_max` / `value_default` | uint16 | Point range awarded on completion |
| `open_for_days` | uint16 (def 0) | How early before the due date it can be started |
| `criticality` | char(1): `H`/`M`/`L` (def `L`) | Deadline strictness (see ARCHITECTURE) |
| `rules` | JSON (def `{}`) | A serialised `Ruleset` (list of `delay:v1` / `calendar:v1` rules) |
| `assignment_notes` | JSON, nullable | Serialised `RuleComputeResult` explaining the current assignment |
| `next_assigned_to` | FK → DmvUser (SET_NULL, nullable) | Who currently holds the job |
| `next_assigned_date` | datetime, nullable | When it was assigned |
| `next_assigned_start_date` | datetime, nullable | Earliest the assignee can start |
| `next_assigned_due_date` | datetime, nullable | Deadline |

Computed properties: `days_overdue`, `bonus` (overdue incentive). Key methods:
`assign()` (compute the next assignee/date — the dice lottery), `claim(user,
value)` (record completion, re-normalise scores, re-assign), `adjust()`
(recompute the current assignment, e.g. after a rules edit), `snooze_options()`,
`validate_value()`.

## `regular_job.RegularJobInstance`

An immutable record of one completion.

| Field | Type | Notes |
| --- | --- | --- |
| `job` | FK → RegularJobDefinition (CASCADE) | `related_name="instances"` |
| `value` | uint16 | Points awarded (incl. any bonus) |
| `bonus` | uint16 | The overdue-bonus part of `value`; `value - bonus` is the job's own points (used by upkeep). Recorded from migration `0002`; earlier rows hold an estimate (`value` above the job's `value_max`) |
| `completed_by` | FK → DmvUser (PROTECT) | `related_name="regular_jobs"` |
| `assigned_at` / `can_start_at` / `due_at` / `completed_at` | datetime, nullable | Snapshot of the assignment at completion time |

---

## Migrations & importer

- Migrations live under each app's `migrations/` directory; apply with
  `manage.py migrate`.
- `dmv_home/management/commands/migrate_from_glg.py` is a one-off importer that
  ingests data from an earlier app ("glg") — historical context for the rewrite,
  not part of normal operation.
