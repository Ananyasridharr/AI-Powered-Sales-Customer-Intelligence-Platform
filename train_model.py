import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pickle

# ============================================
# STEP 1 — LOAD YOUR FEATURE TABLE
# ============================================

df = pd.read_csv("customer_features.csv")
df["segment_code"] = df["segment"].map({
    "Standard": 0, "Premium": 1, "Basic": 2
}).fillna(0)
print(f"Loaded {len(df)} customers with {len(df.columns)} features")

# ============================================
# STEP 2 — DEFINE WHAT "CHURN" MEANS
# A customer who hasn't ordered in 365+ days
# ============================================

df["churned"] = (df["days_since_last_order"] >= 365).astype(int)

churned_count = df["churned"].sum()
active_count = len(df) - churned_count
print(f"\nChurned customers:  {churned_count}")
print(f"Active customers:   {active_count}")
print(f"Churn rate:         {churned_count/len(df)*100:.1f}%")

# ============================================
# STEP 3 — PICK THE FEATURES THE MODEL WILL USE
# These are the "signals" it learns from
# ============================================

feature_columns = [
    "segment_code",
    "ticket_count",
    "avg_satisfaction",
    "avg_resolution_hours",
    "resolved_tickets",
    "escalated_tickets",
    "total_sessions",
    "online_purchases",
    "cart_additions",
    "checkouts"
]

X = df[feature_columns]   # the signals
y = df["churned"]         # the answer (0=active, 1=churned)

print(f"\nFeatures the model will learn from: {len(feature_columns)}")

# ============================================
# STEP 4 — SPLIT INTO TRAINING AND TESTING
# ============================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

print(f"\nTraining set:  {len(X_train)} customers")
print(f"Testing set:   {len(X_test)} customers")

# ============================================
# STEP 5 — TRAIN THE MODEL
# ============================================

print("\nTraining the model...")

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

print("Training complete!")

# ============================================
# STEP 6 — TEST HOW ACCURATE IT IS
# ============================================

y_pred = model.predict(X_test)

print("\n--- MODEL ACCURACY REPORT ---")
print(classification_report(y_test, y_pred,
      target_names=["Active", "Churned"]))

# ============================================
# STEP 7 — SEE WHICH FEATURES MATTER MOST
# ============================================

print("--- WHAT THE MODEL LEARNED ---")
importance = pd.DataFrame({
    "feature": feature_columns,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)

for _, row in importance.iterrows():
    bar = "█" * int(row["importance"] * 100)
    print(f"  {row['feature']:<30} {bar} {row['importance']:.3f}")

# ============================================
# STEP 8 — SAVE THE MODEL FOR LATER USE
# ============================================

with open("churn_model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("feature_columns.pkl", "wb") as f:
    pickle.dump(feature_columns, f)

print("\nModel saved to churn_model.pkl ✓")
print("Ready for Step 3 — scoring all 20,000 customers!")