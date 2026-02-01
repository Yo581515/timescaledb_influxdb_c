#!/usr/bin/env bash
set -euo pipefail

echo "=== Stopping containers and removing volumes ==="
docker compose down -v

echo "=== Starting containers ==="
docker compose up -d

echo "=== Waiting for TimescaleDB to be ready ==="
sleep 10

PG="docker exec -i timescaledb psql -U admin -d metricsdb -v ON_ERROR_STOP=1"

echo "=== Enabling TimescaleDB extension ==="
$PG <<'SQL'
CREATE EXTENSION IF NOT EXISTS timescaledb;
SQL

echo "=== Creating hypertables (narrow + wide) ==="
$PG <<'SQL'
-- Drop tables if they exist
DROP TABLE IF EXISTS sensor_readings;
DROP TABLE IF EXISTS sensor_wide;
DROP TABLE IF EXISTS sensor_plain;

-- Narrow table
CREATE TABLE sensor_readings (
  time      TIMESTAMPTZ NOT NULL,
  device_id INT NOT NULL,
  metric    TEXT NOT NULL,
  value     DOUBLE PRECISION,
  PRIMARY KEY (time, device_id, metric)
);

SELECT create_hypertable(
  'sensor_readings',
  'time',
  chunk_time_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);

CREATE INDEX idx_sensor_readings_device_metric_time
ON sensor_readings (device_id, metric, time DESC);

-- Wide table
CREATE TABLE sensor_wide (
  time        TIMESTAMPTZ NOT NULL,
  device_id   INT NOT NULL,
  cpu_percent DOUBLE PRECISION,
  temperature DOUBLE PRECISION,
  stock_price DOUBLE PRECISION,
  PRIMARY KEY (time, device_id)
);

SELECT create_hypertable(
  'sensor_wide',
  'time',
  chunk_time_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);

CREATE INDEX idx_sensor_wide_device_time
ON sensor_wide (device_id, time DESC);
SQL

echo "=== Inserting synthetic data ==="
$PG <<'SQL'
\set rows_per_device 200000
\set devices 5

TRUNCATE sensor_readings, sensor_wide;

INSERT INTO sensor_wide (time, device_id, cpu_percent, temperature, stock_price)
SELECT
  NOW() - ((:rows_per_device * :devices) - gs) * INTERVAL '1 second',
  ((gs - 1) % :devices) + 1,
  (random() * 50 + 10),
  (random() * 10 + 15),
  (100.0 + (random() - 0.5) * 5.0)
FROM generate_series(1, (:rows_per_device * :devices)) gs;

INSERT INTO sensor_readings (time, device_id, metric, value)
SELECT time, device_id, 'cpu', cpu_percent FROM sensor_wide
UNION ALL
SELECT time, device_id, 'temperature', temperature FROM sensor_wide
UNION ALL
SELECT time, device_id, 'stock_price', stock_price FROM sensor_wide;

ANALYZE sensor_readings;
ANALYZE sensor_wide;
SQL

echo "=== Creating plain PostgreSQL table for comparison ==="
$PG <<'SQL'
CREATE TABLE sensor_plain (
  time      TIMESTAMPTZ NOT NULL,
  device_id INT NOT NULL,
  metric    TEXT NOT NULL,
  value     DOUBLE PRECISION
);

INSERT INTO sensor_plain (time, device_id, metric, value)
SELECT time, device_id, metric, value
FROM sensor_readings;

CREATE INDEX idx_sensor_plain_device_metric_time
ON sensor_plain (device_id, metric, time DESC);

ANALYZE sensor_plain;
SQL

echo "=== Verifying row counts ==="
$PG <<'SQL'
SELECT 'sensor_wide' AS table, count(*) FROM sensor_wide
UNION ALL
SELECT 'sensor_readings', count(*) FROM sensor_readings
UNION ALL
SELECT 'sensor_plain', count(*) FROM sensor_plain;
SQL

echo "=== Database restore complete ==="