#!/usr/bin/env python3
"""Reset Neon's dev branch to production's current data ("reset from parent").

Run by CI after each production deploy (see docs/DEPLOY_GCP.md), so the dev
environment starts from a fresh copy of prod. Anything written to dev since
the last reset is discarded.

Environment:
  NEON_API_KEY       API key (CI reads it from Secret Manager).
  NEON_PROJECT_ID    The Neon project, e.g. "ancient-base-12345678".
  NEON_DEV_BRANCH    Branch to reset (default "dev").
  NEON_PROD_BRANCH   Its parent, the source of the data (default "production").
  NEON_API_URL       Override the API base URL (tests only).

Stdlib only, so CI needs nothing installed. The endpoint and fields follow
Neon's API (`POST /projects/{project_id}/branches/{branch_id}/restore` with
`source_branch_id` and no LSN/timestamp restores to the source's head).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = os.environ.get("NEON_API_URL", "https://console.neon.tech/api/v2").rstrip("/")
POLL_SECONDS = float(os.environ.get("NEON_POLL_SECONDS", "3"))
TIMEOUT_SECONDS = 15 * 60
DONE = {"finished", "skipped"}
FAILED = {"failed", "error", "cancelled", "cancelling"}


class NeonError(Exception):
    pass


def call(method, path, body=None):
    """One API call; retries while Neon reports another operation running."""
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(20):
        request = urllib.request.Request(
            f"{API_URL}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {os.environ['NEON_API_KEY']}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            # 423 Locked: the branch has an operation in progress (e.g. the
            # compute starting up). Wait for it rather than failing the deploy.
            if exc.code == 423 and attempt < 19:
                time.sleep(POLL_SECONDS * 2)
                continue
            detail = exc.read().decode(errors="replace")[:500]
            raise NeonError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
    raise NeonError(f"{method} {path} stayed locked")


def find_branches(project, dev_name, prod_name):
    branches = call("GET", f"/projects/{project}/branches")["branches"]
    by_name = {branch["name"]: branch for branch in branches}
    dev, prod = by_name.get(dev_name), by_name.get(prod_name)
    if not prod:
        raise NeonError(f"No branch named {prod_name!r} in project {project}")
    if not dev:
        raise NeonError(f"No branch named {dev_name!r} in project {project}")
    # Guards: this must only ever overwrite a disposable child of prod.
    if dev["id"] == prod["id"]:
        raise NeonError("The dev and prod branch names resolve to the same branch")
    if dev.get("default") or dev.get("primary") or dev.get("protected"):
        raise NeonError(f"Refusing to reset {dev_name!r}: it is a default or protected branch")
    if dev.get("parent_id") != prod["id"]:
        raise NeonError(f"Refusing to reset {dev_name!r}: its parent is not {prod_name!r}")
    return dev, prod


def wait_for(project, operation_ids):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    pending = list(operation_ids)
    while pending:
        if time.monotonic() > deadline:
            raise NeonError(f"Timed out waiting for operations {pending}")
        still_pending = []
        for operation_id in pending:
            operation = call("GET", f"/projects/{project}/operations/{operation_id}")["operation"]
            status = operation["status"]
            if status in FAILED:
                raise NeonError(
                    f"Operation {operation_id} ({operation.get('action')}) {status}: "
                    f"{operation.get('error', '')}"
                )
            if status not in DONE:
                still_pending.append(operation_id)
        pending = still_pending
        if pending:
            time.sleep(POLL_SECONDS)


def main():
    for name in ("NEON_API_KEY", "NEON_PROJECT_ID"):
        if not os.environ.get(name):
            raise NeonError(f"{name} is not set (see docs/DEPLOY_GCP.md)")
    project = os.environ["NEON_PROJECT_ID"]
    dev_name = os.environ.get("NEON_DEV_BRANCH", "dev")
    prod_name = os.environ.get("NEON_PROD_BRANCH", "production")

    dev, prod = find_branches(project, dev_name, prod_name)
    print(f"Resetting {dev_name} ({dev['id']}) to the head of {prod_name} ({prod['id']})")
    result = call(
        "POST",
        f"/projects/{project}/branches/{dev['id']}/restore",
        {"source_branch_id": prod["id"]},
    )
    operation_ids = [operation["id"] for operation in result.get("operations", [])]
    wait_for(project, operation_ids)
    print(f"{dev_name} now matches {prod_name} ({len(operation_ids)} operations finished)")


if __name__ == "__main__":
    try:
        main()
    except NeonError as exc:
        print(f"::error::Dev database reset failed: {exc}", file=sys.stderr)
        sys.exit(1)
