import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()

# Build local PostgreSQL URL
LOCAL_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}/"
    f"{os.getenv('POSTGRES_DB')}"
)

# Neon connection string
NEON_URL = os.getenv("NEON_DATABASE_URL")

# ============================================
# CONNECT TO BOTH DATABASES
# ============================================

print("Connecting to local database...")
local_engine = create_engine(LOCAL_URL)
print("✓ Local connected")

print("Connecting to Neon...")
neon_engine = create_engine(NEON_URL)
print("✓ Neon connected")

# ============================================
# CREATE SCHEMA IN NEON
# ============================================

with neon_engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS warehouse"))

print("✓ Warehouse schema ready")

# ============================================
# TABLES TO MIGRATE
# ============================================

tables = [
    "dim_customer",
    "dim_product",
    "dim_campaign",
    "dim_date",
    "dim_device",
    "dim_support_agent",
    "fact_orders",
    "fact_marketing_perf",
    "fact_customer_activity",
    "fact_support_tickets",
    "customer_risk_scores",
]

total_rows = 0

# ============================================
# MIGRATE TABLES
# ============================================

for table in tables:
    print(f"\nMigrating {table}...")

    try:
        df = pd.read_sql(
            f"SELECT * FROM warehouse.{table}",
            local_engine
        )

        df.to_sql(
            table,
            neon_engine,
            schema="warehouse",
            if_exists="replace",
            index=False,
            chunksize=1000,
            method="multi"
        )

        total_rows += len(df)
        print(f"✓ {len(df):,} rows migrated")

    except Exception as e:
        print(f"✗ Failed: {e}")

print(f"\nMigration complete!")
print(f"Total rows migrated: {total_rows:,}")

# ============================================
# CLEAN UP
# ============================================

local_engine.dispose()
neon_engine.dispose()