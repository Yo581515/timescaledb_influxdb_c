#!/usr/bin/env python3
import subprocess
import time
import sys
from datetime import datetime


def run_command(command: str, description: str) -> bool:
    """Run a shell command and handle errors."""
    print(f"\n🚀 {description}")
    print(f"💻 Running: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"📄 Output:\n{result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        err = e.stderr.strip() if e.stderr else str(e)
        print(f"Error:\n{err}")
        return False


def check_dependencies() -> bool:
    """Check if all required packages are installed."""
    print("🔍 Checking dependencies...")

    required_packages = ["psycopg2", "pandas", "matplotlib", "seaborn", "requests"]
    missing = []

    for pkg in required_packages:
        try:
            __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} - MISSING")
            missing.append(pkg)

    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("💡 Run:")
        print("   pip install psycopg2-binary pandas matplotlib seaborn requests python-dotenv")
        return False

    print("✅ All dependencies satisfied")
    return True


def _run_analysis() -> None:
    run_command(f"{sys.executable} data_analysis.py", "Data analysis")


def _run_export() -> None:
    # Avoid nasty multiline quoting from PDF by using a short one-liner.
    cmd = (
        f'{sys.executable} -c "from data_analysis import TimescaleAnalyzer; '
        f'TimescaleAnalyzer().export_data_samples()"'
    )
    run_command(cmd, "Data export")


def _run_status_check() -> None:
    # Keep it simple: run a tiny python snippet that prints counts.
    cmd = (
        f'{sys.executable} -c "'
        f'from data_analysis import TimescaleAnalyzer; '
        f'a=TimescaleAnalyzer(); '
        f'import pandas as pd; '
        f'w=a.query_to_dataframe(\\"SELECT COUNT(*) AS weather_records '
        f'FROM weather_data WHERE time >= NOW() - INTERVAL \'24 hours\'\\"); '
        f's=a.query_to_dataframe(\\"SELECT COUNT(*) AS sensor_records '
        f'FROM sensor_readings WHERE time >= NOW() - INTERVAL \'2 hours\'\\"); '
        f'print(\\"Weather (24h):\\", w.iloc[0].to_dict() if w is not None and not w.empty else w); '
        f'print(\\"Sensors (2h):\\", s.iloc[0].to_dict() if s is not None and not s.empty else s)"'

    )
    run_command(cmd, "Data status check")


def main() -> None:
    print("🎯 TimescaleDB Integration Pipeline Runner")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Check if database service exists / is up
    print("\n🔍 Checking database status...")
    if not run_command("docker compose ps timescaledb", "Database status check"):
        print("💡 Start the database with: docker compose up -d")
        sys.exit(1)

    print("\n📋 Pipeline Options:")
    print("1. Run complete pipeline (ingestion + analysis)")
    print("2. Run data ingestion only")
    print("3. Run data analysis only")
    print("4. Export data samples")
    print("5. Check data status")

    choice = input("\nSelect option (1-5): ").strip()

    if choice == "1":
        print("\n🎯 Running complete data pipeline...")

        # Start weather ingestion in background
        print("🌤️  Starting weather data ingestion...")
        weather_process = subprocess.Popen([sys.executable, "weather_ingestion.py"])

        # Wait a bit for weather data to start
        time.sleep(10)

        # Start sensor simulation in background
        print("📡 Starting sensor simulation...")
        sensor_process = subprocess.Popen([sys.executable, "sensor_ingestion.py"])

        # Wait for data collection
        print("⏳ Collecting data for 3 minutes...")
        time.sleep(180)

        # Stop ingestion processes
        print("🛑 Stopping data ingestion...")
        weather_process.terminate()
        sensor_process.terminate()

        # Give them a moment to exit cleanly
        time.sleep(5)

        # Run analysis
        print("📊 Running data analysis...")
        _run_analysis()

    elif choice == "2":
        print("\n📥 Starting data ingestion...")
        print("🌤️  Weather ingestion will run for 2 minutes")
        print("📡 Sensor simulation will run for 2 minutes")
        print("Press Ctrl+C to stop early")

        weather_process = None
        sensor_process = None

        try:
            weather_process = subprocess.Popen([sys.executable, "weather_ingestion.py"])
            time.sleep(5)
            sensor_process = subprocess.Popen([sys.executable, "sensor_ingestion.py"])

            time.sleep(120)
            print("✅ Data ingestion completed")

        except KeyboardInterrupt:
            print("\n🛑 Stopping ingestion processes...")

        finally:
            for p in (weather_process, sensor_process):
                if p is not None:
                    try:
                        p.terminate()
                    except Exception:
                        pass

    elif choice == "3":
        _run_analysis()

    elif choice == "4":
        print("\n💾 Exporting data samples...")
        _run_export()

    elif choice == "5":
        _run_status_check()

    else:
        print("❌ Invalid option selected")
        sys.exit(1)

    print(f"\n🎉 Pipeline execution completed at {datetime.now()}")
    print("📁 Check the current directory for generated files:")
    print("  - *.png (visualization files)")
    print("  - *.csv (exported data)")
    print("  - *.json (exported data)")


if __name__ == "__main__":
    main()
