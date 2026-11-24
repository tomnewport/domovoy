# Database

The backend uses SQLite by default (`domovoy/data/db.sqlite3`, zero config).
Set `domovoy_database_url` to use Postgres instead, e.g. for Neon:

```sh
domovoy_database_url=postgresql://USER:PASSWORD@ep-xxx-pooler.REGION.aws.neon.tech/domovoy?sslmode=require
```

The URL is parsed by [`dj-database-url`](https://github.com/jazzband/dj-database-url)
in `settings.py`; query parameters such as `sslmode` are passed through to
psycopg. Use Neon's **pooled** host (`-pooler` in the hostname) for the running
app: connections are opened per request (`CONN_MAX_AGE = 0`) and PgBouncer
absorbs that cost. Use the **direct** host (no `-pooler`) for `migrate` and
`loaddata`.

## Moving existing data from SQLite to Postgres

There are no data migrations (`RunPython`) and no model signals, so a
`dumpdata`/`loaddata` round trip into a freshly migrated database is enough.

1. **Stop writes.** Stop the old container so the SQLite file is no longer
   changing, then copy `data/db.sqlite3` from the server into
   `domovoy/data/db.sqlite3` of a checkout at the **same commit** as production.

2. **Dump** (with `domovoy_database_url` unset, so it reads SQLite):

   ```sh
   cd domovoy
   poetry run python manage.py dumpdata \
     --natural-foreign \
     --exclude contenttypes --exclude auth.permission \
     --indent 2 -o domovoy-dump.json
   ```

   - `contenttypes` and `auth.permission` are recreated by `migrate` on the
     target; `--natural-foreign` makes admin log entries and any group/user
     permissions refer to them by name rather than by ID.
   - Do **not** pass `--natural-primary`. Primary keys must be preserved:
     `RegularJobDefinition.assignment_notes` (JSON) and session data store raw
     user IDs.
   - Sessions are kept on purpose, so users stay logged in (login links are not
     emailed yet).

3. **Check string lengths.** SQLite does not enforce `max_length`; Postgres
   does, and `loaddata` will fail on an over-long value. This should return no
   rows:

   ```sh
   sqlite3 data/db.sqlite3 "
     SELECT 'user', id FROM dmv_user_dmvuser WHERE length(name_short) > 16 OR length(name_full) > 128 OR length(email_link_hash) > 256
     UNION ALL SELECT 'home', id FROM dmv_home_home WHERE length(name) > 128
     UNION ALL SELECT 'holiday', id FROM dmv_home_holiday WHERE length(note) > 256
     UNION ALL SELECT 'job', id FROM regular_job_regularjobdefinition WHERE length(name) > 128;"
   ```

4. **Load** into an empty Postgres database (direct, non-pooled URL):

   ```sh
   export domovoy_database_url='postgresql://...direct-host.../domovoy?sslmode=require'
   poetry run python manage.py migrate
   poetry run python manage.py loaddata domovoy-dump.json
   ```

   `loaddata` resets the Postgres ID sequences, so new rows don't collide with
   imported IDs.

5. **Verify.** Compare row counts between the two databases, e.g. by running
   this with and without `domovoy_database_url` set:

   ```sh
   poetry run python manage.py shell -c "
   from django.apps import apps
   for m in apps.get_models(): print(m._meta.label, m.objects.count())"
   ```

   Then start the app against Postgres, log in and check that the job list and
   stats render.

Keep the SQLite file and the dump until the new deployment has run for a while.
Rolling back means pointing the old deployment at the old file again.
