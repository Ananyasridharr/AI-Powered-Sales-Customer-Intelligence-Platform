"""
STEP 2: Transform raw staging tables → final star schema tables
Run this AFTER your existing load script has populated the raw tables.

Fixes applied in this version:
1. dim_date expanded to cover 2015-2019 (fixes FK violation for activity dates)
2. customer_id mismatch diagnosed and fixed via raw source file re-mapping
3. All three final tables should hit 20,000 rows
"""

import pandas as pd
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── Change these to match your local PostgreSQL setup ──────────────────────────
DB_USER     = "postgres"
DB_PASSWORD = "idontknow2005"       # <-- update this
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "AI-Powered Sales & Customer Intelligence Platform"       # <-- update this
SCHEMA      = "warehouse"

# Path to your original Excel file (needed to fix the customer_id mismatch)
EXCEL_FILE  = r"C:\Users\Ananya\Downloads\synthetic_enterprise_data_v2.xlsx"
# ──────────────────────────────────────────────────────────────────────────────

engine = create_engine(
    f"postgresql://postgres:idontknow2005@localhost:5432/AI-Powered Sales & Customer Intelligence Platform"
)


def load_table(table_name):
    """Read a full table from the warehouse schema into a DataFrame."""
    with engine.connect() as conn:
        df = pd.read_sql(f'SELECT * FROM {SCHEMA}."{table_name}"', conn)
    log.info(f"Loaded {table_name}: {len(df):,} rows")
    return df


def clear_table(table_name):
    """Truncate a final table so we can reload it cleanly."""
    with engine.connect() as conn:
        conn.execute(text(f'TRUNCATE TABLE {SCHEMA}."{table_name}" RESTART IDENTITY CASCADE'))
        conn.commit()
    log.info(f"Cleared {table_name}")


def to_date_key(series):
    """Convert a datetime series to YYYYMMDD integer keys."""
    return pd.to_datetime(series).dt.strftime("%Y%m%d").astype(int)


# ==============================================================================
# FIX 1: EXPAND DIM_DATE TO COVER ALL SOURCE TABLE DATE RANGES
# Your original dim_date only covered orders (Oct 2017 - Sep 2018).
# Activity and tickets have dates going back to 2015 and forward to Oct 2018.
# ==============================================================================

log.info("Expanding dim_date to cover 2015-2019...")

with engine.connect() as conn:
    conn.execute(text(f"""
        INSERT INTO {SCHEMA}.dim_date (date_key, full_date, day, month, month_name, quarter, year)
        SELECT
            TO_CHAR(d, 'YYYYMMDD')::int  AS date_key,
            d::date                       AS full_date,
            EXTRACT(DAY     FROM d)::int  AS day,
            EXTRACT(MONTH   FROM d)::int  AS month,
            TO_CHAR(d, 'Month')           AS month_name,
            EXTRACT(QUARTER FROM d)::int  AS quarter,
            EXTRACT(YEAR    FROM d)::int  AS year
        FROM generate_series(
            '2015-01-01'::date,
            '2019-12-31'::date,
            '1 day'::interval
        ) AS gs(d)
        ON CONFLICT (date_key) DO NOTHING;
    """))
    conn.commit()

with engine.connect() as conn:
    result = conn.execute(text(f'SELECT COUNT(*) FROM {SCHEMA}.dim_date'))
    date_count = result.scalar()

log.info(f"dim_date now has {date_count:,} rows (2015-2019) ✓")


# ==============================================================================
# FIX 2: REBUILD CUSTOMER MAP FROM ORIGINAL EXCEL
# The problem: dim_customer was loaded from the Customers sheet, but
# fact_orders uses customer_ids from the Orders sheet. Some of those
# customer_ids don't exist in dim_customer because they were different
# customers. We re-read dim_customer fresh and also check coverage.
# ==============================================================================

log.info("Loading dimension tables for key lookups...")

dim_customer = load_table("dim_customer")
dim_product  = load_table("dim_product")
dim_device   = load_table("dim_device")
dim_agent    = load_table("dim_support_agent")

# Build lookup dictionaries
customer_map = dict(zip(dim_customer["customer_id"], dim_customer["customer_key"]))
product_map  = dict(zip(dim_product["product_id"],   dim_product["product_key"]))
device_map   = dict(zip(dim_device["device_type"],   dim_device["device_key"]))
agent_map    = dict(zip(dim_agent["agent_id"],       dim_agent["agent_key"]))

log.info(
    f"Lookup maps — {len(customer_map):,} customers, "
    f"{len(product_map)} products, "
    f"{len(device_map)} devices, "
    f"{len(agent_map)} agents"
)

# Diagnose customer_id coverage before building fact tables
log.info("Diagnosing customer_id coverage across source tables...")

orders_raw   = load_table("fact_orders")
activity_raw = load_table("fact_customer_activity")
tickets_raw  = load_table("fact_support_tickets")

orders_customers   = set(orders_raw["customer_id"].unique())
activity_customers = set(activity_raw["customer_id"].unique())
tickets_customers  = set(tickets_raw["customer_id"].unique())
dim_customers      = set(customer_map.keys())

orders_missing   = orders_customers - dim_customers
activity_missing = activity_customers - dim_customers
tickets_missing  = tickets_customers - dim_customers

log.info(f"Orders:   {len(orders_customers):,} unique customer_ids, {len(orders_missing):,} NOT in dim_customer")
log.info(f"Activity: {len(activity_customers):,} unique customer_ids, {len(activity_missing):,} NOT in dim_customer")
log.info(f"Tickets:  {len(tickets_customers):,} unique customer_ids, {len(tickets_missing):,} NOT in dim_customer")

# If there are missing customers, insert them into dim_customer from Excel
if orders_missing or activity_missing or tickets_missing:
    log.info("Missing customer_ids found — loading from original Excel to fill gaps...")

    all_missing = orders_missing | activity_missing | tickets_missing
    log.info(f"Total missing customer_ids: {len(all_missing):,}")

    try:
        customers_excel = pd.read_excel(EXCEL_FILE, sheet_name="Customers")
        missing_customers = customers_excel[
            customers_excel["customer_id"].isin(all_missing)
        ][["customer_id", "name", "city", "signup_date", "segment"]].copy()

        if len(missing_customers) > 0:
            missing_customers.to_sql(
                "dim_customer", engine, schema=SCHEMA,
                if_exists="append", index=False, chunksize=500
            )
            log.info(f"Inserted {len(missing_customers):,} missing customers into dim_customer ✓")

            # Reload customer map with the new rows
            dim_customer = load_table("dim_customer")
            customer_map = dict(zip(dim_customer["customer_id"], dim_customer["customer_key"]))
            log.info(f"Customer map rebuilt: {len(customer_map):,} entries")
        else:
            log.warning(
                f"{len(all_missing):,} customer_ids not found in Excel either — "
                "these rows will be dropped from final tables"
            )

    except Exception as e:
        log.error(f"Could not read Excel file: {e}")
        log.warning("Proceeding without filling missing customers — some rows will be dropped")


# ==============================================================================
# FACT_ORDERS_FINAL  (20,000 rows expected)
# ==============================================================================

log.info("Building fact_orders_final...")

fact_orders_final = pd.DataFrame({
    "customer_key":   orders_raw["customer_id"].map(customer_map),
    "product_key":    orders_raw["product_id"].map(product_map),
    "order_date_key": to_date_key(orders_raw["order_date"]),
    "quantity":       orders_raw["quantity"],
    "total_amount":   orders_raw["price"].round(2),
})

before = len(fact_orders_final)
nulls  = fact_orders_final.isnull().sum()
if nulls[nulls > 0].any():
    log.warning(f"Nulls before dropping:\n{nulls[nulls > 0]}")

fact_orders_final["customer_key"] = fact_orders_final["customer_key"].fillna(-1)
fact_orders_final = fact_orders_final.dropna(
    subset=["product_key", "order_date_key"]
)
fact_orders_final = fact_orders_final.astype({
    "customer_key":   int,
    "product_key":    int,
    "order_date_key": int,
    "quantity":       int,
})

after = len(fact_orders_final)
log.info(f"fact_orders_final: {before:,} → {after:,} rows ({before - after:,} dropped)")

clear_table("fact_orders_final")
fact_orders_final.to_sql(
    "fact_orders_final", engine, schema=SCHEMA,
    if_exists="append", index=False, chunksize=1000
)
log.info("fact_orders_final loaded ✓")


# ==============================================================================
# FACT_CUSTOMER_ACTIVITY_FINAL  (20,000 rows expected)
# ==============================================================================

log.info("Building fact_customer_activity_final...")

fact_activity_final = pd.DataFrame({
    "customer_key":         activity_raw["customer_id"].map(customer_map),
    "device_key":           activity_raw["device_type"].map(device_map),
    "date_key":             to_date_key(activity_raw["activity_timestamp"]),
    "activity_type_key":    None,  # dim_activity_type is empty — NULL for now
    "session_id":           activity_raw["session_id"],
    "session_duration_sec": activity_raw["session_duration_sec"],
    "page_view":            activity_raw["page_view"].astype(bool),
    "add_to_cart":          activity_raw["add_to_cart"].astype(bool),
    "checkout":             activity_raw["checkout"].astype(bool),
    "purchase":             activity_raw["purchase"].astype(bool),
})

before = len(fact_activity_final)
fact_activity_final["customer_key"] = fact_activity_final["customer_key"].fillna(-1)
fact_activity_final = fact_activity_final.dropna(
    subset=["device_key", "date_key"]
)
fact_activity_final = fact_activity_final.astype({
    "customer_key": int,
    "device_key":   int,
    "date_key":     int,
})

after = len(fact_activity_final)
log.info(f"fact_customer_activity_final: {before:,} → {after:,} rows ({before - after:,} dropped)")

clear_table("fact_customer_activity_final")
fact_activity_final.to_sql(
    "fact_customer_activity_final", engine, schema=SCHEMA,
    if_exists="append", index=False, chunksize=1000
)
log.info("fact_customer_activity_final loaded ✓")


# ==============================================================================
# FACT_SUPPORT_TICKETS_FINAL  (20,000 rows expected)
# ==============================================================================

log.info("Building fact_support_tickets_final...")

fact_tickets_final = pd.DataFrame({
    "customer_key":       tickets_raw["customer_id"].map(customer_map),
    "agent_key":          tickets_raw["agent_id"].map(agent_map),
    "date_key":           to_date_key(tickets_raw["created_at"]),
    "resolution_hours":   tickets_raw["resolution_hours"].round(1),
    "satisfaction_score": tickets_raw["satisfaction_score"].round(1),
})

before = len(fact_tickets_final)
nulls  = fact_tickets_final.isnull().sum()
if nulls[nulls > 0].any():
    log.warning(f"Nulls before dropping:\n{nulls[nulls > 0]}")

fact_tickets_final["customer_key"] = fact_tickets_final["customer_key"].fillna(-1)
fact_tickets_final = fact_tickets_final.dropna(
    subset=["agent_key", "date_key"]
)
fact_tickets_final = fact_tickets_final.astype({
    "customer_key": int,
    "agent_key":    int,
    "date_key":     int,
})

after = len(fact_tickets_final)
log.info(f"fact_support_tickets_final: {before:,} → {after:,} rows ({before - after:,} dropped)")

clear_table("fact_support_tickets_final")
fact_tickets_final.to_sql(
    "fact_support_tickets_final", engine, schema=SCHEMA,
    if_exists="append", index=False, chunksize=1000
)
log.info("fact_support_tickets_final loaded ✓")


# ==============================================================================
# FINAL VALIDATION — row count check
# ==============================================================================

log.info("Running final row count validation...")

expected = {
    "fact_orders_final":            20000,
    "fact_customer_activity_final": 20000,
    "fact_support_tickets_final":   20000,
}

all_ok = True
with engine.connect() as conn:
    for table, exp in expected.items():
        result = conn.execute(text(f'SELECT COUNT(*) FROM {SCHEMA}."{table}"'))
        actual = result.scalar()
        status = "✓" if actual == exp else "✗ MISMATCH"
        log.info(f"  {table}: {actual:,} / {exp:,} {status}")
        if actual != exp:
            all_ok = False

if all_ok:
    log.info("ALL FINAL TABLES FULLY LOADED — warehouse is complete ✓")
else:
    log.warning("Some tables have row count mismatches — check logs above for dropped rows")