#!/usr/bin/env bash
set -euo pipefail

PG_CONTAINER="timescaledb"
INFLUX_CONTAINER="influxdb"
PG_USER="admin"
PG_DB="metricsdb"
INFLUX_ORG="example-org"
INFLUX_BUCKET="example-bucket"

CSV_LOCAL="cpu_data.csv"
LP_LOCAL="cpu.lp"

# 1) generate data if missing
if [ ! -f "$CSV_LOCAL" ] || [ ! -f "$LP_LOCAL" ]; then
  echo "Generating data..."
  python3 generate_data.py
else
  echo "Data present, skipping generation."
fi

# 2) copy files into containers
docker cp "$CSV_LOCAL" ${PG_CONTAINER}:/tmp/cpu_data.csv
docker cp "$LP_LOCAL" ${INFLUX_CONTAINER}:/tmp/cpu.lp

measure() {
  label="$1"
  shift
  echo "---- $label ----"
  start=$(date +%s.%N)
  "$@"
  end=$(date +%s.%N)
  elapsed=$(awk "BEGIN {print ($end - $start)}")
  printf "%s elapsed: %0.3f s\n\n" "$label" "$elapsed"
}

# 3) COPY into plain Postgres table
measure "COPY -> sensor_plain_ingest" \
  docker exec -i ${PG_CONTAINER} psql -U ${PG_USER} -d ${PG_DB} \
  -c "\COPY sensor_plain_ingest(time, device_id, value) FROM '/tmp/cpu_data.csv' CSV"

# 4) COPY into TimescaleDB hypertable
measure "COPY -> sensor_ingest (hypertable)" \
  docker exec -i ${PG_CONTAINER} psql -U ${PG_USER} -d ${PG_DB} \
  -c "\COPY sensor_ingest(time, device_id, value) FROM '/tmp/cpu_data.csv' CSV"

# 5) InfluxDB write
measure "InfluxDB write" \
  sh -c "docker exec -i ${INFLUX_CONTAINER} influx write \
    --org ${INFLUX_ORG} \
    --bucket ${INFLUX_BUCKET} \
    --precision ns - < ${LP_LOCAL}"

# 6) short streaming test
echo "Running streaming insert test (100,000 rows)"
python3 stream_insert.py --table sensor_stream --rows 100000 --batch 1000

# 7) row counts
echo "Counts:"
docker exec -i ${PG_CONTAINER} psql -U ${PG_USER} -d ${PG_DB} \
  -c "SELECT 'sensor_plain_ingest' AS table, count(*) FROM sensor_plain_ingest;"
docker exec -i ${PG_CONTAINER} psql -U ${PG_USER} -d ${PG_DB} \
  -c "SELECT 'sensor_ingest' AS table, count(*) FROM sensor_ingest;"
docker exec -i ${PG_CONTAINER} psql -U ${PG_USER} -d ${PG_DB} \
  -c "SELECT 'sensor_stream' AS table, count(*) FROM sensor_stream;"

echo "Benchmark run complete."
