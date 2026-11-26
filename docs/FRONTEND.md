# Frontend guide

The `domovoy_app/` directory is the user-facing single-page app. It is a
mobile-first PWA built with **Vite + Vue 3** (Composition API), **Vuetify 3**
for UI, **Pinia** for state, and **vue-router**. This describes the app **as it
is today**.

## Running it

```sh
cd domovoy_app
nvm use 22                 # Node 22
npm install
npm run domovoy-types      # regenerate the typed API client (no server needed)
npm run dev                # Vite dev server
```

Other scripts: `npm run build` (type-check + production build), `npm run lint`
(ESLint --fix), `npm run format` (Prettier), `npm run preview` (preview a build).

## How it talks to the backend

The API layer lives in `src/services/domovoy/`:

- **`schema.d.ts`** — **generated** from the backend's OpenAPI document by
  `npm run domovoy-types`, which exports the schema straight from Django
  (`scripts/generate-api-types.sh`; CI runs it too and fails if it's stale).
  Do not edit by hand; regenerate after any backend API change.
- **`index.ts`** — creates an [`openapi-fetch`](https://openapi-ts.dev/) `client`
  typed against `schema.d.ts`, choosing the API root from the current hostname
  (`localhost:8000` in dev, same-origin in prod).
- **`base.ts`** — `getHeaders()` attaches the `X-Session-Key` header from
  `localStorage`; `apiFetch()` is a lower-level fetch wrapper that can also set
  the `X-Hashcash` header.
- **`usersV1.ts` / `homesV1.ts`** — typed, per-domain call wrappers.

> The session key is held in `localStorage` and sent on every request — this and
> the hashcash flow change under the hosted-auth migration (issue #17).

## State (Pinia stores — `src/stores/`)

| Store | Responsibility |
| --- | --- |
| `session.ts` | Current session/user; `setSessionId`, `reloadSession`, `clearSession`. Persists the key to `localStorage`. |
| `homes.ts` | The user's homes and memberships. |
| `regular-job.ts` | Job definitions, instances, claim/snooze actions. |
| `hashcash-config.ts` | Caches the server's hashcash config for the PoW solver. |
| `manager.ts` | Shared loading/error helper (`useLoadingState`). |

`src/utils/hashcash.ts` is the client-side proof-of-work solver mirroring the
backend's `security/hashcash.py` (both retired under issue #17).

The stats maths lives in `src/utils/` too: `progress.ts` (a member's points,
jobs, on-time rate and streak per period, and a home's standings), `upkeep.ts`
(upkeep ratio and status, a home's job and on-time counts per period, and its
overdue jobs) and `tiles.ts` (comparisons with the period before, for
`StatTiles`).

## Routing (`src/router/index.ts`)

History-mode routes. Most carry a `meta.bottomNav` index for the bottom menu.

| Path | View | Purpose |
| --- | --- | --- |
| `/`, `/tasks` | `TasksView` | The user's task list (home) |
| `/tasks/:jobId/edit` | `TasksView` | Edit a task inline |
| `/homes` | `HomesView` | Your homes, each with this week's upkeep, overdue count and points |
| `/homes/:homeId` | `HomeDetailView` | A home's stats, activity and settings (tabs; `?tab=activity` / `?tab=settings`) |
| `/homes/:homeId/jobs` | `HomeJobsView` | Jobs in a home |
| `/homes/:homeId/jobs/:jobId` | `HomeJobsView` | A single job |
| `/profile` | `ProfileView` | Your own progress, activity and holidays (tabs; `?tab=activity` / `?tab=holidays`) |
| `/register` | `RegisterView` | Sign up |
| `/auth_link/:emailB64/:emailCode` | `AuthLinkLogin` | Magic-link landing page |
| `/auth_link/error` | `AuthLinkError` | Magic-link failure page |

## Components (`src/components/`)

Grouped by domain:

- **`auth/`** — `Login`, `Register`, `Logout`, `SendEmailLink`, `AuthWall`
  (gates authenticated content).
- **`homes/`** — how a home is doing, and its settings. `HomesList` shows a
  `HomeSummaryCard` per home; a home's page has `HomeOverview` (`HomeUpkeep`:
  points done against the home's ideal, per period and per week; job, on-time
  and overdue tiles; `HomeStandings`: who did what, with the points race) and
  `HomeSettings` (name, description, members, link to the jobs). Also
  `UpkeepMeter`, `CreateHome`, `HomeJobList`.
- **`activity/`** — `ActivityFeed`: completed jobs, newest first, for one
  person (Profile) or one home (with a chip per member to narrow it).
- **`regular-jobs/`** — the largest group: `TodoList` (Yours, Up for grabs,
  then folded Coming up and Not scheduled; or one list by date) /
  `TodoItem` (a job's name, when and whose, and its points; tapping it
  opens its `CompleteJobCard`),
  `JobEditor` / `CreateRegularJob`, `RulesEditor` (+ `RuleDelayEditor`,
  `RuleCalendarEditor`), `CompleteJobCard`, `CongratulateCard` (mounted in
  `App.vue`), `JobAssignerResult`, `InstanceViewer`,
  `RegularJobDefinitionList`.
- **`profile/`** — your own contribution: `ProgressTiles`, `HomeContributions`
  (your share of each home's points), `TopJobs`, and the holiday planner
  (`HolidayPlanner`, `HolidayCalendar`, `HolidayForm`, with the data logic in
  `holidays.ts`).
- **`charts/`** — `PointsRaceChart` (several members on one pair of axes, with
  legend, crosshair tooltip and table view) and `Sparkline`. Member colours come
  from `utils/memberColors.ts`: a fixed categorical palette, assigned by user id
  so a person keeps their colour.
- **`common/`** — reusable display widgets registered globally in `main.ts`:
  `UserDisplay` (`DUserDisplay`), `DateDisplay` (`DDateDisplay`),
  `HomeDisplay` (`DHomeDisplay`), `EditableItem` (`DEditableItem`); and
  `StatTiles`, the grid of headline numbers on Profile and a home's overview.
- **`layout/`** — `BottomMenu` (the mobile bottom navigation).

## Theming & app shell

`src/main.ts` registers Vuetify with a custom light/dark theme (purple primary,
cyan secondary; **dark by default**), registers the global `common/` display
components, and mounts `App.vue`. The app ships a web manifest and icons under
`public/` (installable as a PWA).
