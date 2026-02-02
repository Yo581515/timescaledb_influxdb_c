-- Enable TimescaleDB extension 
CREATE EXTENSION IF NOT EXISTS timescaledb; 
 
-- Sensor data table 
CREATE TABLE sensor_readings ( 
    time TIMESTAMPTZ NOT NULL, 
    device_id TEXT NOT NULL, 
    location TEXT NOT NULL, 
    temperature DOUBLE PRECISION NOT NULL, 
    humidity INTEGER, 
    battery_level INTEGER DEFAULT 100 
); 
 
-- Convert to hypertable for time-series optimization 
SELECT create_hypertable('sensor_readings', 'time'); 
 
-- Create index for better query performance 
CREATE INDEX idx_sensor_device_time ON sensor_readings (device_id, time DESC); 
 
-- Alert table 
CREATE TABLE temperature_alerts ( 
    id SERIAL PRIMARY KEY, 
    device_id TEXT NOT NULL, 
    temperature DOUBLE PRECISION NOT NULL, 
    threshold_exceeded DOUBLE PRECISION NOT NULL, 
    alert_time TIMESTAMPTZ DEFAULT NOW(), 
    message TEXT 
); 
 
-- Sample devices 
INSERT INTO sensor_readings (time, device_id, location, temperature, humidity) VALUES 
    (NOW() - INTERVAL '1 hour', 'SENSOR_001', 'Office', 22.5, 45), 
    (NOW() - INTERVAL '1 hour', 'SENSOR_002', 'Server Room', 24.8, 35), 
    (NOW() - INTERVAL '1 hour', 'SENSOR_003', 'Warehouse', 19.2, 60); 
 
-- Function to check temperature alerts 
CREATE OR REPLACE FUNCTION check_temperature_alert() 
RETURNS TRIGGER AS $$ 
BEGIN 
    -- Alert if temperature > 30°C 
    IF NEW.temperature > 30.0 THEN 
        INSERT INTO temperature_alerts (device_id, temperature, threshold_exceeded, message) 
        VALUES (NEW.device_id, NEW.temperature, 30.0,  
                format('High temperature alert: %.1f°C at %s', NEW.temperature, NEW.location)); 
    END IF; 
     
    -- Alert if temperature < 15°C 
    IF NEW.temperature < 15.0 THEN 
        INSERT INTO temperature_alerts (device_id, temperature, threshold_exceeded, message) 
        VALUES (NEW.device_id, NEW.temperature, 15.0, 
                format('Low temperature alert: %.1f°C at %s', NEW.temperature, NEW.location)); 
    END IF; 
     
    RETURN NEW; 
END;

$$ LANGUAGE plpgsql; 
 
-- Create trigger for automatic alerts 
CREATE TRIGGER temperature_alert_trigger 
    AFTER INSERT ON sensor_readings 
    FOR EACH ROW 
    EXECUTE FUNCTION check_temperature_alert(); 
 
-- Create continuous aggregate for hourly averages 
CREATE MATERIALIZED VIEW hourly_averages 
WITH (timescaledb.continuous) AS 
SELECT  
    time_bucket('1 hour', time) AS bucket, 
    device_id, 
    location, 
    AVG(temperature) as avg_temperature, 
    MIN(temperature) as min_temperature, 
    MAX(temperature) as max_temperature, 
    COUNT(*) as reading_count 
FROM sensor_readings 
GROUP BY bucket, device_id, location; 
 
-- Simple auto-refresh policy (refresh every 30 minutes) 
SELECT add_continuous_aggregate_policy('hourly_averages', 
    start_offset => INTERVAL '1 day', 
    end_offset => INTERVAL '1 hour', 
    schedule_interval => INTERVAL '30 minutes');