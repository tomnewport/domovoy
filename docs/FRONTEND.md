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

## Routing (`src/router/index.ts`)

History-mode routes. Most carry a `meta.bottomNav` index for the bottom menu.

| Path | View | Purpose |
| --- | --- | --- |
| `/`, `/tasks` | `TasksView` | The user's task list (home) |
| `/tasks/:jobId/edit` | `TasksView` | Edit a task inline |
| `/homes` | `HomesView` | List of homes |
| `/homes/:homeId` | `HomeDetailView` | A single home |
| `/homes/:homeId/jobs` | `HomeJobsView` | Jobs in a home |
| `/homes/:homeId/jobs/:jobId` | `HomeJobsView` | A single job |
| `/profile` | `ProfileView` | Progress, activity feed and holidays (tabs; `?tab=activity` / `?tab=holidays`) |
| `/reports` | `TasksView` | Reports tab |
| `/register` | `RegisterView` | Sign up |
| `/auth_link/:emailB64/:emailCode` | `AuthLinkLogin` | Magic-link landing page |
| `/auth_link/error` | `AuthLinkError` | Magic-link failure page |

## Components (`src/components/`)

Grouped by domain:

- **`auth/`** — `Login`, `Register`, `Logout`, `SendEmailLink`, `AuthWall`
  (gates authenticated content).
- **`homes/`** — `HomesList`, `CreateHome`, `HomeEditor`, `HomeJobList`.
- **`regular-jobs/`** — the largest group: `TodoList` / `TodoItem`,
  `JobEditor` / `CreateRegularJob`, `RulesEditor` (+ `RuleDelayEditor`,
  `RuleCalendarEditor`), `CompleteJobCard` / `QuickCompleteJob`,
  `CongratulateCard`, `JobAssignerResult`, `InstanceViewer`,
  `RegularJobDefinitionList`.
- **`profile/`** — `ProgressTiles`, `HomeStandings` (with `HomeUpkeep`: points
  done against the home's ideal, per period and per week), `ActivityFeed`, and the
  holiday planner (`HolidayPlanner`, `HolidayCalendar`, `HolidayForm`, with the
  data logic in `holidays.ts`). `progress.ts` holds the period maths (points,
  jobs, on-time rate, streak, standings).
- **`charts/`** — `PointsRaceChart` (several members on one pair of axes, with
  legend, crosshair tooltip and table view) and `Sparkline`. Member colours come
  from `utils/memberColors.ts`: a fixed categorical palette, assigned by user id
  so a person keeps their colour.
- **`common/`** — reusable display widgets registered globally in `main.ts`:
  `UserDisplay` (`DUserDisplay`), `DateDisplay` (`DDateDisplay`),
  `HomeDisplay` (`DHomeDisplay`), `EditableItem` (`DEditableItem`).
- **`layout/`** — `BottomMenu` (the mobile bottom navigation).

## Theming & app shell

`src/main.ts` registers Vuetify with a custom light/dark theme (purple primary,
cyan secondary; **dark by default**), registers the global `common/` display
components, and mounts `App.vue`. The app ships a web manifest and icons under
`public/` (installable as a PWA).
