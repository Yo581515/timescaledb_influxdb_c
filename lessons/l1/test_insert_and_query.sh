#!/usr/bin/env bash
# test_insert_and_query.sh
# Portable test script for TimescaleDB (Postgres+Timescale), InfluxDB, Grafana
# Works on macOS, Linux, and WSL.
# Usage: chmod +x test_insert_and_query.sh && ./test_insert_and_query.sh

set -euo pipefail

# === Configuration (match your docker-compose.yml) ===
PG_CONTAINER="timescaledb"
PG_USER="admin"
PG_DB="metricsdb"

INFLUX_CONTAINER="influxdb"
INFLUX_ORG="example-org"
INFLUX_BUCKET="example-bucket"
# INFLUX_TOKEN=""

# Optional: set this if your InfluxDB requires a token (recommended for InfluxDB 2.x)
# export INFLUX_TOKEN="your-token-here"

# === Start stack ===
echo "Starting docker compose (if not already running)..."
docker compose up -d

# === Wait for Postgres/TimescaleDB ===
echo "Waiting for TimescaleDB to be ready..."
attempt=0
max_attempts=60
while ! docker exec -i "${PG_CONTAINER}" pg_isready -U "${PG_USER}" >/dev/null 2>&1; do
  attempt=$((attempt+1))
  echo "  waiting for postgres... attempt ${attempt}/${max_attempts}"
  if [ "${attempt}" -ge "${max_attempts}" ]; then
    echo "Postgres did not become ready in time. Check container logs: docker logs ${PG_CONTAINER}"
    exit 1
  fi
  sleep 2
done
echo "Postgres is ready."

# === Create table and hypertable (idempotent) ===
echo "Creating sensor_data table and hypertable (if not exists)..."
docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d "${PG_DB}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS sensor_data (
  time TIMESTAMPTZ NOT NULL,
  sensor_id INT,
  temperature DOUBLE PRECISION
);

DO $$
BEGIN
  -- Create hypertable only if not already a hypertable
  IF NOT EXISTS (
    SELECT 1
    FROM timescaledb_information.hypertables
    WHERE hypertable_name='sensor_data'
  ) THEN
    PERFORM create_hypertable('sensor_data', 'time');
  END IF;
END;
$$;
SQL

# === Insert sample rows into TimescaleDB ===
echo "Inserting 3 timestamped rows into TimescaleDB..."
docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d "${PG_DB}" <<'SQL'
INSERT INTO sensor_data (time, sensor_id, temperature) VALUES
  (NOW() - INTERVAL '5 minutes', 1, 21.7),
  (NOW() - INTERVAL '2 minutes', 1, 22.1),
  (NOW(), 1, 22.6);
SQL

# === Query TimescaleDB: latest and last 1 hour ===
echo
echo "=== TimescaleDB: latest row ==="
docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d "${PG_DB}" -c \
"SELECT * FROM sensor_data ORDER BY time DESC LIMIT 1;"

echo
echo "=== TimescaleDB: rows from last 1 hour ==="
docker exec -i "${PG_CONTAINER}" psql -U "${PG_USER}" -d "${PG_DB}" -c \
"SELECT * FROM sensor_data WHERE time > NOW() - INTERVAL '1 hour' ORDER BY time ASC;"

# === Wait for InfluxDB HTTP API to be healthy ===
echo
echo "Waiting for InfluxDB HTTP API to be healthy..."
attempt=0
max_attempts=60
while true; do
  attempt=$((attempt+1))
  set +e
  status=$(docker exec "${INFLUX_CONTAINER}" sh -lc \
    "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8086/health" 2>/dev/null || echo "000")
  set -e

  if [ "${status}" = "200" ]; then
    break
  fi

  echo "  waiting for influxdb... attempt ${attempt}/${max_attempts} (status=${status})"
  if [ "${attempt}" -ge "${max_attempts}" ]; then
    echo "InfluxDB did not become healthy in time. Check container logs: docker logs ${INFLUX_CONTAINER}"
    exit 1
  fi
  sleep 2
done
echo "InfluxDB appears healthy."

# === Token args (only if INFLUX_TOKEN is set) ===
# INFLUX_TOKEN_ARGS=()
# if [ "${INFLUX_TOKEN:-}" != "" ]; then
#   echo "Using InfluxDB token for authentication."
#   INFLUX_TOKEN_ARGS+=(--token "${INFLUX_TOKEN}")
# fi
# # === debug token args value
# echo "INFLUX_TOKEN_ARGS=${INFLUX_TOKEN_ARGS[@]}"
# echo ""


# === Write sample points to InfluxDB (portable, safe) ===
echo "Writing 3 points to InfluxDB bucket=${INFLUX_BUCKET}..."

TS1=$(python3 - <<'PY'
import time
print(int(time.time() - 5*60))
PY
)

TS2=$(python3 - <<'PY'
import time
print(int(time.time() - 2*60))
PY
)

TS3=$(python3 - <<'PY'
import time
print(int(time.time()))
PY
)

{
  printf "temperature,sensor_id=1 value=21.7 %s\n" "$TS1"
  printf "temperature,sensor_id=1 value=22.1 %s\n" "$TS2"
  printf "temperature,sensor_id=1 value=22.6 %s\n" "$TS3"
} | docker exec -i "${INFLUX_CONTAINER}" influx write \
  --org "${INFLUX_ORG}" \
  --bucket "${INFLUX_BUCKET}" \
  --precision s \
  # "${INFLUX_TOKEN_ARGS[@]}" \
  -

# === Query InfluxDB: last 1 hour and latest point (Flux) ===
echo
echo "=== InfluxDB: last 1 hour (flux) ==="
docker exec -i "${INFLUX_CONTAINER}" influx query \
  --org "${INFLUX_ORG}" \
  --raw \
  # "${INFLUX_TOKEN_ARGS[@]}" \
  - <<'FLUX'
from(bucket:"example-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "temperature")
  |> filter(fn: (r) => r._field == "value")
  |> sort(columns: ["_time"])
FLUX

echo
echo "=== InfluxDB: latest point (flux) ==="
docker exec -i "${INFLUX_CONTAINER}" influx query \
  --org "${INFLUX_ORG}" \
  --raw \
  # "${INFLUX_TOKEN_ARGS[@]}" \
  - <<'FLUX'
from(bucket:"example-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "temperature")
  |> filter(fn: (r) => r._field == "value")
  |> sort(desc: true, columns: ["_time"])
  |> limit(n: 1)
FLUX

echo
echo "All done. If you saw rows for TimescaleDB and points for InfluxDB, your stack is working."