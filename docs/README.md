# Domovoy documentation

Reference documentation for the **current (as-is) state** of Domovoy. Start with
the [project README](../README.md) for the product overview and developer
quickstart, then dive into the area you need:

| Doc | What's in it |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System overview, backend layout, the rules engine, the assignment & scoring algorithm, auth/hashcash, and the deployment picture. |
| [DATA_MODEL.md](DATA_MODEL.md) | All six models, their fields and relationships, and key methods. |
| [API.md](API.md) | The full REST API: every endpoint, its auth mode, and request/response shapes. |
| [FRONTEND.md](FRONTEND.md) | The Vue 3 SPA: API client, Pinia stores, routing, components, theming. |
| [DEPLOYMENT_GCP.md](DEPLOYMENT_GCP.md) | Step-by-step guide to set up Google Cloud (Cloud Run + Neon + GitHub Actions) for deployment. |
| [../CLAUDE.md](../CLAUDE.md) | Commands, conventions, and gotchas for contributors/agents. |

## Live API docs

When the backend is running, Swagger UI is at `/api/docs` and the raw OpenAPI
schema at `/api/openapi.json` (the source of truth the frontend client is
generated from).

## Known gaps & roadmap

These docs describe the app as it actually behaves today, including a few quirks
and bugs, each linked to its tracking issue (testing, managed deployment,
Postgres, real email, hosted OAuth2 login / hashcash removal, and assorted
refactors). See the [repository issues](https://github.com/tomnewport/domovoy/issues)
for the current plan.
