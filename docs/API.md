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

### `GET /holidays` — list my upcoming holidays
`200` → `list[HolidaySchema]` (includes the nested membership + home).

### `POST /holidays/` — create a holiday
Body — `CreateHolidaySchema` (`home_id`, `from_date`, `to_date`, `note`).
Validates `from_date ≤ to_date` and that it ends in the future. `200` → empty.

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
Body — `CreateRegularJobInstanceRequest` (`value` optional; clamped to the job's
min/max). Awards points (plus overdue bonus if a non-assignee rescues a late
job), re-normalises scores, records the instance, and re-assigns the next
occurrence.
`200` → `ClaimResponse`:
```jsonc
{
  "value": 12,                 // points awarded
  "statistics": { … },         // HomeStatistics (per-member daily scores, 30d)
  "result": { … }              // RuleComputeResult for the new assignment
}
```

### `GET /definitions/{definition_id}/snooze` — snooze options
`200` → `list[SnoozeOption]` (`{ label, date }`) — suggested later dates.

> `snooze_options()` currently mis-passes its date argument — see issue #13.

### `POST /definitions/{definition_id}/snooze` — snooze to a date
Query param `new_date`. Reschedules the current assignment's due/start dates.
`200` → empty.

---

## Admin

The Django admin is mounted at **`/krimba/`** (not `/admin/`). All models
(`DmvUser`, `Home`, `Membership`, `Holiday`, `RegularJobDefinition`,
`RegularJobInstance`) are registered. It requires a staff/superuser account
(`manage.py createsuperuser`).
