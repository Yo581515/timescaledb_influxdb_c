#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="results"
mkdir -p "$OUT_DIR"

PG="docker exec -i timescaledb psql -U admin -d metricsdb -q -A -t"

run_explain_json () {
  local filename="$1"
  local sql="$2"

  $PG -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) $sql" \
    > "${OUT_DIR}/${filename}.json"

  echo "Saved: ${OUT_DIR}/${filename}.json"
}

echo "=== Range query: last 1 hour, device 1, cpu metric ==="
run_explain_json \
  "range_1h_sensor_readings_cpu_device1" \
  "SELECT time, value FROM sensor_readings WHERE device_id = 1 AND metric = 'cpu' AND time > NOW() - INTERVAL '1 hour' ORDER BY time DESC LIMIT 100;"

run_explain_json \
  "range_1h_sensor_plain_cpu_device1" \
  "SELECT time, value FROM sensor_plain WHERE device_id = 1 AND metric = 'cpu' AND time > NOW() - INTERVAL '1 hour' ORDER BY time DESC LIMIT 100;"

run_explain_json \
  "range_1h_sensor_wide_cpu_device1" \
  "SELECT time, cpu_percent FROM sensor_wide WHERE device_id = 1 AND time > NOW() - INTERVAL '1 hour' ORDER BY time DESC LIMIT 100;"

echo "=== Aggregation: avg per minute last 6 hours ==="
run_explain_json \
  "agg_6h_avg_per_min_sensor_readings_cpu" \
  "SELECT time_bucket('1 minute', time) AS minute, avg(value) FROM sensor_readings WHERE metric='cpu' AND time > NOW() - INTERVAL '6 hours' GROUP BY minute;"

run_explain_json \
  "agg_6h_avg_per_min_sensor_plain_cpu" \
  "SELECT time_bucket('1 minute', time) AS minute, avg(value) FROM sensor_plain WHERE metric='cpu' AND time > NOW() - INTERVAL '6 hours' GROUP BY minute;"

run_explain_json \
  "agg_6h_avg_per_min_sensor_wide_cpu" \
  "SELECT time_bucket('1 minute', time) AS minute, avg(cpu_percent) FROM sensor_wide WHERE time > NOW() - INTERVAL '6 hours' GROUP BY minute;"

echo "=== Point lookup: latest per device ==="
run_explain_json \
  "latest_per_device_sensor_readings_cpu" \
  "SELECT DISTINCT ON (device_id) device_id, time, value FROM sensor_readings WHERE metric='cpu' ORDER BY device_id, time DESC;"

run_explain_json \
  "latest_per_device_sensor_plain_cpu" \
  "SELECT DISTINCT ON (device_id) device_id, time, value FROM sensor_plain WHERE metric='cpu' ORDER BY device_id, time DESC;"

run_explain_json \
  "latest_per_device_sensor_wide_cpu" \
  "SELECT DISTINCT ON (device_id) device_id, time, cpu_percent FROM sensor_wide ORDER BY device_id, time DESC;"
