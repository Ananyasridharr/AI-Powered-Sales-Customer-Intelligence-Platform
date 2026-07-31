import os
import pandas as pd
import pickle
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()

# Build PostgreSQL connection URL
DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}/"
    f"{os.getenv('POSTGRES_DB')}"
)

# ============================================
# STEP 1 — LOAD THE TRAINED MODEL
# ============================================

with open("churn_model.pkl", "rb") as f:
    model = pickle.load(f)

with open("feature_columns.pkl", "rb") as f:
    feature_columns = pickle.load(f)

print("Model loaded ✓")

# ============================================
# STEP 2 — LOAD THE CUSTOMER FEATURES
# ============================================

df = pd.read_csv("customer_features.csv")

df["segment_code"] = df["segment"].map({
    "Standard": 0,
    "Premium": 1,
    "Basic": 2
}).fillna(0)

print(f"Loaded {len(df):,} customers ✓")

# ============================================
# STEP 3 — GENERATE RISK SCORES
# ============================================

churn_probability = model.predict_proba(df[feature_columns])[:, 1]

df["churn_risk_score"] = (churn_probability * 100).round(1)

def risk_label(score):
    if score >= 75:
        return "High Risk"
    elif score >= 50:
        return "Medium Risk"
    else:
        return "Low Risk"

df["risk_level"] = df["churn_risk_score"].apply(risk_label)

print("Risk scores generated ✓")

# ============================================
# STEP 4 — PREVIEW RESULTS
# ============================================

print("\n--- TOP 10 HIGHEST RISK CUSTOMERS ---")

high_risk = (
    df[
        [
            "name",
            "city",
            "segment",
            "churn_risk_score",
            "risk_level",
            "ticket_count",
            "avg_satisfaction",
            "avg_resolution_hours",
            "days_since_last_order",
        ]
    ]
    .sort_values("churn_risk_score", ascending=False)
    .head(10)
)

print(high_risk.to_string(index=False))

print("\n--- RISK DISTRIBUTION ---")
print(df["risk_level"].value_counts())

print("\n--- SCORE SUMMARY ---")
print(f"Average risk score: {df['churn_risk_score'].mean():.1f}")
print(f"Highest risk score: {df['churn_risk_score'].max():.1f}")
print(f"Lowest risk score: {df['churn_risk_score'].min():.1f}")
print(f"Customers above 75: {(df['churn_risk_score'] >= 75).sum():,}")
print(f"Customers above 50: {(df['churn_risk_score'] >= 50).sum():,}")

# ============================================
# STEP 5 — SAVE TO POSTGRESQL
# ============================================

print("\nSaving scores to PostgreSQL...")

engine = create_engine(DATABASE_URL)

scores_df = df[
    [
        "customer_id",
        "name",
        "city",
        "segment",
        "churn_risk_score",
        "risk_level",
        "total_orders",
        "total_spent",
        "ticket_count",
        "avg_satisfaction",
        "days_since_last_order",
    ]
]

scores_df.to_sql(
    "customer_risk_scores",
    engine,
    schema="warehouse",
    if_exists="replace",
    index=False,
    method="multi",
)

print("Scores saved to warehouse.customer_risk_scores ✓")

# ============================================
# STEP 6 — SAVE CSV BACKUP
# ============================================

df.to_csv("customer_scores.csv", index=False)
print("Scores saved to customer_scores.csv ✓")

engine.dispose()

print(f"\nStep 3 complete — all {len(df):,} customers scored!")