#!/usr/bin/env python3
# stream_insert.py
# Batched streaming insert into a table (sensor_stream or sensor_ingest).

import argparse
import time
import random
import psycopg2
from datetime import datetime, timedelta, timezone


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--dsn",
        default="dbname=metricsdb user=admin password=admin123 host=localhost port=5432",
    )
    p.add_argument("--table", default="sensor_stream")
    p.add_argument("--rows", type=int, default=1000000)
    p.add_argument("--batch", type=int, default=1000)
    return p.parse_args()


def main():
    args = parse_args()

    conn = psycopg2.connect(args.dsn)
    cur = conn.cursor()

    start_time = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
    
    t0 = time.time()

    buffer = []
    inserted = 0

    for i in range(args.rows):
        ts = start_time + timedelta(seconds=i)
        device_id = random.randint(1, 10)
        value = round(random.uniform(10.0, 90.0), 2)

        if args.table == "sensor_stream":
            buffer.append((ts, device_id, "cpu", value))
        else:
            buffer.append((ts, device_id, value))

        if len(buffer) >= args.batch:
            if args.table == "sensor_stream":
                vals = ",".join(cur.mogrify("(%s,%s,%s,%s)", r).decode() for r in buffer)
                cur.execute(
                    "INSERT INTO sensor_stream(time, device_id, metric, value) VALUES "
                    + vals
                )
            else:
                vals = ",".join(cur.mogrify("(%s,%s,%s)", r).decode() for r in buffer)
                cur.execute(
                    "INSERT INTO sensor_ingest(time, device_id, value) VALUES " + vals
                )

            conn.commit()
            inserted += len(buffer)
            buffer.clear()

    if buffer:
        if args.table == "sensor_stream":
            vals = ",".join(cur.mogrify("(%s,%s,%s,%s)", r).decode() for r in buffer)
            cur.execute(
                "INSERT INTO sensor_stream(time, device_id, metric, value) VALUES "
                + vals
            )
        else:
            vals = ",".join(cur.mogrify("(%s,%s,%s)", r).decode() for r in buffer)
            cur.execute("INSERT INTO sensor_ingest(time, device_id, value) VALUES " + vals)

        conn.commit()
        inserted += len(buffer)

    t1 = time.time()

    cur.close()
    conn.close()

    elapsed = t1 - t0
    print(
        f"Inserted {inserted} rows into {args.table} in {elapsed:.2f} s "
        f"({inserted/elapsed:.2f} rows/s)"
    )


if __name__ == "__main__":
    main()
