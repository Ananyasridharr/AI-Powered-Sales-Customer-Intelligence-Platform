import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# =====================================================
# LOAD .env FILE
# =====================================================

load_dotenv()

# =====================================================
# POSTGRESQL CONNECTION
# =====================================================

PG_HOST = os.getenv("POSTGRES_HOST")
PG_DB = os.getenv("POSTGRES_DB")
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")

engine = create_engine(
    f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}/{PG_DB}"
)

# =====================================================
# EXCEL FILE PATH
# =====================================================

file = r"C:\Users\Ananya\Downloads\synthetic_enterprise_data_v3.xlsx"

# =====================================================
# LOAD CUSTOMERS -> DIM_CUSTOMER
# =====================================================

customers_df = pd.read_excel(file, sheet_name="Customers")

customers_df.to_sql(
    "dim_customer",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Customers loaded successfully!")


# =====================================================
# LOAD PRODUCTS -> DIM_PRODUCT
# =====================================================

products_df = pd.read_excel(file, sheet_name="Products")

products_df.to_sql(
    "dim_product",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Products loaded successfully!")


# =====================================================
# LOAD ORDERS -> FACT_ORDERS (RAW)
# =====================================================

orders_df = pd.read_excel(file, sheet_name="Orders")

orders_df.to_sql(
    "fact_orders",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Orders loaded successfully!")


# =====================================================
# LOAD CAMPAIGN DIMENSION
# =====================================================

campaigns_df = pd.read_excel(file, sheet_name="Marketing_Campaigns")

campaign_dim_df = campaigns_df[[
    'campaign_id',
    'campaign_name',
    'source',
    'goal'
]]

campaign_dim_df.to_sql(
    "dim_campaign",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Campaign dimension loaded successfully!")


# =====================================================
# LOAD FACT_MARKETING_PERF
# =====================================================

marketing_fact_df = campaigns_df[[
    'campaign_id',
    'start_date',
    'impressions',
    'clicks',
    'conversions',
    'spend',
    'revenue'
]]

marketing_fact_df.to_sql(
    "fact_marketing_perf",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Marketing performance fact loaded successfully!")


# =====================================================
# LOAD WEBSITE ACTIVITY -> FACT_CUSTOMER_ACTIVITY
# =====================================================

activity_df = pd.read_excel(file, sheet_name="Website_Activity")

# Convert integer columns to BOOLEAN
bool_cols = ['page_view', 'add_to_cart', 'checkout', 'purchase']

for col in bool_cols:
    activity_df[col] = activity_df[col].astype(bool)

activity_df.to_sql(
    "fact_customer_activity",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Website activity loaded successfully!")


# =====================================================
# LOAD SUPPORT TICKETS -> FACT_SUPPORT_TICKETS
# =====================================================

tickets_df = pd.read_excel(file, sheet_name="Support_Tickets")

tickets_df.to_sql(
    "fact_support_tickets",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Support tickets loaded successfully!")


# =====================================================
# CREATE & LOAD DIM_DATE
# =====================================================

min_date = orders_df['order_date'].min()
max_date = orders_df['order_date'].max()

dates = pd.date_range(start=min_date, end=max_date)

date_df = pd.DataFrame({
    'full_date': dates
})

date_df['date_key'] = date_df['full_date'].dt.strftime('%Y%m%d').astype(int)

date_df['day'] = date_df['full_date'].dt.day

date_df['month'] = date_df['full_date'].dt.month

date_df['month_name'] = date_df['full_date'].dt.month_name()

date_df['quarter'] = date_df['full_date'].dt.quarter

date_df['year'] = date_df['full_date'].dt.year

date_df.to_sql(
    "dim_date",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Date dimension loaded successfully!")


# =====================================================
# CREATE & LOAD DIM_DEVICE
# =====================================================

device_df = activity_df[['device_type']].drop_duplicates()

device_df.to_sql(
    "dim_device",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Device dimension loaded successfully!")


# =====================================================
# CREATE & LOAD DIM_SUPPORT_AGENT
# =====================================================

agent_df = tickets_df[['agent_id']].drop_duplicates()

agent_df.to_sql(
    "dim_support_agent",
    engine,
    schema="warehouse",
    if_exists="append",
    index=False
)

print("Support agent dimension loaded successfully!")

print("ALL DATA LOADED SUCCESSFULLY!")