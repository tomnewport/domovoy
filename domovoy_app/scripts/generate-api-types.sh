#!/usr/bin/env bash
# Regenerate src/services/domovoy/schema.d.ts from the backend's OpenAPI
# schema. The schema is exported straight from Django, so no server needs to
# be running. `npm run domovoy-types` runs this, and so does CI, which fails if
# the committed file differs from the result.
#
# The backend settings must load: locally from domovoy/.env, in CI from the
# job's dummy domovoy_* variables.
set -euo pipefail

app="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

(
  cd "$app/../domovoy"
  poetry -P .. run python manage.py shell -c "
from django.core.management import call_command
from ninja.management.commands.export_openapi_schema import Command
call_command(Command(), output='$tmp/openapi.json')"
)

cd "$app"
npx openapi-typescript "$tmp/openapi.json" -o src/services/domovoy/schema.d.ts
