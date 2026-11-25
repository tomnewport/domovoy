# Architecture

This document explains how Domovoy is put together: the domain model, the
assignment algorithm, the rules engine, the authentication scheme, and how the
pieces are deployed. It is aimed at someone picking the codebase up for the first
time. For a higher-level overview see the [README](../README.md).

## System overview

```
┌────────────────────┐        HTTPS         ┌──────────────────────────┐
│  Vue 3 SPA          │  ───────────────▶   │  django-ninja API         │
│  (domovoy_app)      │  ◀───────────────   │  (domovoy/)               │
│  Vuetify + Pinia    │   x-session-key      │  Django ORM → SQLite      │
└────────────────────┘                      └──────────────────────────┘
        │  build-time                                 │
        │  openapi-typescript                         │  SMTP (email links)
        ▼                                             ▼
  typed API client                              mail server
```

The frontend is a static SPA. It talks to the backend exclusively through the
django-ninja API under `/api/`, using a **typed client generated from the
backend's OpenAPI schema** (`npm run domovoy-types`). Authentication state is a
session key passed in the `x-session-key` header.

## Backend layout

The Django project lives in `domovoy/` and is split into three apps plus shared
`security/` and `utils/` packages.

### `dmv_user` — identity & login

- **`DmvUser`** extends Django's `AbstractUser` with `name_short` / `name_full`,
  `email_verified`, and the fields backing email magic-link login
  (`email_link_hash`, `email_link_sent`).
- Login is **passwordless by default**: `send_email_code()` emails a one-time
  link; `verify_email_code()` checks it (30-minute expiry, 1-minute resend
  backoff). A password factor is also supported.
- The API (`api/v1/api.py`) exposes registration, `email_code`, session
  create/delete, and the hashcash config endpoint.

### `dmv_home` — households

- **`Home`** — a household. Holds the gamification knobs: `base_score`,
  `d6_cost` / `d6_min` / `d6_max` (dice economy), and `overdue_bounty`.
- **`Membership`** — a user's place in a home, carrying their running `score`.
  `filter_available_dates()` filters a stream of candidate dates against the
  member's holidays.
- **`Holiday`** — a date range during which a member is unavailable.

### `regular_job` — chores, scheduling & scoring

This is the heart of the app.

- **`RegularJobDefinition`** — a recurring chore. Stores its `rules` (JSON),
  point values, `criticality`, `open_for_days`, and the *currently scheduled*
  assignment (`next_assigned_to` / `next_assigned_*` dates / `assignment_notes`).
- **`RegularJobInstance`** — an immutable record of one completion (who, when,
  how many points).
- **`rules.py`** — the Pydantic-based rules engine (see below).
- **`stats.py`** — builds per-member daily score histories for the dashboard.
- **`utils.py`** — `before_midnight()`, which converts a date into "23:59 local
  time, expressed as UTC" (currently hardcoded to `Europe/London`).

## The rules engine

A schedule is a `Ruleset`: an ordered list of rules, each of which is a generator
filter over an infinite stream of candidate dates produced by `generate_dates()`.

```
generate_dates(from)  →  rule₁.evaluate  →  rule₂.evaluate  →  …  →  due dates
```

- **`RuleDelay` (`delay:v1`)** — drops candidates until at least N
  days/weeks/months have passed since the start date.
- **`RuleCalendar` (`calendar:v1`)** — keeps only candidates whose
  `strftime(query)` is in the `match` list (e.g. weekday name, month name).

Rules are a Pydantic **discriminated union** keyed on the `rule` field, so new
versioned rule types (`delay:v2`, …) can be added without breaking stored data.
`Ruleset.find()` returns the lazy stream of valid due dates; callers take the
first one(s) they need.

## The assignment algorithm

`RegularJobDefinition.assign()` decides **who** does the job **next** and **when**.
It is a weighted lottery with deadline handling:

1. **Roll dice per member.** Each member rolls `clamp(score // d6_cost, d6_min,
   d6_max)` six-sided dice plus a random tiebreak. Lower scores → fewer points
   already → fewer dice → likelier to roll low → likelier to be picked. (When
   re-adjusting an existing assignment, the current assignee can roll a fixed `0`
   to stay put.)
2. **Sort** members by `sum(rolls) + tiebreak`; lowest wins.
3. **Resolve against availability and criticality:**
   - **Low** — the winner takes it on their first available date, even if that
     slips past the ideal date.
   - **Medium** — if the winner can't make the ideal date, pick whoever is
     available soonest.
   - **High** — *Price-is-Right* rule: across all members, choose the date that
     is as close as possible to the ideal date **without going over**, so the job
     lands before anyone's holiday.

`assign()` returns a `RuleComputeResult` (participants, rolls, ideal/selected
dates, a human-readable `remark`) which is also stored on the job as
`assignment_notes` for transparency in the UI.

### Completion & score normalisation

`claim()` runs inside a transaction when a job is completed:

1. Compute the awarded value (`validate_value` clamps to min/max) plus the
   overdue **bonus** if a non-assignee rescues a late job.
2. Add it to the completer's membership score.
3. **Re-normalise:** subtract the minimum score across the home from everyone, so
   the lowest member sits at 0, and add that minimum to the home's `base_score`.
   This keeps relative standings while preventing scores from growing unbounded.
4. Record a `RegularJobInstance` and re-assign the next occurrence.

> The normalisation and dice math are the subtlest parts of the codebase; their
> tests are in `domovoy/apps/regular_job/tests.py`.

## Authentication & abuse protection

Two custom django-ninja security backends live in `security/`:

- **`SessionHeader`** (`x-session-key`) — loads a Django session by key and
  resolves it to a verified user. Used to protect all the home/job endpoints.
- **`Hashcash`** (`X-Hashcash`) — a [hashcash](https://en.wikipedia.org/wiki/Hashcash)
  proof-of-work gate on the *unauthenticated* endpoints (registration, requesting
  a login email). The client fetches a server-signed nonce + difficulty from
  `GET /api/users/v1/hashcash`, grinds a header whose SHA-256 has enough trailing
  zero bits, and submits it. Nonces are derived from the day + `SECRET_KEY` and
  are valid for ~1 hour, so the work can't be precomputed or replayed cheaply.

## Frontend

The SPA in `domovoy_app/` is a standard Vite + Vue 3 + Vuetify setup. Notable
pieces:

- `src/services/domovoy/` — the API layer. `schema.d.ts` is **generated** from
  the backend OpenAPI document; `base.ts` wraps `openapi-fetch` with the session
  header; per-domain modules (`homesV1.ts`, `usersV1.ts`) expose typed calls.
- `src/stores/` — Pinia stores for session, homes, jobs, and the hashcash config.
- `src/utils/hashcash.ts` — the client-side proof-of-work solver.

## Deployment

[`DEPLOY_GCP.md`](DEPLOY_GCP.md) has the details. GCP project
`domovoy-tdnsh`, `europe-west2`. A push to `main` deploys prod
(`domovoy.tdn.sh`), resets dev's Neon branch from prod's, and deploys `main`
to dev (`dom-dev.tdn.sh`); a manual run deploys any branch to dev. Each
deploy (`.github/workflows/deploy-gcp.yml`, called from `ci.yml` once the
checks pass):

- builds the image into Artifact Registry and deploys it by digest;
- runs `migrate` as a Cloud Run job against Neon Postgres (AWS eu-west-2, branches `production` and `dev`) over
  the direct URL;
- deploys the API to Cloud Run, which scales to zero, has at most 2 instances,
  and uses the pooled Neon URL;
- deploys the SPA to Firebase Hosting, which rewrites `/api`, `/api-static` and
  `/krimba` to Cloud Run on the same origin.

CI authenticates with Workload Identity Federation, with per-environment
deployer and runtime service accounts. Secrets live in Secret Manager, and
GitHub holds only non-secret repository variables (no GitHub Environments,
which private repos on GitHub Free may lack). Because Firebase forwards
only the `__session` cookie, the GCP config renames the session cookie and keeps
CSRF state in the session. The SPA's `x-session-key` header auth is unaffected.
Each environment's deploys are serialised by a per-environment concurrency group.

`tdn.sh` DNS is in Cloud DNS (project `tdnsh-dns`). Until 2026-11-25 the app
ran on a single VPS with an SQLite file. The data moved to Neon at the cutover.
