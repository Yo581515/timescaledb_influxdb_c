#!/usr/bin/env python3
import psycopg2
import random
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import threading

load_dotenv()


class SensorIngestion:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", 5432),
            "database": os.getenv("DB_NAME", "integrations_db"),
            "user": os.getenv("DB_USER", "admin"),
            "password": os.getenv("DB_PASSWORD", "passpass"),
        }

        # Simulated sensor configurations
        self.sensors = {
            "factory_floor": {
                "devices": ["TEMP_001", "TEMP_002", "HUMID_001", "PRESS_001"],
                "location": "Factory Floor A",
                "sensors": {
                    "TEMP_001": {"type": "temperature", "unit": "celsius", "range": (18, 26)},
                    "TEMP_002": {"type": "temperature", "unit": "celsius", "range": (20, 28)},
                    "HUMID_001": {"type": "humidity", "unit": "percent", "range": (40, 70)},
                    "PRESS_001": {"type": "pressure", "unit": "hPa", "range": (1010, 1025)},
                },
            },
            "warehouse": {
                "devices": ["TEMP_003", "MOTION_001", "LIGHT_001"],
                "location": "Warehouse B",
                "sensors": {
                    "TEMP_003": {"type": "temperature", "unit": "celsius", "range": (15, 25)},
                    "MOTION_001": {"type": "motion", "unit": "boolean", "range": (0, 1)},
                    "LIGHT_001": {"type": "light", "unit": "lux", "range": (100, 800)},
                },
            },
        }

        self.running = False

    def connect_db(self):
        """Connect to TimescaleDB"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None

    def generate_sensor_reading(self, device_id, sensor_config, location):
        """Generate realistic sensor reading"""
        sensor_type = sensor_config["type"]
        unit = sensor_config["unit"]
        value_range = sensor_config["range"]

        if sensor_type == "motion":
            # Motion sensor: mostly 0, occasionally 1
            value = 1 if random.random() < 0.1 else 0

        elif sensor_type == "temperature":
            # Temperature with some natural variation
            base_temp = sum(value_range) / 2
            variation = (value_range[1] - value_range[0]) * 0.3
            value = base_temp + random.uniform(-variation, variation)
            value = round(value, 2)

        elif sensor_type == "humidity":
            # Humidity with gradual changes
            value = random.uniform(*value_range)
            value = round(value, 1)

        elif sensor_type == "pressure":
            # Pressure with small variations
            base_pressure = sum(value_range) / 2
            variation = (value_range[1] - value_range[0]) * 0.2
            value = base_pressure + random.uniform(-variation, variation)
            value = round(value, 2)

        else:
            # Default: random value in range
            value = round(random.uniform(*value_range), 2)

        # Add some metadata
        metadata = {
            "battery_level": random.randint(75, 100),
            "signal_strength": random.randint(-80, -30),
            "firmware_version": "1.2.3",
        }

        return {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "location": location,
            "metadata": json.dumps(metadata),
            "timestamp": datetime.now(),
        }

    def insert_sensor_reading(self, reading):
        """Insert sensor reading into TimescaleDB"""
        conn = self.connect_db()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            insert_query = """
                INSERT INTO sensor_readings
                    (time, device_id, sensor_type, value, unit, location, metadata)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                insert_query,
                (
                    reading["timestamp"],
                    reading["device_id"],
                    reading["sensor_type"],
                    reading["value"],
                    reading["unit"],
                    reading["location"],
                    reading["metadata"],
                ),
            )

            conn.commit()
            print(f"📡 {reading['device_id']}: {reading['value']} {reading['unit']}")
            return True

        except Exception as e:
            print(f"❌ Failed to insert sensor reading: {e}")
            return False
        finally:
            conn.close()

    def simulate_location_sensors(self, location_name, location_config):
        """Simulate all sensors for a specific location"""
        while self.running:
            for device_id, sensor_config in location_config["sensors"].items():
                reading = self.generate_sensor_reading(
                    device_id,
                    sensor_config,
                    location_config["location"],
                )
                self.insert_sensor_reading(reading)
                time.sleep(0.5)  # Small delay between readings

            time.sleep(5)  # Delay between cycles

    def start_simulation(self, duration_minutes=10):
        """Start sensor simulation for all locations"""
        print(f"🏭 Starting IoT sensor simulation for {duration_minutes} minutes")
        print("📡 Sensors active:")

        for _, config in self.sensors.items():
            print(f"  📍 {config['location']}: {', '.join(config['devices'])}")

        self.running = True
        threads = []

        # Start a thread for each location
        for location_name, location_config in self.sensors.items():
            thread = threading.Thread(
                target=self.simulate_location_sensors,
                args=(location_name, location_config),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        try:
            # Run for specified duration
            time.sleep(duration_minutes * 60)
        except KeyboardInterrupt:
            print("\n🛑 Stopping sensor simulation...")
        finally:
            self.running = False
            print("✅ Sensor simulation stopped")


if __name__ == "__main__":
    simulation = SensorIngestion()

    print("🧪 Testing sensor ingestion...")
    simulation.start_simulation(duration_minutes=2)  # Run for 2 minutes