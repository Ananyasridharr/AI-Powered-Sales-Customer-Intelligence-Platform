import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# ============================================
# LOAD .env FILE
# ============================================

load_dotenv()

# ============================================
# CONNECT TO YOUR DATABASE
# ============================================

db = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)

print("Connected to database...")

# ============================================
# FEATURE 1 — ORDER HISTORY PER CUSTOMER
# How much have they spent? How recently?
# ============================================

orders_query = """
    SELECT
        c.customer_id,
        c.name,
        c.city,
        c.segment,
        COUNT(o.order_id)                    AS total_orders,
        COALESCE(SUM(o.price), 0)            AS total_spent,
        COALESCE(AVG(o.price), 0)            AS avg_order_value,
        MAX(o.order_date)                    AS last_order_date,
        CURRENT_DATE - MAX(o.order_date)     AS days_since_last_order
    FROM warehouse.dim_customer c
    LEFT JOIN warehouse.fact_orders o
           ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.name, c.city, c.segment
"""

orders_df = pd.read_sql(orders_query, db)
print(f"Order features built: {len(orders_df)} customers")

# ============================================
# FEATURE 2 — SUPPORT TICKET HISTORY
# How many issues? Were they resolved well?
# ============================================

tickets_query = """
    SELECT
        customer_id,
        COUNT(ticket_id)                     AS ticket_count,
        COALESCE(AVG(satisfaction_score), 3) AS avg_satisfaction,
        COALESCE(AVG(resolution_hours), 0)   AS avg_resolution_hours,
        SUM(CASE WHEN resolution_status = 'Resolved'
                 THEN 1 ELSE 0 END)          AS resolved_tickets,
        SUM(CASE WHEN resolution_status = 'Escalated'
                 THEN 1 ELSE 0 END)          AS escalated_tickets
    FROM warehouse.fact_support_tickets
    GROUP BY customer_id
"""

tickets_df = pd.read_sql(tickets_query, db)
print(f"Support features built: {len(tickets_df)} customers")

# ============================================
# FEATURE 3 — WEBSITE ACTIVITY
# Do they engage with the website?
# ============================================

activity_query = """
    SELECT
        customer_id,
        COUNT(session_id)                    AS total_sessions,
        SUM(CASE WHEN purchase = true
                 THEN 1 ELSE 0 END)          AS online_purchases,
        SUM(CASE WHEN add_to_cart = true
                 THEN 1 ELSE 0 END)          AS cart_additions,
        SUM(CASE WHEN checkout = true
                 THEN 1 ELSE 0 END)          AS checkouts
    FROM warehouse.fact_customer_activity
    GROUP BY customer_id
"""

activity_df = pd.read_sql(activity_query, db)
print(f"Activity features built: {len(activity_df)} customers")

# ============================================
# COMBINE ALL FEATURES INTO ONE TABLE
# ============================================

# Start with all customers from orders
features_df = orders_df.copy()

# Add support ticket features
# LEFT JOIN means: keep all customers even if they have no tickets
features_df = features_df.merge(
    tickets_df,
    on="customer_id",
    how="left"
)

# Add website activity features
features_df = features_df.merge(
    activity_df,
    on="customer_id",
    how="left"
)

# Fill any blanks with 0
# (customers with no tickets or no activity)
features_df = features_df.fillna(0)

# ============================================
# PREVIEW THE RESULT
# ============================================

print("\n--- YOUR FEATURE TABLE ---")
print(f"Shape: {features_df.shape[0]} customers x {features_df.shape[1]} columns")
print("\nColumn names:")
for col in features_df.columns:
    print(f"  - {col}")
print("\nFirst 3 customers:")
print(features_df.head(3).to_string())

# ============================================
# SAVE TO A CSV FILE FOR THE NEXT STEP
# ============================================

features_df.to_csv("customer_features.csv", index=False)
print("\nSaved to customer_features.csv ✓")