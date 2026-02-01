#!/usr/bin/env bash
# cleanup_benchmarks.sh (hypertable-safe)
# Drops benchmark tables one-by-one (avoids "cannot drop a hypertable along with other objects"),
# removes files copied into containers, and optionally cleans Node artifacts.

set -euo pipefail

PG_CONTAINER=${PG_CONTAINER:-timescaledb}
INFLUX_CONTAINER=${INFLUX_CONTAINER:-influxdb}
PG_USER=${PG_USER:-admin}
PG_DB=${PG_DB:-metricsdb}

LOCAL_FILES=("cpu_data.csv" "cpu.lp")
CONTAINER_PG_TMP="/tmp/cpu_data.csv"
CONTAINER_INFLUX_TMP="/tmp/cpu.lp"

KEEP_NODE=${KEEP_NODE:-false}  # set KEEP_NODE=true to preserve package.json etc

TABLES=("sensor_plain_ingest" "sensor_ingest" "sensor_stream")

echo "=== Cleanup start ==="
echo "Using Postgres container: ${PG_CONTAINER}, DB: ${PG_DB}"

# show hypertables for info
echo "Hypertables currently present (if any):"
docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d "${PG_DB}" \
  -c "SELECT hypertable_name FROM timescaledb_information.hypertables;" || true

echo "Dropping tables individually (safe for hypertables)..."
for t in "${TABLES[@]}"; do
  echo "Attempting: DROP TABLE IF EXISTS ${t};"
  if docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d "${PG_DB}" \
    -c "DROP TABLE IF EXISTS ${t};"
  then
    echo "  Dropped ${t} (or it did not exist)."
  else
    echo "  DROP TABLE failed for ${t} — retrying with CASCADE ..."
    # try again with CASCADE (will remove dependent objects)
    docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d "${PG_DB}" \
      -c "DROP TABLE IF EXISTS ${t} CASCADE;"
    echo "  Dropped ${t} with CASCADE."
  fi
done

echo "Removing temporary files inside containers (if present)..."
if docker exec "${PG_CONTAINER}" test -f "${CONTAINER_PG_TMP}" >/dev/null 2>&1; then
  docker exec -i "${PG_CONTAINER}" bash -lc \
    "rm -f '${CONTAINER_PG_TMP}' && echo 'Removed ${CONTAINER_PG_TMP} from ${PG_CONTAINER}'"
else
  echo "  ${CONTAINER_PG_TMP} not found in ${PG_CONTAINER}"
fi

if docker exec "${INFLUX_CONTAINER}" test -f "${CONTAINER_INFLUX_TMP}" >/dev/null 2>&1; then
  docker exec -i "${INFLUX_CONTAINER}" bash -lc \
    "rm -f '${CONTAINER_INFLUX_TMP}' && echo 'Removed ${CONTAINER_INFLUX_TMP} from ${INFLUX_CONTAINER}'"
else
  echo "  ${CONTAINER_INFLUX_TMP} not found in ${INFLUX_CONTAINER}"
fi

echo "Removing local generated files..."
for f in "${LOCAL_FILES[@]}"; do
  if [ -f "$f" ]; then
    rm -f "$f"
    echo "  removed: $f"
  else
    echo "  not found: $f"
  fi
done

if [ "${KEEP_NODE}" = "true" ] || [ "${KEEP_NODE}" = "True" ]; then
  echo "KEEP_NODE=true -> preserving package.json, package-lock.json and node_modules (if any)."
else
  echo "Removing Node artifacts on host (if present): package.json, package-lock.json, node_modules"
  if [ -f package.json ]; then
    rm -f package.json && echo "  removed: package.json"
  else
    echo "  package.json not found"
  fi

  if [ -f package-lock.json ]; then
    rm -f package-lock.json && echo "  removed: package-lock.json"
  else
    echo "  package-lock.json not found"
  fi

  if [ -d node_modules ]; then
    rm -rf node_modules && echo "  removed: node_modules/"
  else
    echo "  node_modules not found"
  fi
fi

echo
echo "NOTE: If you still see hypertables in timescaledb_information.hypertables, list dependent objects:"
echo "  docker exec -i ${PG_CONTAINER} psql -U ${PG_USER} -d ${PG_DB} -c \"SELECT * FROM timescaledb_information.hypertables;\""
echo "If there are dependent continuous aggregates or policies, drop those objects first (e.g., DROP MATERIALIZED VIEW <name> or remove policies)."

echo "Cleanup complete."
echo "To remove Docker containers & volumes (destructive): docker compose down -v"
echo "=== Cleanup finished ==="
