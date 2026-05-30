#!/bin/bash
# Create least-privileged roles for the gate-db-readiness stack.
set -euo pipefail

READINESS_ROLE="${DB_READINESS_APP_USER:-vf_migrator}"
READINESS_PASSWORD="${DB_READINESS_APP_PASSWORD:-vf_migrator_readiness_secret}"
DATABASES="${POSTGRES_MULTIPLE_DATABASES:-${POSTGRES_DB:-postgres}}"

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB:-postgres}" <<-EOSQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${READINESS_ROLE}') THEN
      CREATE ROLE ${READINESS_ROLE} LOGIN PASSWORD '${READINESS_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;
  END
  \$\$;
EOSQL

for database in $(echo "${DATABASES}" | tr ',' ' '); do
  database="$(echo "${database}" | xargs)"
  if [ -z "${database}" ]; then
    continue
  fi
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${database}" <<-EOSQL
    ALTER DATABASE ${database} OWNER TO ${READINESS_ROLE};
    GRANT CONNECT, TEMPORARY ON DATABASE ${database} TO ${READINESS_ROLE};
    GRANT ALL PRIVILEGES ON SCHEMA public TO ${READINESS_ROLE};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${READINESS_ROLE};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${READINESS_ROLE};
EOSQL
done
