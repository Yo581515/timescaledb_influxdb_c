#!/usr/bin/env python3
import psycopg2
import time
import random
from datetime import datetime
import threading


class IoTSensor:
    def __init__(self, device_id, location, base_temp=22.0):
        self.device_id = device_id
        self.location = location
        self.base_temp = base_temp
        self.current_temp = base_temp
        self.battery = random.randint(80, 100)
        self.running = True

    def generate_temperature(self):
        # Realistic temperature changes
        change = random.uniform(-0.5, 0.5)
        self.current_temp += change

        # Keep within reasonable bounds
        self.current_temp = max(10, min(40, self.current_temp))

        # Occasional battery drain
        if random.random() < 0.01:  # 1% chance
            self.battery = max(0, self.battery - 1)

        return round(self.current_temp, 1)

    def get_reading(self):
        return {
            "device_id": self.device_id,
            "location": self.location,
            "temperature": self.generate_temperature(),
            "humidity": random.randint(30, 70),
            "battery_level": self.battery,
            "timestamp": datetime.now(),
        }


class IoTSimulator:
    def __init__(self):
        self.db_config = {
            "host": "localhost",
            "port": 5555,
            "database": "iot_monitoring",
            "user": "admin",
            "password": "password123",
        }

        # Create sensors
        self.sensors = [
            IoTSensor("SENSOR_001", "Office", 22.0),
            IoTSensor("SENSOR_002", "Server Room", 26.0),
            IoTSensor("SENSOR_003", "Warehouse", 18.0),
            IoTSensor("SENSOR_004", "Kitchen", 24.0),
        ]

        self.running = True
        self.total_readings = 0

    def connect_db(self):
        return psycopg2.connect(**self.db_config)

    def insert_reading(self, reading):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO sensor_readings (
                    time, device_id, location, temperature, humidity, battery_level
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    reading["timestamp"],
                    reading["device_id"],
                    reading["location"],
                    reading["temperature"],
                    reading["humidity"],
                    reading["battery_level"],
                ),
            )

            conn.commit()
            cursor.close()
            conn.close()

            self.total_readings += 1
            return True

        except Exception as e:
            print(f"Database error: {e}")
            return False

    def simulate_sensor(self, sensor):
        while self.running:
            reading = sensor.get_reading()
            success = self.insert_reading(reading)

            if success:
                print(f"{sensor.device_id}: {reading['temperature']}°C at {sensor.location}")

            time.sleep(2)  # Send data every 2 seconds

    def start_simulation(self):
        print("Starting IoT Sensor Simulation")
        print(f"Monitoring {len(self.sensors)} sensors...")

        # Start threads for each sensor
        threads = []
        for sensor in self.sensors:
            thread = threading.Thread(target=self.simulate_sensor, args=(sensor,))
            thread.daemon = True
            thread.start()
            threads.append(thread)

        try:
            while True:
                time.sleep(10)
                print(f"Total readings sent: {self.total_readings}")
        except KeyboardInterrupt:
            print("\nStopping simulation...")
            self.running = False


if __name__ == "__main__":
    simulator = IoTSimulator()
    simulator.start_simulation()
