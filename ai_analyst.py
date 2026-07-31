import os
import requests
import psycopg2
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# ============================================
# LOAD .env FILE
# ============================================

load_dotenv()  # reads the .env file in the same folder and loads it into os.environ

# ============================================
# YOUR API KEY
# ============================================

API_KEY = os.getenv("OPENROUTER_API_KEY")

# ============================================
# YOUR POSTGRESQL CONNECTION
# ============================================

db = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)

# ============================================
# YOUR MONGODB ATLAS CONNECTION
# ============================================

MONGO_URI = os.getenv("MONGO_URI")

mongo_client = MongoClient(MONGO_URI)

# This creates a database called "ai_analyst" inside Atlas
# and a collection (like a table) called "conversations"
# Think of collection = drawer, document = piece of paper inside
mongo_db = mongo_client["ai_analyst"]
collection = mongo_db["conversations"]

# ============================================
# THE SCHEMA BRIEFING
# ============================================

SCHEMA_BRIEFING = """
You are an expert SQL analyst for a Sales and Customer Intelligence Platform.
Your job is to answer business questions by writing PostgreSQL SQL queries.

All tables live in the 'warehouse' schema — always write 'warehouse.table_name'.

--- DIMENSION TABLES ---

warehouse.dim_customer
  customer_key (integer, surrogate key)
  customer_id  (text, natural key)
  name         (text)
  city         (text)
  signup_date  (date)
  segment      (text — 'Standard' or 'Premium')

warehouse.dim_product
  product_id   (text, primary key e.g. 'PROD-001')
  category     (text e.g. 'Electronics', 'Clothing')
  brand        (text)
  product_name (text)
  price_min    (numeric)
  price_max    (numeric)
  supplier     (text)
  supplier_sku (text)

warehouse.dim_campaign
  campaign_id   (text, primary key e.g. 'CAMP-0001')
  campaign_name (text)
  source        (text e.g. 'Facebook', 'Google')
  goal          (text e.g. 'Brand Awareness', 'Lead Generation')

warehouse.dim_date
  date_key   (integer e.g. 20230115)
  full_date  (date)
  day        (integer)
  month      (integer)
  month_name (text)
  quarter    (integer)
  year       (integer)

warehouse.dim_device
  device_type (text — 'Mobile', 'Desktop', 'Tablet')

warehouse.dim_support_agent
  agent_id (text e.g. 'AGT-041')

warehouse.dim_activity_type
  activity_type_key (integer)
  activity_type     (text)
  category          (text)
  funnel_stage      (text)

--- FACT TABLES ---

warehouse.fact_orders
  order_id    (text, primary key)
  customer_id (text, FK → dim_customer.customer_id)
  product_id  (text, FK → dim_product.product_id)
  order_date  (date)
  quantity    (integer)
  price       (numeric — the revenue from this order)

warehouse.fact_marketing_perf
  campaign_id (text, FK → dim_campaign.campaign_id)
  start_date  (date)
  impressions (integer)
  clicks      (integer)
  conversions (integer)
  spend       (numeric)
  revenue     (numeric)

warehouse.fact_customer_activity
  session_id           (text, primary key)
  customer_id          (text, FK → dim_customer.customer_id)
  activity_timestamp   (numeric)
  session_duration_sec (integer)
  device_type          (text, FK → dim_device.device_type)
  page_view            (boolean)
  add_to_cart          (boolean)
  checkout             (boolean)
  purchase             (boolean)

warehouse.fact_support_tickets
  ticket_id          (text, primary key)
  customer_id        (text, FK → dim_customer.customer_id)
  issue_type         (text e.g. 'Delayed Delivery', 'Payment Issue')
  created_at         (numeric)
  resolution_hours   (numeric)
  resolution_status  (text e.g. 'Resolved', 'Pending', 'Escalated')
  satisfaction_score (numeric, 1 to 5)
  agent_id           (text, FK → dim_support_agent.agent_id)
  channel            (text e.g. 'Phone', 'Email', 'Chat')

--- RULES ---
1. Always use the 'warehouse.' prefix before every table name.
2. Always JOIN tables — never assume data is in one table.
3. Return ONLY the raw SQL query — no explanation, no markdown, no backticks.
4. End every query with a semicolon.
5. Use 'price' not 'total_amount' for order revenue in fact_orders.
6. Never use LIMIT unless the question explicitly asks for a specific number.
"""

# ============================================
# LOAD PREVIOUS CONVERSATION FROM MONGODB
# ============================================

def load_history():
    # Find the most recent conversation saved in Atlas
    last_session = collection.find_one(
        sort=[("started_at", -1)]
    )

    if last_session:
        print("\n--- Your last session ---")
        print(f"Started: {last_session['started_at']}")
        print(f"Questions asked: {len(last_session['messages']) // 2}")
        print("\nLast 5 questions you asked:")

        # Pull out only the user messages (not the SQL answers)
        user_messages = [
            m["content"]
            for m in last_session["messages"]
            if m["role"] == "user"
        ]

        # Show the last 5
        for i, q in enumerate(user_messages[-5:], 1):
            print(f"  {i}. {q}")
        print("-------------------------\n")

        # Return the messages so the AI remembers them
        return last_session["messages"]
    else:
        print("\nNo previous sessions found. Starting fresh!\n")
        return []

# ============================================
# SAVE CONVERSATION TO MONGODB
# ============================================

def save_history(session_id, messages):
    # Update the document in Atlas with the latest messages
    # upsert=True means: create it if it doesn't exist yet
    collection.update_one(
        {"session_id": session_id},
        {"$set": {
            "session_id": session_id,
            "started_at": datetime.now(),
            "messages": messages
        }},
        upsert=True
    )

# ============================================
# CONVERSATION MEMORY + MONGODB
# ============================================

# Create a unique ID for this session using today's date and time
# e.g. "session_20240115_143022"
session_id = "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")

# Load previous history from MongoDB to show the user
load_history()

# Start a fresh history for this new session
chat_history = []

# ============================================
# THE ask_ai FUNCTION
# ============================================

def ask_ai(question):

    # Step 1 — Add question to history
    chat_history.append({
        "role": "user",
        "content": question
    })

    # Step 2 — Send full history to AI
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "cohere/north-mini-code:free",
            "messages": [
                {
                    "role": "system",
                    "content": SCHEMA_BRIEFING
                }
            ] + chat_history
        }
    )

    # Step 3 — Extract SQL
    sql = response.json()["choices"][0]["message"]["content"]
    print(f"\nQuestion: {question}")
    print(f"\nAI wrote this SQL:\n{sql}")

    # Step 4 — Add AI answer to history
    chat_history.append({
        "role": "assistant",
        "content": sql
    })

    # Step 5 — Save to MongoDB after every question
    save_history(session_id, chat_history)
    print("(Saved to MongoDB ✓)")

    # Step 6 — Run SQL on PostgreSQL
    cursor = db.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    # Step 7 — Print results
    print("\nResults from your database:")
    print(" | ".join(columns))
    print("-" * 60)
    for row in rows:
        print(" | ".join(str(value) for value in row))
    print("\n")

# ============================================
# ASK YOUR QUESTIONS HERE
# ============================================

ask_ai("Which product category generates the most total revenue?")
ask_ai("Now show me the same but only for Premium customers")