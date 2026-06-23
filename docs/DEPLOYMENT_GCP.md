# GCP / cloud account setup

How to stand up the cloud side of Domovoy's deployment: **Cloud Run** (the
container) talking to a **Neon** Postgres database and **Auth0** for login, with
**GitHub Actions** deploying automatically using **no long-lived keys** (Workload
Identity Federation) and **no secrets in the repo** (they live in Secret Manager).

The infrastructure itself is defined as code with **Terraform** — see
[`deploy/terraform/README.md`](../deploy/terraform/README.md). This page covers
the one thing Terraform can't do for you: **creating the cloud account**. Do
this first, then follow the Terraform README.

---

## A. Create your Google Cloud account (first time only)

Skip this if you already have a Google Cloud account.

1. You need a **Google account** (any Gmail address). If you don't have one,
   create it first at <https://accounts.google.com/signup>.
2. Go to <https://cloud.google.com> and click **Get started for free** (or
   **Start free**).
3. Sign in with your Google account.
4. **Step 1 of the signup** — pick your country, agree to the terms, click
   **Continue**.
5. **Step 2 of the signup** — you'll be asked for a **credit/debit card**. This
   is only to verify you're a real person. You get **$300 of free credit for 90
   days**, and Google will **not** charge you automatically — your account stays
   on "free trial" until you *manually* choose to upgrade to paid. Enter the card
   and click **Start my free trial**.
6. You'll land in the **Google Cloud Console** at
   <https://console.cloud.google.com>, usually with a default project called
   "My First Project". You can ignore it — Terraform's bootstrap creates a
   dedicated project.

> **Will this cost me money?** Not within the free trial, and not within Cloud
> Run's separate "Always Free" monthly allowance, which a small app like this
> stays inside. After the trial ends (90 days or $300 used), services pause
> unless you upgrade — they won't silently start billing you.

✅ **Checkpoint:** <https://console.cloud.google.com> loads and shows a project
picker at the top.

---

## B. You'll also need Neon and Auth0 accounts

- **Neon** (managed Postgres) — sign up at <https://neon.tech>. Free tier.
- **Auth0** (login) — sign up at <https://auth0.com>. Free tier.

You don't need to configure anything in them by hand beyond creating an API
key / a management application — the Terraform README walks through exactly what
to grab from each.

---

## C. Provision everything with Terraform

Everything else — the project wiring, Artifact Registry, service accounts, IAM,
Workload Identity Federation, secrets, the Cloud Run service, the Neon database,
and the Auth0 API + app — is created by Terraform.

➡️ **Follow [`deploy/terraform/README.md`](../deploy/terraform/README.md).**

It runs entirely in **Cloud Shell** (nothing to install) and ends by printing the
GitHub repository variables the deploy workflow needs. Once those are set, a push
to `main` builds, deploys, and migrates automatically.
