#!/usr/bin/env python3
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

load_dotenv()


class TimescaleAnalyzer:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "integrations_db"),
            "user": os.getenv("DB_USER", "admin"),
            "password": os.getenv("DB_PASSWORD", "admin123"),
        }

        # Plot style
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

    def connect_db(self):
        """Create database connection"""
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None

    def query_to_dataframe(self, query, params=None):
        """Execute query and return pandas DataFrame"""
        conn = self.connect_db()
        if not conn:
            return None

        try:
            return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return None
        finally:
            conn.close()

    def analyze_weather_data(self):
        """Analyze weather data and create visualizations"""
        print("🌤️  Analyzing weather data...")

        query = """
            SELECT
                time,
                city,
                temperature,
                humidity,
                pressure,
                wind_speed
            FROM weather_data
            WHERE time >= NOW() - INTERVAL '24 hours'
            ORDER BY time DESC, city
        """

        df = self.query_to_dataframe(query)
        if df is None or df.empty:
            print("❌ No weather data found")
            return None

        print(f"📊 Found {len(df)} weather records")
        print(f"🏙️  Cities: {', '.join(df['city'].unique())}")

        df["time"] = pd.to_datetime(df["time"])

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle("Weather Data Analysis", fontsize=16, fontweight="bold")

        # Temperature by city over time
        for city in df["city"].unique():
            city_data = df[df["city"] == city]
            axes[0, 0].plot(
                city_data["time"],
                city_data["temperature"],
                marker="o",
                label=city,
                linewidth=2,
            )

        axes[0, 0].set_title("Temperature Over Time by City")
        axes[0, 0].set_xlabel("Time")
        axes[0, 0].set_ylabel("Temperature (°C)")
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].tick_params(axis="x", rotation=45)

        # Current temperature comparison
        latest_data = df.groupby("city").last()
        bars = axes[0, 1].bar(latest_data.index, latest_data["temperature"])
        axes[0, 1].set_title("Current Temperature by City")
        axes[0, 1].set_ylabel("Temperature (°C)")
        axes[0, 1].tick_params(axis="x", rotation=45)

        for bar in bars:
            height = bar.get_height()
            axes[0, 1].text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.1f}°C",
                ha="center",
                va="bottom",
            )

        # Humidity vs Temperature scatter
        colors = plt.cm.viridis(np.linspace(0, 1, len(df["city"].unique())))
        for i, city in enumerate(df["city"].unique()):
            city_data = df[df["city"] == city]
            axes[1, 0].scatter(
                city_data["temperature"],
                city_data["humidity"],
                label=city,
                alpha=0.7,
                s=60,
                color=colors[i],
            )

        axes[1, 0].set_title("Humidity vs Temperature")
        axes[1, 0].set_xlabel("Temperature (°C)")
        axes[1, 0].set_ylabel("Humidity (%)")
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # Weather summary statistics
        summary_stats = (
            df.groupby("city")
            .agg(
                {
                    "temperature": ["mean", "min", "max"],
                    "humidity": "mean",
                    "wind_speed": "mean",
                }
            )
            .round(2)
        )

        # Heatmap of average values
        heatmap_data = df.groupby("city")[["temperature", "humidity", "wind_speed"]].mean()
        im = axes[1, 1].imshow(heatmap_data.T, cmap="YlOrRd", aspect="auto")
        axes[1, 1].set_title("Average Weather Metrics Heatmap")
        axes[1, 1].set_xticks(range(len(heatmap_data.index)))
        axes[1, 1].set_xticklabels(heatmap_data.index, rotation=45)
        axes[1, 1].set_yticks(range(len(heatmap_data.columns)))
        axes[1, 1].set_yticklabels(heatmap_data.columns)

        plt.colorbar(im, ax=axes[1, 1])

        for i in range(len(heatmap_data.index)):
            for j in range(len(heatmap_data.columns)):
                axes[1, 1].text(
                    i,
                    j,
                    f"{heatmap_data.iloc[i, j]:.1f}",
                    ha="center",
                    va="center",
                    color="black",
                )

        plt.tight_layout()
        plt.savefig("weather_analysis.png", dpi=300, bbox_inches="tight")
        plt.show()

        print("\n📈 Weather Summary Statistics:")
        print(summary_stats)

        return df

    def analyze_sensor_data(self):
        """Analyze IoT sensor data"""
        print("\n📡 Analyzing sensor data...")

        query = """
            SELECT
                time,
                device_id,
                sensor_type,
                value,
                unit,
                location,
                metadata
            FROM sensor_readings
            WHERE time >= NOW() - INTERVAL '2 hours'
            ORDER BY time DESC
        """

        df = self.query_to_dataframe(query)
        if df is None or df.empty:
            print("❌ No sensor data found")
            return None

        print(f"📊 Found {len(df)} sensor readings")
        print(f"🏭 Locations: {', '.join(df['location'].unique())}")

        df["time"] = pd.to_datetime(df["time"])

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle("IoT Sensor Data Analysis", fontsize=16, fontweight="bold")

        # Temperature sensors over time
        temp_data = df[df["sensor_type"] == "temperature"]
        if not temp_data.empty:
            for device in temp_data["device_id"].unique():
                device_data = temp_data[temp_data["device_id"] == device]
                axes[0, 0].plot(
                    device_data["time"],
                    device_data["value"],
                    marker="o",
                    label=device,
                    linewidth=2,
                )

            axes[0, 0].set_title("Temperature Sensors Over Time")
            axes[0, 0].set_xlabel("Time")
            axes[0, 0].set_ylabel("Temperature (°C)")
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].tick_params(axis="x", rotation=45)

        # Sensor type distribution
        sensor_counts = df["sensor_type"].value_counts()
        bars = axes[0, 1].bar(sensor_counts.index, sensor_counts.values)
        axes[0, 1].set_title("Sensor Reading Count by Type")
        axes[0, 1].set_ylabel("Number of Readings")
        axes[0, 1].tick_params(axis="x", rotation=45)

        for bar in bars:
            height = bar.get_height()
            axes[0, 1].text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(height)}",
                ha="center",
                va="bottom",
            )

        # Humidity sensor readings
        humidity_data = df[df["sensor_type"] == "humidity"]
        if not humidity_data.empty:
            axes[1, 0].plot(humidity_data["time"], humidity_data["value"], "g-o", linewidth=2)
            axes[1, 0].set_title("Humidity Sensor Readings")
            axes[1, 0].set_xlabel("Time")
            axes[1, 0].set_ylabel("Humidity (%)")
            axes[1, 0].grid(True, alpha=0.3)
            axes[1, 0].tick_params(axis="x", rotation=45)
        else:
            axes[1, 0].text(
                0.5,
                0.5,
                "No humidity data available",
                ha="center",
                va="center",
                transform=axes[1, 0].transAxes,
            )

        # Latest sensor values by location heatmap
        latest_readings = df.loc[df.groupby(["location", "sensor_type"])["time"].idxmax()]
        pivot_data = latest_readings.pivot_table(
            index="location",
            columns="sensor_type",
            values="value",
            aggfunc="mean",
        )

        if not pivot_data.empty:
            sns.heatmap(pivot_data, annot=True, fmt=".1f", cmap="viridis", ax=axes[1, 1])
            axes[1, 1].set_title("Latest Sensor Values by Location")
        else:
            axes[1, 1].text(
                0.5,
                0.5,
                "Insufficient data for heatmap",
                ha="center",
                va="center",
                transform=axes[1, 1].transAxes,
            )

        plt.tight_layout()
        plt.savefig("sensor_analysis.png", dpi=300, bbox_inches="tight")
        plt.show()

        print("\n📈 Sensor Summary Statistics:")
        summary = (
            df.groupby(["location", "sensor_type"])
            .agg({"value": ["count", "mean", "min", "max"]})
            .round(2)
        )
        print(summary)

        return df

    def create_combined_dashboard(self):
        """Create a combined dashboard with multiple data sources"""
        print("\n📊 Creating combined data dashboard...")

        queries = {
            "weather": """
                SELECT
                    time_bucket('1 hour', time) as bucket,
                    city,
                    AVG(temperature) as avg_temp,
                    AVG(humidity) as avg_humidity
                FROM weather_data
                WHERE time >= NOW() - INTERVAL '24 hours'
                GROUP BY bucket, city
                ORDER BY bucket DESC
            """,
            "sensors": """
                SELECT
                    time_bucket('15 minutes', time) as bucket,
                    sensor_type,
                    location,
                    AVG(value) as avg_value,
                    COUNT(*) as reading_count
                FROM sensor_readings
                WHERE time >= NOW() - INTERVAL '2 hours'
                GROUP BY bucket, sensor_type, location
                ORDER BY bucket DESC
            """,
        }

        data = {}
        for name, query in queries.items():
            df = self.query_to_dataframe(query)
            if df is not None and not df.empty:
                df["bucket"] = pd.to_datetime(df["bucket"])
                data[name] = df
            else:
                print(f"⚠️  No data found for {name}")

        if not data:
            print("❌ No data available for dashboard")
            return None

        # NOTE: Your PDF snippet stops here.
        # Paste the next section (TSDB008 page 20+) and I’ll append/clean it too.
        return data


if __name__ == "__main__":
    analyzer = TimescaleAnalyzer()

    print("🔍 Starting TimescaleDB Data Analysis")
    print("=" * 50)

    try:
        analyzer.analyze_weather_data()
        analyzer.analyze_sensor_data()
        analyzer.create_combined_dashboard()

        print("\n✅ Analysis complete! Check the generated PNG files and exported data.")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
