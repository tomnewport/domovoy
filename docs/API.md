# API reference

The backend exposes a single [django-ninja](https://django-ninja.dev/) API
mounted at **`/api/`**, composed of three versioned routers. This document
describes the API **as it is today**. Interactive, always-up-to-date docs are
served at **`/api/docs`** (Swagger UI) and the raw schema at
**`/api/openapi.json`** — the frontend's typed client is generated from the
latter.

> Some endpoints have known quirks/bugs; these are noted inline and linked to
> their tracking issues so this document reflects the **actual** behaviour.

## Conventions

- **Base path:** all routes below are relative to `/api/`.
- **Content type:** `application/json` for request and response bodies.
- **Errors:** failures raise `HttpError` and return
  `{"detail": "<message>"}` with the relevant 4xx status.

## Authentication

Three auth modes are used across the endpoints (implemented as django-ninja
security classes in `domovoy/domovoy/security/`):

| Mode | Header | Used for |
| --- | --- | --- |
| **Session key** | `x-session-key: <key>` | All authenticated endpoints. The key is returned by `POST /users/v1/session`. Resolves to a verified `DmvUser`; 401 otherwise. |
| **Hashcash** | `X-Hashcash: <header>` | The two public, abuse-prone endpoints (`POST /users/v1/email_code`, `POST /users/v1/new`). A proof-of-work header solved by the client; see [ARCHITECTURE.md](ARCHITECTURE.md#authentication--abuse-protection). |
| **None** | — | `GET /users/v1/hashcash` only. |

> The session-key + hashcash scheme is slated for replacement by a hosted OAuth2
> provider — see issues #17 (provider) and the hashcash-removal checklist.

---

## Users — `/api/users/v1/`

### `GET /session` — current session
**Auth:** session key. Returns the logged-in user and session expiry.

`200` → `ActiveSessionResponse`
```jsonc
{
  "id": 1, "email": "h@example.com", "username": "HBerherbo",
  "name_full": "Herberto Berherbo", "name_short": "Herb",
  "session_expires": "2026-01-01T00:00:00Z"
}
```

### `POST /session` — log in (create session)
**Auth:** none. Verifies one or more authentication factors and starts a session.

Body — `CreateSessionRequest`:
```jsonc
{
  "email": "h@example.com",
  "factors": [
    { "factor_type": "password", "password": "…" }
    // or { "factor_type": "email_code", "email_code": "<uuid from email link>" }
  ]
}
```
At least **one** factor must verify and the user's email must be verified.
`200` → the session key (string), also returned in the `x-session-key`
response header.

### `DELETE /session` — log out
**Auth:** session key. Deletes the server-side session. `200` → empty.

### `POST /email_code` — request a login link
**Auth:** hashcash. Query param `email`. The hashcash subject **must** equal the
requested email. Emails a one-time magic link (30-min expiry, 1-min resend
backoff). `200` → empty.

> Currently the email is **printed to stdout**, not sent (see issue #12).

### `POST /new` — register
**Auth:** hashcash (subject must equal `body.email`).

Body — `UserRegistrationRequest`: `name_short`, `name_full`, `email`,
`username`, `password`. Creates the user and sends an email-verification link.
`200` → empty.

> The "email already in use" branch currently returns a malformed response
> instead of a 400 — see issue #13.

### `GET /hashcash` — proof-of-work config
**Auth:** none. `200` → `HashcashConfig` (`version`, `nonces`, `difficulty`,
`time`). The client uses this to solve the `X-Hashcash` header.

---

## Homes — `/api/homes/v1/`

All endpoints require a **session key**. Users only ever see homes they are a
member of.

### `GET /homes` — list my homes
`200` → `list[HomeSchema]` (each with `id`, `name`, `description`, and
`memberships` → `[{ score, user }]`).

### `POST /homes` — create a home
Body — `CreateHomeRequest` (`name` 3–100 chars, `description` ≤ 1000). The
creator becomes the first member. Limited to **5 memberships per user** (403
beyond). `409` if the name is taken.

### `PATCH /homes/{home_id}` — update a home
Body — `UpdateHomeRequest` (optional `name`, `description`). `403` if not a
member.

### `GET /holidays` — list my holidays
Those that haven't ended yet (a holiday runs to the end of its last day),
earliest first; `?include_past=true` returns all of them.
`200` → `list[HolidaySchema]` (includes the nested membership + home).

### `POST /holidays/` — create a holiday
Body — `CreateHolidaySchema` (`home_id`, `from_date`, `to_date`, `note`).
Validates `from_date ≤ to_date` and that it ends in the future. `200` → empty.

### `PATCH /holidays/{holiday_id}` — edit a holiday
Body — `UpdateHolidaySchema` (`from_date`, `to_date`, `note`). Same validation
as creating one. Only the owning user's holidays; `404` otherwise.
`200` → `HolidaySchema`.

### `DELETE /holidays/{holiday_id}` — delete a holiday
Only the owning user's holidays. `404` otherwise. `200` → empty.

---

## Regular jobs — `/api/regular_jobs/v1/`

All endpoints require a **session key** and are scoped to the caller's homes.

### `GET /definitions` — list job definitions
Query params: `home_id` (optional filter), `assignee` (`"*"` for any assignee,
or a user id).
`200` → `list[RegularJobDefinitionSchema]` (the full job incl. `rules`,
computed `bonus`, and `next_assigned_*` scheduling fields).

> The `assignee` filter currently references a non-existent field and will raise
> `FieldError` — see issue #13.

### `POST /definitions` — create a job definition
Query param `home_id`. Body — `CreateRegularJobDefinitionRequest` (`name` 5–100,
`description` ≤ 1000, `value_min`/`value_max`/`value_default`). Limited to **500
jobs per home**. The first assignment is computed via `adjust()`. `200` (no body).

### `PATCH /definitions/{definition_id}` — edit a job definition
Body — `RegularJobDefinitionEditSchema` (all fields optional: `name`,
`description`, `open_for_days`, `criticality`, `rules`, value fields). If `rules`
change, the assignment is recomputed. `200` → `RegularJobDefinitionSchema`.

### `GET /definitions/{definition_id}/instances` — completion history
`200` → `list[RegularJobInstanceSchema]` (each completion: who, value, and the
assigned/start/due/completed timestamps).

### `POST /definitions/{definition_id}/instances` — claim / complete a job
Body — `CreateRegularJobInstanceRequest`:
- `value` (optional): clamped to the job's min/max.
- `assigned_at` (optional, but the app always sends it): the job's
  `next_assigned_date` as the client last saw it, naming the occurrence being
  completed. Every claim, snooze or reassignment sets a new one, so if it no
  longer matches, that occurrence was already dealt with and the claim is
  refused with **`409`** and nothing changes. This is what stops a double tap or
  a retry from counting twice. (The due date can't do this: a daily job done
  early is due "tomorrow" again.) The job row is locked while this is checked.

Awards points (plus overdue bonus if a non-assignee rescues a late job),
re-normalises scores, records the instance, and re-assigns the next
occurrence.
`200` → `ClaimResponse`:
```jsonc
{
  "value": 12,                 // points awarded
  "statistics": { … },         // HomeStatistics (per-member daily scores, 30d)
  "result": { … },             // RuleComputeResult for the new assignment
  "definition": { … }          // the job now: next assignee and dates
}
```

### `GET /definitions/{definition_id}/snooze` — snooze options
`200` → `list[SnoozeOption]` (`{ label, date }`) — suggested later dates.


### `POST /definitions/{definition_id}/snooze` — snooze to a date
Query params `new_date`, and optionally `assigned_at` (as for claims: `409` if
that occurrence has since been completed or moved). Reschedules the current
assignment's due/start dates. `200` → `RegularJobDefinitionSchema`, the job now.

### `GET /statistics` — points per member per day, for one home
Query params `home_id` and `days` (1–365, default 30). `404` if you aren't a
member. `200` → `HomeStatistics`: `dates` (one per day, oldest first) and, per
member, `id`, `name`, `name_short`, `relative_score` (the fairness balance) and
`daily_scores` (points earned each day).

### `GET /instances` — recent completions across your homes
Newest first. Optional query params: `home_id`, `user_id`, `since` (datetime),
`before` (datetime; pass the last item's `completed_at` for the next page) and
`limit` (1–100, default 30). `200` → `list[JobCompletionSchema]`: `id`,
`job_id`, `job_name`, `home_id`, `value` (points, including any overdue bonus),
`completed_by_id`, `completed_at`, `due_at`, and `on_time` (completed by the end
of its due date; `null` if it had none).

### `GET /upkeep` — how well a home is keeping up
Query params `home_id` and `days` (7–365, default 56). `404` if you aren't a
member. `200` → `HomeUpkeep`:
- `ideal_per_week`: the points a week of every job done on schedule would earn.
  Each job's rules are simulated over two years to get its average occurrences
  per week (from the average gap between scheduled dates), times its
  `value_default`. Jobs without rules count for nothing.
- `dates` / `daily_points`: points actually earned each day, **without**
  overdue bonuses (`value - bonus`), oldest first.
- `daily_jobs` / `daily_on_time` / `daily_late`: jobs completed each day, and
  how many of those met or missed their due date (by the same test as
  `on_time` in `GET /instances`; jobs with no due date are in neither).
- `jobs`: each job's `per_week`, `value` and `points_per_week`, largest first.

The ideal uses today's jobs and rules, so older weeks are compared against the
current schedule.

---

## Admin

The Django admin is mounted at **`/krimba/`** (not `/admin/`). All models
(`DmvUser`, `Home`, `Membership`, `Holiday`, `RegularJobDefinition`,
`RegularJobInstance`) are registered. It requires a staff/superuser account
(`manage.py createsuperuser`).
