# SQLite migration repair for partner onboarding

## Symptom

A local SQLite database may fail while applying `partner_onboarding.0005_remove_partner_type_constraint` with:

```text
sqlite3.OperationalError: error in view onboarding_unified_record: no such table: main.onboarding_partner_application
```

## Cause

SQLite rebuilds tables for some constraint and field changes. A stale `onboarding_unified_record` view can reference `onboarding_partner_application` while that table is being renamed during the rebuild. SQLite validates the stale view during the rename and aborts the migration.

The same issue can occur at later migrations that alter `PartnerApplication`. The repaired migrations remove the view before the rebuild and recreate the canonical view immediately afterward. Migration `0008` and later remain the source of the canonical view definition.

## Recovery after pulling the fix

From the backend directory, pull the latest `sultan` branch and run:

```bash
python manage.py migrate
```

If the failed migration left a temporary SQLite lock, stop the local Django server and retry the command. Do not use `--fake`; the schema operation must actually run.

For a disposable development database with no data to preserve, the cleanest reset is:

```bash
cp db.sqlite3 db.sqlite3.backup
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

Back up any database containing useful local data before deleting it. Production or shared databases should not be deleted; restore from the appropriate database backup and run the normal migration process.

## Verification

The repair has been verified by applying the complete migration chain to a fresh SQLite database, by reproducing a stale `onboarding_unified_record` view before migration `0005`, and by running the full partner-onboarding test suite.
