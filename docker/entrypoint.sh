#!/bin/bash
set -e

# Wait for database
echo "Waiting for PostgreSQL..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; do
  echo "Database is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is up and running!"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Execute the container's main command
exec "$@"
