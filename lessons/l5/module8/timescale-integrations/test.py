import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Always load the .env next to this script (not whatever the current working dir is)
env_path = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=env_path)

config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "integrations_db"),
    "user": os.getenv("DB_USER", "yosafe"),
    "password": os.getenv("DB_PASSWORD", "yosafe123"),
}

print(config)

conn = psycopg2.connect(**config)
cur = conn.cursor()

# Prove which server we hit
cur.execute("select inet_server_addr(), inet_server_port(), version(), current_user;")
print("CONNECTED TO:", cur.fetchone())

cur.execute("SELECT NOW();")
print("NOW():", cur.fetchone())

cur.close()
conn.close()
