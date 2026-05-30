#!/usr/bin/env python3
"""PostgreSQL logical-backup manager for Value Fabric.

Performs pg_dump-based logical backups, optionally encrypts the result with
a Fernet symmetric key, and uploads to a local path, S3, or GCS.

Usage:
    python3 scripts/ops/postgres_backup.py --help

Environment variables (all required in production):
    POSTGRES_HOST          – host (default: localhost)
    POSTGRES_PORT          – port (default: 5432)
    POSTGRES_USER          – database user
    POSTGRES_PASSWORD      – database password (passed via PGPASSWORD env var)
    POSTGRES_DB            – database name
    BACKUP_STORAGE         – one of: local, s3, gcs  (default: local)
    BACKUP_DEST            – local directory path OR bucket name
    BACKUP_PREFIX          – object/path prefix inside bucket or local dir
                             (default: "postgres-backups")
    BACKUP_ENCRYPTION_KEY  – base64-urlsafe 32-byte Fernet key; when set the
                             dump is encrypted before upload.  Generate with:
                               python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    BACKUP_RETENTION_DAYS  – delete backups older than N days (default: 30)
    AWS_ACCESS_KEY_ID      – (S3) standard AWS credential env var
    AWS_SECRET_ACCESS_KEY  – (S3) standard AWS credential env var
    AWS_DEFAULT_REGION     – (S3) standard AWS region env var
    GOOGLE_APPLICATION_CREDENTIALS – (GCS) path to service account JSON
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger("postgres_backup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ---------------------------------------------------------------------------
# Storage abstraction
# ---------------------------------------------------------------------------

@runtime_checkable
class BackupStorage(Protocol):
    """Minimal storage interface for backup uploads and housekeeping."""

    def upload(self, local_path: Path, remote_key: str) -> None: ...
    def list_backups(self, prefix: str) -> list[dict]: ...
    def delete(self, remote_key: str) -> None: ...


class LocalStorage:
    """Write backups to a local directory."""

    def __init__(self, dest_dir: str) -> None:
        self.dest = Path(dest_dir)
        self.dest.mkdir(parents=True, exist_ok=True)

    def upload(self, local_path: Path, remote_key: str) -> None:
        target = self.dest / remote_key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, target)
        logger.info("Backup stored locally at %s", target)

    def list_backups(self, prefix: str) -> list[dict]:
        results = []
        for p in self.dest.rglob("*.gz"):
            results.append({"key": str(p.relative_to(self.dest)), "last_modified": datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)})
        return results

    def delete(self, remote_key: str) -> None:
        target = self.dest / remote_key
        if target.exists():
            target.unlink()
            logger.info("Deleted old backup %s", target)


class S3Storage:
    """Upload backups to AWS S3."""

    def __init__(self, bucket: str, prefix: str) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 storage. Install with: pip install boto3") from exc
        self._s3 = boto3.client("s3")
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")

    def _key(self, remote_key: str) -> str:
        return f"{self.prefix}/{remote_key}" if self.prefix else remote_key

    def upload(self, local_path: Path, remote_key: str) -> None:
        key = self._key(remote_key)
        self._s3.upload_file(str(local_path), self.bucket, key)
        logger.info("Uploaded backup to s3://%s/%s", self.bucket, key)

    def list_backups(self, prefix: str) -> list[dict]:
        full_prefix = self._key(prefix)
        paginator = self._s3.get_paginator("list_objects_v2")
        results = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=full_prefix):
            for obj in page.get("Contents", []):
                results.append({"key": obj["Key"], "last_modified": obj["LastModified"]})
        return results

    def delete(self, remote_key: str) -> None:
        key = self._key(remote_key)
        self._s3.delete_object(Bucket=self.bucket, Key=key)
        logger.info("Deleted old S3 backup %s", key)


class GCSStorage:
    """Upload backups to Google Cloud Storage."""

    def __init__(self, bucket: str, prefix: str) -> None:
        try:
            from google.cloud import storage as gcs
        except ImportError as exc:
            raise RuntimeError("google-cloud-storage is required for GCS storage. Install with: pip install google-cloud-storage") from exc
        self._client = gcs.Client()
        self._bucket = self._client.bucket(bucket)
        self.prefix = prefix.rstrip("/")

    def _key(self, remote_key: str) -> str:
        return f"{self.prefix}/{remote_key}" if self.prefix else remote_key

    def upload(self, local_path: Path, remote_key: str) -> None:
        blob = self._bucket.blob(self._key(remote_key))
        blob.upload_from_filename(str(local_path))
        logger.info("Uploaded backup to gs://%s/%s", self._bucket.name, self._key(remote_key))

    def list_backups(self, prefix: str) -> list[dict]:
        full_prefix = self._key(prefix)
        results = []
        for blob in self._bucket.list_blobs(prefix=full_prefix):
            results.append({"key": blob.name, "last_modified": blob.updated})
        return results

    def delete(self, remote_key: str) -> None:
        blob = self._bucket.blob(self._key(remote_key))
        blob.delete()
        logger.info("Deleted old GCS backup %s", self._key(remote_key))


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def _get_fernet():
    """Return a Fernet instance if BACKUP_ENCRYPTION_KEY is set."""
    key = os.environ.get("BACKUP_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError(f"BACKUP_ENCRYPTION_KEY is set but invalid: {exc}") from exc


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# pg_dump / psql wrappers
# ---------------------------------------------------------------------------

_POSTGRES_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_identifier(identifier: str) -> str:
    """Return a safely quoted PostgreSQL identifier for database DDL."""
    if not _POSTGRES_IDENTIFIER_RE.fullmatch(identifier):
        raise RuntimeError(f"Unsafe PostgreSQL identifier: {identifier!r}")
    return f'"{identifier}"'


def _sql_literal(value: str) -> str:
    """Return a single-quoted PostgreSQL literal."""
    return "'" + value.replace("'", "''") + "'"


def _pg_dump(host: str, port: str, user: str, dbname: str, out_path: Path) -> None:
    """Run pg_dump and write a gzipped plain-text dump to *out_path*."""
    cmd = [
        "pg_dump",
        "--no-password",
        "--format=plain",
        f"--host={host}",
        f"--port={port}",
        f"--username={user}",
        dbname,
    ]
    env = os.environ.copy()
    pg_password = os.environ.get("POSTGRES_PASSWORD", "")
    if pg_password:
        env["PGPASSWORD"] = pg_password

    logger.info("Running pg_dump for database '%s' on %s:%s", dbname, host, port)

    with gzip.open(out_path, "wb") as gz_fh:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            raise RuntimeError(f"pg_dump failed (exit {result.returncode}): {stderr}")
        gz_fh.write(result.stdout)

    logger.info("pg_dump succeeded, %d bytes written (gzipped)", out_path.stat().st_size)


def _psql_restore(
    host: str,
    port: str,
    user: str,
    dbname: str,
    dump_path: Path,
    *,
    clean: bool = False,
) -> None:
    """Restore a gzipped plain-text pg_dump into *dbname* with psql."""
    if clean:
        quoted_dbname = _quote_identifier(dbname)
        dbname_literal = _sql_literal(dbname)
        admin_base_cmd = [
            "psql",
            "--no-password",
            f"--host={host}",
            f"--port={port}",
            f"--username={user}",
            "--dbname=postgres",
            "--set=ON_ERROR_STOP=1",
            "--command",
        ]
        _run_pg_command(
            admin_base_cmd
            + [
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                f"WHERE datname = {dbname_literal} AND pid <> pg_backend_pid();"
            ]
        )
        _run_pg_command(admin_base_cmd + [f"DROP DATABASE IF EXISTS {quoted_dbname};"])
        _run_pg_command(admin_base_cmd + [f"CREATE DATABASE {quoted_dbname};"])

    cmd = [
        "psql",
        "--no-password",
        f"--host={host}",
        f"--port={port}",
        f"--username={user}",
        "--set=ON_ERROR_STOP=1",
        "--dbname",
        dbname,
    ]
    env = os.environ.copy()
    pg_password = os.environ.get("POSTGRES_PASSWORD", "")
    if pg_password:
        env["PGPASSWORD"] = pg_password

    logger.info("Restoring %s into database '%s' on %s:%s", dump_path, dbname, host, port)
    with gzip.open(dump_path, "rb") as gz_fh:
        result = subprocess.run(
            cmd,
            stdin=gz_fh,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise RuntimeError(f"psql restore failed (exit {result.returncode}): {stderr}")
    logger.info("Restore completed into database '%s'", dbname)


def _run_pg_command(cmd: list[str]) -> None:
    env = os.environ.copy()
    pg_password = os.environ.get("POSTGRES_PASSWORD", "")
    if pg_password:
        env["PGPASSWORD"] = pg_password
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise RuntimeError(f"PostgreSQL command failed (exit {result.returncode}): {stderr}")


def restore_backup(input_path: Path, target_db: str, *, clean: bool = False) -> None:
    """Decrypt (if needed), verify checksum, and restore a logical backup."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "")
    if not user or not target_db:
        raise RuntimeError("POSTGRES_USER and target database are required for restore.")

    if not input_path.exists():
        raise RuntimeError(f"Backup file does not exist: {input_path}")

    logger.info("Input SHA-256 checksum: %s", _sha256(input_path))
    with tempfile.TemporaryDirectory(prefix="vf-pg-restore-") as tmpdir:
        restore_path = input_path
        if input_path.suffix == ".enc":
            fernet = _get_fernet()
            if not fernet:
                raise RuntimeError("BACKUP_ENCRYPTION_KEY is required to restore encrypted backups.")
            restore_path = Path(tmpdir) / input_path.with_suffix("").name
            restore_path.write_bytes(fernet.decrypt(input_path.read_bytes()))
            logger.info("Decrypted backup SHA-256 checksum: %s", _sha256(restore_path))

        _psql_restore(
            host=host,
            port=port,
            user=user,
            dbname=target_db,
            dump_path=restore_path,
            clean=clean,
        )


# ---------------------------------------------------------------------------
# Main backup logic
# ---------------------------------------------------------------------------

def run_backup() -> None:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "")
    dbname = os.environ.get("POSTGRES_DB", "")
    storage_type = os.environ.get("BACKUP_STORAGE", "local")
    dest = os.environ.get("BACKUP_DEST", "/tmp/postgres-backups")
    prefix = os.environ.get("BACKUP_PREFIX", "postgres-backups")
    retention_days = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))

    if not user or not dbname:
        raise RuntimeError("POSTGRES_USER and POSTGRES_DB environment variables are required.")

    fernet = _get_fernet()

    # Build storage backend
    if storage_type == "s3":
        storage: BackupStorage = S3Storage(bucket=dest, prefix=prefix)
    elif storage_type == "gcs":
        storage = GCSStorage(bucket=dest, prefix=prefix)
    else:
        storage = LocalStorage(dest_dir=dest)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"{timestamp}-{dbname}.sql.gz"
    if fernet:
        backup_name += ".enc"

    with tempfile.TemporaryDirectory(prefix="vf-pg-backup-") as tmpdir:
        raw_path = Path(tmpdir) / f"{timestamp}-{dbname}.sql.gz"
        final_path = raw_path

        _pg_dump(host=host, port=port, user=user, dbname=dbname, out_path=raw_path)

        if fernet:
            enc_path = Path(tmpdir) / backup_name
            enc_path.write_bytes(fernet.encrypt(raw_path.read_bytes()))
            final_path = enc_path
            logger.info("Backup encrypted with Fernet key")

        checksum = _sha256(final_path)
        logger.info("SHA-256 checksum: %s", checksum)

        remote_key = f"{timestamp}/{backup_name}"
        storage.upload(final_path, remote_key)

    # Retention enforcement
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    old_backups = [
        b for b in storage.list_backups(prefix="")
        if b["last_modified"] < cutoff
    ]
    if old_backups:
        logger.info("Purging %d backup(s) older than %d days", len(old_backups), retention_days)
        for backup in old_backups:
            storage.delete(backup["key"])

    logger.info("Backup complete: %s  checksum=%s", backup_name, checksum)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Value Fabric PostgreSQL backup manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print configuration and exit without running pg_dump or uploading",
    )
    parser.add_argument(
        "--restore",
        type=Path,
        help="Restore the given .sql.gz or .sql.gz.enc logical backup with psql",
    )
    parser.add_argument(
        "--target-db",
        help="Target database for --restore",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Drop and recreate --target-db before restoring",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("Dry-run mode.  Effective configuration:")
        for key in [
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_DB",
            "BACKUP_STORAGE", "BACKUP_DEST", "BACKUP_PREFIX",
            "BACKUP_RETENTION_DAYS",
        ]:
            val = os.environ.get(key, "<not set>")
            if key == "POSTGRES_PASSWORD":
                val = "***" if val else "<not set>"
            print(f"  {key}={val}")
        enc_set = bool(os.environ.get("BACKUP_ENCRYPTION_KEY", "").strip())
        print(f"  BACKUP_ENCRYPTION_KEY={'<set>' if enc_set else '<not set>'}")
        sys.exit(0)

    try:
        if args.restore:
            if not args.target_db:
                raise RuntimeError("--target-db is required with --restore")
            restore_backup(args.restore, args.target_db, clean=args.clean)
        else:
            run_backup()
    except Exception as exc:
        action = "Restore" if args.restore else "Backup"
        logger.error("%s failed: %s", action, exc)
        sys.exit(1)
