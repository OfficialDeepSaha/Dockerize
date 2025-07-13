#!/bin/bash
set -e

# Dynamically detect if postgres hostname is available (Docker Compose)
# or use host.docker.internal for standalone Docker
echo "Detecting PostgreSQL host..."
if nc -z postgres 5432 >/dev/null 2>&1; then
  export DB_HOST="postgres"
  export POSTGRES_HOST="postgres"
  echo "Using POSTGRES_HOST=postgres (Docker Compose environment)"
else
  export DB_HOST="host.docker.internal"
  export POSTGRES_HOST="host.docker.internal"
  echo "Using POSTGRES_HOST=host.docker.internal (Standalone Docker environment)"
fi

# Wait for PostgreSQL to be available
/wait-for-it.sh $DB_HOST 5432 echo "PostgreSQL is up"

# Run database initialization scripts (idempotent)
export PGPASSWORD="$POSTGRES_PASSWORD"
echo "Running initialization scripts for database $POSTGRES_DB as user $POSTGRES_USER..."
psql -h $DB_HOST -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /app/01-init-db.sql
psql -h $DB_HOST -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /app/02-add_test_users.sql

# Start the FastAPI development server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
