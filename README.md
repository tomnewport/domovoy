# Domovoy

> A *domovoy* is a household spirit from Slavic folklore who looks after the home
> and its chores. This app does the same — fairly.

Domovoy is a self-hostable web app for **sharing recurring household chores**
between the members of a household. Instead of a static rota, it assigns each
job using a transparent, score-balancing algorithm that keeps the workload fair
over time, works around people's holidays, and nudges overdue tasks back into
view with bonus points.

- **Backend:** Django 5 + [django-ninja](https://django-ninja.dev/) REST API (SQLite today)
- **Frontend:** Vue 3 + Vuetify 3 + Pinia single-page app
- **Auth:** passwordless email magic-links (optional password), with
  [hashcash](https://en.wikipedia.org/wiki/Hashcash) proof-of-work to throttle abuse

---

## How it works

A household is a **Home**. Each member joins via a **Membership**, which carries
that member's running **score**. Members create **Regular Jobs** — recurring
chores such as "take out the bins" or "clean the bathroom".

Each Regular Job has:

- a **value** (points earned for doing it, with min/default/max),
- a **criticality** (Low / Medium / High — controls how strictly the deadline is honoured),
- a **ruleset** describing *when* it is next due (see [Rules](#rules) below), and
- an **open-for** window (how many days before the deadline it can be started).

When a job is completed, Domovoy:

1. awards the completer the job's value (plus an **overdue bounty** if someone
   other than the assignee picks up a late job),
2. **re-normalises** all members' scores so the lowest is zero (the home's
   `base_score` absorbs the offset), and
3. **re-assigns** the next occurrence.

### Assignment algorithm

Assignment is a weighted, dice-based lottery designed so that whoever has done
*less* recently is more likely to be picked, while still respecting deadlines and
holidays:

1. Each member rolls a number of d6 dice. More dice = more likely to roll low =
   more likely to be chosen. The dice count is derived from their score and the
   home's `d6_cost` / `d6_min` / `d6_max` settings.
2. The **lowest total** (with a random tiebreak) wins the job.
3. The member's first **available** date (skipping their holidays) is compared to
   the job's **ideal** date, and criticality decides what happens when they don't
   line up:
   - **Low** — assign anyway; the job can slip.
   - **Medium** — pick the member who can do it soonest.
   - **High** — "Price is Right" rules: schedule as close to the ideal date as
     possible *without going over*, before anyone's holiday.

The full logic lives in
[`apps/regular_job/models.py`](domovoy/domovoy/apps/regular_job/models.py)
(`RegularJobDefinition.assign` / `.claim`). See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a deeper walkthrough.

### Rules

A job's schedule is a **ruleset** — a list of composable rules evaluated in order
over a stream of candidate dates. Two rule types exist today:

| Rule | Meaning | Example |
| --- | --- | --- |
| `delay:v1` | At least N days/weeks/months since the job was last done | every 4 days |
| `calendar:v1` | The date matches a calendar predicate | only on Wednesdays, or only in summer months |

Rules are stored as JSON on the job and parsed/validated with Pydantic models in
[`apps/regular_job/rules.py`](domovoy/domovoy/apps/regular_job/rules.py).

---

## Documentation

Comprehensive reference docs for the current state of the app live in
[`docs/`](docs/README.md):

- [Architecture](docs/ARCHITECTURE.md) — system design, rules engine, assignment & scoring algorithm, auth.
- [Data model](docs/DATA_MODEL.md) — all models, fields, and relationships.
- [API reference](docs/API.md) — every endpoint, auth mode, and payload.
- [Frontend guide](docs/FRONTEND.md) — the Vue SPA's client, stores, routing, and components.
- [CLAUDE.md](CLAUDE.md) — contributor/agent conventions and gotchas.

---

## Repository layout

```
.
├── domovoy/                  # Django backend (Poetry project)
│   ├── domovoy/
│   │   ├── api.py            # NinjaAPI root, mounts the v1 routers
│   │   ├── settings.py       # Django settings (reads DmvSettings)
│   │   ├── environment.py    # Pydantic-settings env model (.env)
│   │   ├── security/         # hashcash proof-of-work + session-key auth
│   │   ├── utils/            # email + helpers
│   │   └── apps/
│   │       ├── dmv_user/     # custom user, email magic-link login
│   │       ├── dmv_home/     # Home, Membership, Holiday
│   │       └── regular_job/  # jobs, rules engine, assignment, stats
│   └── manage.py
├── domovoy_app/             # Vue 3 + Vuetify frontend (npm)
│   └── src/services/domovoy # API client generated from the OpenAPI schema
├── deploy/                  # docker-compose + nginx site config (current deploy)
├── Dockerfile              # backend image
└── .github/workflows/ci.yml # build + SSH deploy to a single VPS
```

---

## Developer quickstart

### Backend

```sh
cd domovoy
poetry install
# create domovoy/.env with the variables in "Configuration" below
poetry run python manage.py migrate
poetry run python manage.py runserver
```

The API is then served at `http://127.0.0.1:8000/api/` with interactive docs at
`http://127.0.0.1:8000/api/docs`. The Django admin is mounted at `/krimba/`.

> Email login links are currently **printed to the server console** rather than
> sent — see `utils/email.py` and the related issue.

### Frontend

```sh
cd domovoy_app
nvm use 22                     # Node 22
npm install
npm run domovoy-types          # regenerate the typed API client from the running backend
npm run dev
```

Re-run `npm run domovoy-types` whenever the backend schema changes — it pulls
`http://127.0.0.1:8000/api/openapi.json` and regenerates
`src/services/domovoy/schema.d.ts`.

---

## Configuration

The backend is configured via environment variables (loaded from `domovoy/.env`
by [`environment.py`](domovoy/domovoy/environment.py)):

| Variable | Required | Description |
| --- | --- | --- |
| `domovoy_server_secret_key` | ✅ | Django `SECRET_KEY` (also used to sign hashcash nonces) |
| `domovoy_django_debug` | | `true`/`false`, defaults to `false` |
| `domovoy_allowed_hosts` | | JSON list of allowed hostnames |
| `domovoy_allowed_cors_origins` | | JSON list of allowed CORS origins |
| `domovoy_csrf_trusted_origins` | | JSON list of origins trusted for CSRF on unsafe requests (e.g. the admin login) when served over HTTPS behind a proxy, e.g. `["https://domovoy.tdn.sh"]`. Defaults to `[]`, which is fine for local HTTP dev |
| `domovoy_frontend_root` | ✅ | Public base URL of the frontend (used in email links) |
| `domovoy_smtp_server` | ✅ | SMTP host |
| `domovoy_smtp_port` | ✅ | SMTP port |
| `domovoy_smtp_username` | ✅ | SMTP username |
| `domovoy_smtp_password` | ✅ | SMTP password |

---

## Deployment

The current production deployment is a GitHub Actions workflow
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) that, on push to `main`
or `dev`:

1. builds the Vue frontend and `scp`s the static files to a single VPS,
2. builds and pushes the backend Docker image to Docker Hub,
3. templates a `docker-compose.yml` + nginx site config and `scp`s them to the VPS,
4. SSHes in to `docker-compose pull && up -d` and run migrations.

This works but is tied to one hand-managed VM, an `scp`'d SQLite file, secrets
passed as env blobs, and no test gate. Migrating to a managed, dockerised host
with a managed database (no VM or DB to babysit) is tracked in the issues — see
the **Deployment** issue and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Status & roadmap

This is a personal/household project and a rewrite of an earlier app (see the
`migrate_from_glg` management command). Known gaps — automated tests, real email
delivery, a managed deployment, and a handful of correctness bugs — are tracked
as GitHub issues. Contributions and refactors against those issues are welcome.
