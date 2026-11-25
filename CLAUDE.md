# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this is

Domovoy is a household chore-sharing app: a **Django 6 + django-ninja** backend
(`domovoy/`) serving a typed REST API, and a **Vue 3 + Vuetify + Pinia** SPA
(`domovoy_app/`). See [`README.md`](README.md) for the product overview and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the internals fit together.

## Commands

Backend (from `domovoy/`, uses [uv](https://docs.astral.sh/uv/) >= 0.13.10 and
Python 3.14 from `.python-version`; uv finds the root `pyproject.toml` from the
subdirectory):

```sh
uv sync                                  # installs Python 3.14 if needed, and the locked deps
uv run python manage.py migrate
uv run python manage.py runserver        # serves /api/ and /api/docs
uv run python manage.py test             # discovers domovoy/apps/*/tests.py
uv run ruff check .                      # lint (ruff is a dev dependency)
```

Frontend (from `domovoy_app/`, Node 22):

```sh
npm install
npm run dev
npm run build          # type-check + vite build
npm run lint           # eslint --fix
npm run domovoy-types  # regenerate src/services/domovoy/schema.d.ts (no server needed)
```

## Conventions & gotchas

- The backend reads config from `domovoy/.env` via `environment.py`
  (pydantic-settings). All variables are prefixed `domovoy_`. Start from
  `domovoy/.env.example`; the README's Configuration table describes each one.
- There is one uv project: the root `pyproject.toml` + `uv.lock` (the
  `Dockerfile` and CI install from there too, with `--locked`). Change
  dependencies with `uv add` / `uv lock`, never by editing `uv.lock`. Don't add
  a `pyproject.toml` under `domovoy/`; uv would pick it up instead of the root
  one.
- The outer `domovoy/` directory is not a Python package. Don't add an
  `__init__.py` to it: test discovery would then look for `domovoy.domovoy`.
- The custom user model is `dmv_user.DmvUser` (`AUTH_USER_MODEL`). Always use
  `get_user_model()`.
- Frontend types are **generated** from the backend OpenAPI schema. After any API
  change, regenerate with `npm run domovoy-types` and commit it; CI fails if it's
  stale. It exports the schema from Django directly, so no server is needed.
- The Django admin lives at `/krimba/`, not `/admin/`.
- Email login links are currently **printed to stdout** (`utils/email.py`), not
  sent. Don't assume mail is delivered in dev.
- Use Pydantic v2 APIs only (`model_validate`, `model_dump`, `model_config`).
  The test runner (`domovoy/testing.py`) turns Pydantic v1 deprecation warnings
  into errors, so a `parse_obj` or `.dict()` call fails the test that reaches
  it, and a dedicated test fails on any of our models with a class-based
  `Config`.
- The riskiest logic — `RegularJobDefinition.assign`/`claim` and the rules engine
  — is covered by `domovoy/apps/regular_job/tests.py`. Change it together with
  its tests; CI runs the suite on SQLite and on Postgres.

## Working agreements

- Open issues for refactors, bugs, tests, and deployment changes rather than
  bundling unrelated changes into one PR.
- Keep new code at the same altitude and style as its neighbours.
