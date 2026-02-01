#!/usr/bin/env python3
import requests
import psycopg2
import time
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()


class WeatherIngestion:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME", "integrations_db"),
            "user": os.getenv("DB_USER", "admin"),
            "password": os.getenv("DB_PASSWORD", "admin123"),
        }

        # Using free weather API (no key required)
        self.base_url = "https://api.open-meteo.com/v1/forecast"

        # Cities to monitor
        self.cities = {
            "New York": {"lat": 40.7128, "lon": -74.0060},
            "London": {"lat": 51.5074, "lon": -0.1278},
            "Tokyo": {"lat": 35.6762, "lon": 139.6503},
            "Sydney": {"lat": -33.8688, "lon": 151.2093},
            "Mumbai": {"lat": 19.0760, "lon": 72.8777},
        }

    def connect_db(self):
        """Connect to TimescaleDB"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None

    def fetch_weather_data(self, city, coordinates):
        """Fetch weather data from Open-Meteo API"""
        try:
            params = {
                "latitude": coordinates["lat"],
                "longitude": coordinates["lon"],
                "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m",
                "timezone": "auto",
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            current = data["current"]

            return {
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "pressure": current.get("surface_pressure"),
                "wind_speed": current.get("wind_speed_10m"),
                "description": f"Temperature: {current.get('temperature_2m')}°C",
                "timestamp": datetime.fromisoformat(current["time"].replace("Z", "+00:00")),
            }

        except Exception as e:
            print(f"❌ Failed to fetch weather for {city}: {e}")
            return None

    def insert_weather_data(self, city, weather_data):
        """Insert weather data into TimescaleDB"""
        conn = self.connect_db()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            insert_query = """
                INSERT INTO weather_data
                    (time, city, temperature, humidity, pressure, wind_speed, description)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                insert_query,
                (
                    weather_data["timestamp"],
                    city,
                    weather_data["temperature"],
                    weather_data["humidity"],
                    weather_data["pressure"],
                    weather_data["wind_speed"],
                    weather_data["description"],
                ),
            )

            conn.commit()
            print(f"✅ Inserted weather data for {city}: {weather_data['temperature']}°C")
            return True

        except Exception as e:
            print(f"❌ Failed to insert data for {city}: {e}")
            return False
        finally:
            conn.close()

    def run_ingestion_cycle(self):
        """Run one complete ingestion cycle for all cities"""
        print(f"🌤️  Starting weather ingestion at {datetime.now()}")

        success_count = 0
        for city, coordinates in self.cities.items():
            weather_data = self.fetch_weather_data(city, coordinates)

            if weather_data:
                if self.insert_weather_data(city, weather_data):
                    success_count += 1
                time.sleep(1)  # Be nice to the API

        print(f"📊 Ingestion complete: {success_count}/{len(self.cities)} cities updated")
        return success_count

    def run_continuous(self, interval_minutes=15):
        """Run continuous ingestion"""
        print(f"🔄 Starting continuous weather ingestion (every {interval_minutes} minutes)")
        print("Press Ctrl+C to stop")

        try:
            while True:
                self.run_ingestion_cycle()
                print(f"💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n🛑 Stopping weather ingestion")


if __name__ == "__main__":
    ingestion = WeatherIngestion()

    # Run a single cycle first
    print("🧪 Testing single ingestion cycle...")
    ingestion.run_ingestion_cycle()

    # Ask user if they want continuous ingestion
    print("\n" + "=" * 50)
    response = input("Run continuous ingestion? (y/n): ").lower()

    if response == "y":
        ingestion.run_continuous(interval_minutes=5)  # Every 5 minutes for demo
    else:
        print("✅ Single ingestion complete!")
