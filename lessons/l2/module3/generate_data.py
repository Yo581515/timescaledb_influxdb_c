#!/usr/bin/env python3

from datetime import datetime, timezone, timedelta
import random

ROW_COUNT = 1000000
CSV_PATH = "cpu_data.csv"
LP_PATH = "cpu.lp"

def iso_ts(dt):
    return dt.isoformat()

def ns_epoch(dt):
    return int(dt.timestamp() * 1_000_000_000)

def main():
    start = datetime.now(timezone.utc)

    print(f"Generating {ROW_COUNT} rows...")

    with open(CSV_PATH, "w") as csvf, open(LP_PATH, "w") as lpf:
        for i in range(ROW_COUNT):
            ts = start + timedelta(seconds=i)
            device_id = random.randint(1, 10)
            value = round(random.uniform(10.0, 90.0), 2)

            csvf.write(f"{iso_ts(ts)},{device_id},{value}\n")
            lpf.write(f"cpu,device_id={device_id} value={value} {ns_epoch(ts)}\n")

    print("Done generating data.")

if __name__ == "__main__":
    main()