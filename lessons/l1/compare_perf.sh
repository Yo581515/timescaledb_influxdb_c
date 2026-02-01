#!/usr/bin/env bash
set -euo pipefail

PG="docker exec -i timescaledb psql -U admin -d metricsdb -q -A -t"

echo "=== Range query: last 1 hour, device 1, cpu metric ==="
$PG -c "\timing on"
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT time, value FROM sensor_readings WHERE device_id = 1 AND metric = 'cpu' AND time > NOW() - INTERVAL '1 hour' ORDER BY time DESC LIMIT 100;" 
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT time, value FROM sensor_plain    WHERE device_id = 1 AND metric = 'cpu' AND time > NOW() - INTERVAL '1 hour' ORDER BY time DESC LIMIT 100;"
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT time, cpu_percent FROM sensor_wide WHERE device_id = 1 AND time > NOW() - INTERVAL '1 hour' ORDER BY time DESC LIMIT 100;"

echo "=== Aggregation: avg per minute last 6 hours ==="
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT time_bucket('1 minute', time) AS minute, avg(value)       FROM sensor_readings WHERE metric='cpu' AND time > NOW() - INTERVAL '6 hours' GROUP BY minute;"
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT time_bucket('1 minute', time) AS minute, avg(value)       FROM sensor_plain    WHERE metric='cpu' AND time > NOW() - INTERVAL '6 hours' GROUP BY minute;"
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT time_bucket('1 minute', time) AS minute, avg(cpu_percent) FROM sensor_wide     WHERE time > NOW() - INTERVAL '6 hours' GROUP BY minute;"

echo "=== Point lookup: latest per device ==="
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT DISTINCT ON (device_id) device_id, time, value       FROM sensor_readings WHERE metric='cpu' ORDER BY device_id, time DESC;"
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT DISTINCT ON (device_id) device_id, time, value       FROM sensor_plain    WHERE metric='cpu' ORDER BY device_id, time DESC;"
$PG -c "EXPLAIN (ANALYZE, BUFFERS) SELECT DISTINCT ON (device_id) device_id, time, cpu_percent FROM sensor_wide     ORDER BY device_id, time DESC;"
