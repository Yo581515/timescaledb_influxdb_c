-- init-scripts/01-setup.sql
-- Clean, copy-safe setup SQL (Module 8 schema)

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Weather data table
CREATE TABLE IF NOT EXISTS weather_data (
    time        TIMESTAMPTZ NOT NULL,
    city        TEXT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity    INTEGER,
    pressure    DOUBLE PRECISION,
    wind_speed  DOUBLE PRECISION,
    description TEXT,
    api_source  TEXT DEFAULT 'openweather'
);

-- Create hypertable (idempotent)
SELECT create_hypertable('weather_data', 'time', if_not_exists => TRUE);

-- Stock price data table
CREATE TABLE IF NOT EXISTS stock_prices (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    open_price  DOUBLE PRECISION,
    high_price  DOUBLE PRECISION,
    low_price   DOUBLE PRECISION,
    close_price DOUBLE PRECISION,
    volume      BIGINT,
    api_source  TEXT DEFAULT 'alphavantage'
);

-- Create hypertable (idempotent)
SELECT create_hypertable('stock_prices', 'time', if_not_exists => TRUE);

-- Sensor data table (for simulated IoT)
CREATE TABLE IF NOT EXISTS sensor_readings (
    time        TIMESTAMPTZ NOT NULL,
    device_id   TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    value       DOUBLE PRECISION,
    unit        TEXT,
    location    TEXT,
    metadata    JSONB
);

-- Create hypertable (idempotent)
SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE);

-- Indexes for better query performance (idempotent)
CREATE INDEX IF NOT EXISTS idx_weather_city_time
    ON weather_data (city, time DESC);

CREATE INDEX IF NOT EXISTS idx_stock_symbol_time
    ON stock_prices (symbol, time DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_device_time
    ON sensor_readings (device_id, time DESC);
