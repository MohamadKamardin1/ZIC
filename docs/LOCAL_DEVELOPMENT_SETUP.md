# Local Development and SQLite Database Safety

## Purpose

The development environment uses SQLite by default through `DATABASE_URL=sqlite:///db.sqlite3`. The local database contains developer-specific data and must not be shared through Git. Each working copy must maintain its own `backend/db.sqlite3` file.

> **Important:** `backend/db.sqlite3` is local state. It is ignored by Git and is no longer part of the repository index. Pulling application code must not replace it.

## Safe pull procedure

Before pulling changes, create a database backup outside the repository. This protects the local data even if a migration or local command fails.

```bash
cd /path/to/ZIC
mkdir -p "$HOME/ZIC_sqlite_backups"
ts=$(date -u +%Y%m%dT%H%M%SZ)
cp -p backend/db.sqlite3 "$HOME/ZIC_sqlite_backups/db.sqlite3.$ts.bak"
```

Then update the code and apply migrations:

```bash
git pull --ff-only origin sultan
cd backend
python manage.py migrate
```

If the branch cannot be fast-forwarded, stop and resolve the Git situation before using a force reset. Do not resolve a database conflict by accepting a remote copy of `backend/db.sqlite3`; the database should not be tracked after this change.

## Confirm that the database is protected

From the repository root, the following command should report the ignore rule that protects the database:

```bash
git check-ignore -v backend/db.sqlite3
```

The database should not be listed by this command:

```bash
git ls-files backend/db.sqlite3
```

An empty result is expected. A local database may still appear in `git status` if it was previously tracked and the index has not yet received the database-removal commit. After pulling the safety fix, it should remain silent because it is ignored.

## Creating a manual backup

A backup should be made before migrations, branch switches that change schema, bulk imports, or destructive test-data operations.

```bash
cd /path/to/ZIC
mkdir -p "$HOME/ZIC_sqlite_backups"
ts=$(date -u +%Y%m%dT%H%M%SZ)
cp -p backend/db.sqlite3 "$HOME/ZIC_sqlite_backups/db.sqlite3.$ts.bak"
sha256sum "$HOME/ZIC_sqlite_backups/db.sqlite3.$ts.bak"
```

Keep backups outside the Git repository. Do not add the backup directory to a commit. If SQLite is running in WAL mode, stop the development server before copying the database so all pending writes are finalized; copy any `backend/db.sqlite3-wal` and `backend/db.sqlite3-shm` files alongside the database when they exist.

## Restoring a backup

Stop the Django development server before restoring a database. Preserve the current file first, then copy the selected backup into place:

```bash
cd /path/to/ZIC
mv backend/db.sqlite3 "$HOME/ZIC_sqlite_backups/db.sqlite3.before-restore.$(date -u +%Y%m%dT%H%M%SZ).bak"
cp -p "$HOME/ZIC_sqlite_backups/db.sqlite3.YYYYMMDDTHHMMSSZ.bak" backend/db.sqlite3
cd backend
python manage.py migrate
```

Replace `YYYYMMDDTHHMMSSZ` with the timestamp of the backup to restore. If the restored database is from an older schema, run migrations before starting the application.

## Recreating an empty development database

Only recreate the database when the existing local data is no longer needed or a backup has already been confirmed:

```bash
cd /path/to/ZIC/backend
mv db.sqlite3 "$HOME/ZIC_sqlite_backups/db.sqlite3.before-recreate.$(date -u +%Y%m%dT%H%M%SZ).bak"
python manage.py migrate
```

Do not use `git checkout -- backend/db.sqlite3`, `git restore backend/db.sqlite3`, or `git clean -fdx` as a way to repair application code. The first two commands can replace local data, and the last command can delete ignored files including the SQLite database.

## Team and deployment guidance

SQLite is suitable for local development and automated tests. It is not the shared persistence mechanism for production or for multiple developers. Shared environments should use their managed database and a separate backup policy. Schema changes belong in Django migration files; data that must exist in every environment belongs in explicit reference-data migrations or seed commands, not in a committed SQLite file.

The repository also ignores runtime logs, frontend `dist/` output, and TypeScript incremental build state. These are generated artifacts and should be regenerated locally rather than merged through Git.
