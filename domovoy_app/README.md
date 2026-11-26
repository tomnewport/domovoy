# Domovoy frontend (`domovoy_app`)

The user-facing single-page app for [Domovoy](../README.md) — a mobile-first PWA
built with **Vite + Vue 3** (Composition API), **Vuetify 4**, **Pinia**, and
**vue-router**.

> 📖 Full frontend documentation (API client, stores, routing, components,
> theming) lives in [`../docs/FRONTEND.md`](../docs/FRONTEND.md).

## Quickstart

Requires **Node 26** (`.nvmrc`). The backend should be running first (see the
[root README](../README.md)).

```sh
nvm use
npm install
npm run domovoy-types   # generate the typed API client (no server needed)
npm run dev             # start the Vite dev server
```

Re-run `npm run domovoy-types` whenever the backend API schema changes. It runs
`scripts/generate-api-types.sh`, which exports the OpenAPI schema straight from
Django (using `domovoy/.env`, no server needed) and regenerates
`src/services/domovoy/schema.d.ts` (do not edit that file by hand). CI fails if
the committed file is stale.

## Scripts

| Script | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server with hot reload |
| `npm run build` | Type-check (`vue-tsc`) + production build |
| `npm run preview` | Preview a production build locally |
| `npm run lint` | ESLint with `--fix` |
| `npm run format` | Prettier over `src/` |
| `npm run domovoy-types` | Regenerate the typed API client |

## Recommended IDE

[VS Code](https://code.visualstudio.com/) + the
[Vue (Volar)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)
extension (disable Vetur). Type-checking for `.vue` files uses `vue-tsc` in place
of `tsc`. See the [Vite config reference](https://vitejs.dev/config/) for build
customisation.
