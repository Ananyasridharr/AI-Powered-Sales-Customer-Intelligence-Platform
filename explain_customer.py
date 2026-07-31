import os
import psycopg2
import requests
from dotenv import load_dotenv

# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

db = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)

# ============================================
# STEP 1 — PICK A CUSTOMER TO EXPLAIN
# ============================================

CUSTOMER_NAME = "Isabela Ribeiro"

# ============================================
# STEP 2 — FETCH THEIR FULL PROFILE
# ============================================

query = """
SELECT
    r.name,
    r.city,
    r.segment,
    r.churn_risk_score,
    r.risk_level,
    r.total_orders,
    r.total_spent,
    r.ticket_count,
    r.avg_satisfaction,
    r.days_since_last_order,
    t.issue_type,
    t.resolution_hours,
    t.resolution_status,
    t.channel
FROM warehouse.customer_risk_scores r
LEFT JOIN warehouse.fact_support_tickets t
       ON r.customer_id = t.customer_id
WHERE LOWER(r.name) = LOWER(%s)
LIMIT 5;
"""

cursor = db.cursor()
cursor.execute(query, (CUSTOMER_NAME,))
rows = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]

if not rows:
    print(f"Customer '{CUSTOMER_NAME}' not found.")
    cursor.close()
    db.close()
    exit()

# ============================================
# STEP 3 — FORMAT CUSTOMER DATA
# ============================================

main = dict(zip(columns, rows[0]))

tickets = []
for row in rows:
    d = dict(zip(columns, row))
    if d["issue_type"]:
        hours = d["resolution_hours"] if d["resolution_hours"] is not None else 0
        tickets.append(
            f"  - {d['issue_type']} via {d['channel']} "
            f"({hours:.0f} hours, {d['resolution_status']})"
        )

ticket_summary = "\n".join(tickets) if tickets else "  - No support tickets on record"

customer_briefing = f"""
CUSTOMER PROFILE:
  Name: {main['name']}
  City: {main['city']}
  Segment: {main['segment']}
  Churn risk score: {main['churn_risk_score']} / 100
  Risk level: {main['risk_level']}

ORDER HISTORY:
  Total orders: {int(main['total_orders'])}
  Total spent: ${main['total_spent']:,.2f}
  Days since last order: {int(main['days_since_last_order'])} days

SUPPORT HISTORY:
  Number of tickets: {int(main['ticket_count'])}
  Avg satisfaction: {main['avg_satisfaction']:.1f} / 5.0
  Tickets:
{ticket_summary}
"""

print("\n--- CUSTOMER PROFILE RETRIEVED ---")
print(customer_briefing)

# ============================================
# STEP 4 — ASK OPENROUTER AI
# ============================================

prompt = f"""
You are a customer success analyst reviewing a customer profile.

Here is the customer's data:

{customer_briefing}

Please provide:

1. A plain English explanation of why this customer is at their current churn risk.
2. The top 3 warning signs.
3. One specific action the company should take to retain the customer.

Keep the response concise and easy to understand.
"""

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "cohere/north-mini-code:free",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    },
    timeout=60
)

if response.status_code == 200:
    explanation = response.json()["choices"][0]["message"]["content"]
    print("\n--- AI EXPLANATION ---\n")
    print(explanation)
else:
    print("OpenRouter Error:")
    print(response.status_code)
    print(response.text)

cursor.close()
db.close()