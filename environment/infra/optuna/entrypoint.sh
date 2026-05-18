#!/bin/sh

set -e

# Wait for postgres to be ready
echo "Waiting for postgres..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "Postgres is up!"

# Create the database if it doesn't exist
echo "Ensuring optuna_db exists..."
export PGPASSWORD=postgres
psql -h postgres -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'optuna_db'" | grep -q 1 || \
psql -h postgres -U postgres -c "CREATE DATABASE optuna_db"

# Initialize the Optuna database schema
echo "Initializing Optuna database schema..."
python3 -c "import optuna; optuna.create_study(storage='postgresql://postgres:postgres@postgres:5432/optuna_db', study_name='healthcheck', load_if_exists=True)"

# Start the dashboard
echo "Starting optuna-dashboard..."
exec optuna-dashboard postgresql://postgres:postgres@postgres:5432/optuna_db --host 0.0.0.0 --port 8080
