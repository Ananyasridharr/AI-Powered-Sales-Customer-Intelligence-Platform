import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import requests
import os
from dotenv import load_dotenv

# ============================================
# LOAD .env FILE
# ============================================

load_dotenv()

# ============================================
# PAGE CONFIGURATION — must be first line
# ============================================

st.set_page_config(
    page_title="Sales Intelligence Platform",
    page_icon="📊",
    layout="wide"
)

# Fix for Windows psycopg2 connection caching
os.environ["no_proxy"] = "*"


# ============================================
# DATABASE CONNECTION
# ============================================

@st.cache_resource
def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

db = get_connection()

# ============================================
# DATA LOADING FUNCTIONS
# ============================================

@st.cache_data
def load_risk_scores():
    query = """
        SELECT name, city, segment,
               churn_risk_score, risk_level,
               total_orders, total_spent,
               ticket_count, avg_satisfaction,
               days_since_last_order
        FROM warehouse.customer_risk_scores
        ORDER BY churn_risk_score DESC
    """
    return pd.read_sql(query, db)

@st.cache_data
def load_revenue_by_category():
    query = """
        SELECT p.category,
               SUM(o.price)    AS total_revenue,
               COUNT(o.order_id) AS total_orders
        FROM warehouse.fact_orders o
        JOIN warehouse.dim_product p
          ON o.product_id = p.product_id
        GROUP BY p.category
        ORDER BY total_revenue DESC
    """
    return pd.read_sql(query, db)

@st.cache_data
def load_revenue_by_city():
    query = """
        SELECT c.city,
               SUM(o.price) AS total_revenue,
               COUNT(DISTINCT o.customer_id) AS customers
        FROM warehouse.fact_orders o
        JOIN warehouse.dim_customer c
          ON o.customer_id = c.customer_id
        GROUP BY c.city
        ORDER BY total_revenue DESC
        LIMIT 15
    """
    return pd.read_sql(query, db)

@st.cache_data
def load_marketing_performance():
    query = """
        SELECT dc.source,
               SUM(f.spend)    AS total_spend,
               SUM(f.revenue)  AS total_revenue,
               ROUND(SUM(f.revenue) /
                     NULLIF(SUM(f.spend),0), 2) AS roas
        FROM warehouse.fact_marketing_perf f
        JOIN warehouse.dim_campaign dc
          ON f.campaign_id = dc.campaign_id
        GROUP BY dc.source
        ORDER BY roas DESC
    """
    return pd.read_sql(query, db)

@st.cache_data
def load_support_summary():
    query = """
        SELECT issue_type,
               COUNT(*)              AS ticket_count,
               ROUND(AVG(resolution_hours)::numeric, 1)
                                     AS avg_hours,
               ROUND(AVG(satisfaction_score)::numeric, 2)
                                     AS avg_satisfaction
        FROM warehouse.fact_support_tickets
        GROUP BY issue_type
        ORDER BY avg_hours DESC
    """
    return pd.read_sql(query, db)

# ============================================
# SIDEBAR NAVIGATION
# ============================================

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Overview", "Customer Risk", "Marketing", "Support", "AI Analyst"]
)

# ============================================
# PAGE 1 — OVERVIEW
# ============================================

if page == "Overview":
    st.title("Sales & Customer Intelligence")
    st.caption("Powered by your PostgreSQL warehouse + AI")

    risk_df = load_risk_scores()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", f"{len(risk_df):,}")
    col2.metric("High Risk",
                f"{(risk_df['risk_level']=='High Risk').sum():,}",
                delta="-needs attention",
                delta_color="inverse")
    col3.metric("Avg Risk Score",
                f"{risk_df['churn_risk_score'].mean():.1f}/100")
    col4.metric("Total Revenue",
                f"${risk_df['total_spent'].sum():,.0f}")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Revenue by product category")
        cat_df = load_revenue_by_category()
        fig = px.bar(
            cat_df,
            x="category",
            y="total_revenue",
            color="total_revenue",
            color_continuous_scale="purples",
            labels={"total_revenue": "Revenue ($)",
                    "category": "Category"}
        )
        fig.update_layout(showlegend=False,
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Top 15 cities by revenue")
        city_df = load_revenue_by_city()
        fig2 = px.bar(
            city_df,
            x="total_revenue",
            y="city",
            orientation="h",
            color="total_revenue",
            color_continuous_scale="teal",
            labels={"total_revenue": "Revenue ($)",
                    "city": "City"}
        )
        fig2.update_layout(showlegend=False,
                           coloraxis_showscale=False,
                           yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig2, use_container_width=True)

# ============================================
# PAGE 2 — CUSTOMER RISK
# ============================================

elif page == "Customer Risk":
    st.title("Customer Churn Risk")
    st.caption("Scores generated by your Random Forest model")

    risk_df = load_risk_scores()

    col1, col2, col3 = st.columns(3)
    high = (risk_df["risk_level"] == "High Risk").sum()
    med  = (risk_df["risk_level"] == "Medium Risk").sum()
    low  = (risk_df["risk_level"] == "Low Risk").sum()
    col1.metric("High Risk",   f"{high:,}", delta="above 75")
    col2.metric("Medium Risk", f"{med:,}",  delta="50–75")
    col3.metric("Low Risk",    f"{low:,}",  delta="below 50")

    st.divider()

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Risk distribution")
        dist_df = risk_df["risk_level"].value_counts().reset_index()
        dist_df.columns = ["Risk Level", "Count"]
        fig = px.pie(
            dist_df,
            names="Risk Level",
            values="Count",
            color="Risk Level",
            color_discrete_map={
                "High Risk":   "#E24B4A",
                "Medium Risk": "#BA7517",
                "Low Risk":    "#1D9E75"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Risk score vs days inactive")
        fig2 = px.scatter(
            risk_df.sample(min(2000, len(risk_df))),
            x="days_since_last_order",
            y="churn_risk_score",
            color="risk_level",
            color_discrete_map={
                "High Risk":   "#E24B4A",
                "Medium Risk": "#BA7517",
                "Low Risk":    "#1D9E75"
            },
            hover_data=["name", "city", "segment"],
            labels={
                "days_since_last_order": "Days since last order",
                "churn_risk_score": "Risk score"
            },
            opacity=0.6
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Customer risk table")

    risk_filter = st.selectbox(
        "Filter by risk level",
        ["All", "High Risk", "Medium Risk", "Low Risk"]
    )

    filtered = risk_df if risk_filter == "All" \
               else risk_df[risk_df["risk_level"] == risk_filter]

    st.dataframe(
        filtered[[
            "name", "city", "segment",
            "churn_risk_score", "risk_level",
            "total_orders", "total_spent",
            "ticket_count", "avg_satisfaction",
            "days_since_last_order"
        ]].reset_index(drop=True),
        use_container_width=True,
        height=400
    )

# ============================================
# PAGE 3 — MARKETING
# ============================================

elif page == "Marketing":
    st.title("Marketing Performance")

    mkt_df = load_marketing_performance()

    for _, row in mkt_df.iterrows():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Channel", row["source"])
        col2.metric("Total Spend",   f"${row['total_spend']:,.0f}")
        col3.metric("Total Revenue", f"${row['total_revenue']:,.0f}")
        col4.metric("ROAS", f"{row['roas']}x")
        st.divider()

    st.subheader("Revenue vs Spend by channel")
    fig = px.bar(
        mkt_df,
        x="source",
        y=["total_spend", "total_revenue"],
        barmode="group",
        labels={"value": "Amount ($)", "source": "Channel"},
        color_discrete_map={
            "total_spend":   "#AFA9EC",
            "total_revenue": "#534AB7"
        }
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# PAGE 4 — SUPPORT
# ============================================

elif page == "Support":
    st.title("Support Performance")

    sup_df = load_support_summary()

    st.subheader("Resolution time by issue type")
    fig = px.bar(
        sup_df,
        x="avg_hours",
        y="issue_type",
        orientation="h",
        color="avg_satisfaction",
        color_continuous_scale="RdYlGn",
        labels={
            "avg_hours":       "Avg resolution hours",
            "issue_type":      "Issue type",
            "avg_satisfaction": "Avg satisfaction"
        }
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Support data table")
    st.dataframe(sup_df, use_container_width=True)

# ============================================
# PAGE 5 — AI ANALYST
# ============================================

elif page == "AI Analyst":
    st.title("AI Analyst")
    st.caption("Ask anything about your data in plain English")

    API_KEY = os.getenv("OPENROUTER_API_KEY")

    SCHEMA = """
    You are an expert SQL analyst for a Sales Intelligence Platform.
    Answer questions using these PostgreSQL tables (all in 'warehouse' schema):
    - fact_orders: order_id, customer_id, product_id, order_date, quantity, price
    - dim_customer: customer_id, name, city, segment, signup_date
    - dim_product: product_id, product_name, category, brand, price_min, price_max
    - fact_support_tickets: ticket_id, customer_id, issue_type, resolution_hours, satisfaction_score, resolution_status, channel
    - fact_marketing_perf: campaign_id, start_date, impressions, clicks, spend, revenue
    - dim_campaign: campaign_id, campaign_name, source, goal
    - customer_risk_scores: customer_id, name, churn_risk_score, risk_level
    Always use warehouse. prefix. Return ONLY raw SQL ending with semicolon.
    Never use LIMIT unless the user asks for a specific number.
    Use 'price' not 'total_amount' in fact_orders.
    """

    from pymongo import MongoClient
    from datetime import datetime

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    if "mongo_history" not in st.session_state:
        st.session_state.mongo_history = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if question := st.chat_input("Ask a question about your data..."):

        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "cohere/north-mini-code:free",
                        "messages": [
                            {"role": "system", "content": SCHEMA}
                        ] + st.session_state.messages
                    }
                )

                sql = response.json()["choices"][0]["message"]["content"]

                try:
                    cursor = db.cursor()
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    cols = [d[0] for d in cursor.description]
                    result_df = pd.DataFrame(rows, columns=cols)

                    st.markdown("**SQL generated:**")
                    st.code(sql, language="sql")
                    st.markdown("**Results:**")
                    st.dataframe(result_df, use_container_width=True)

                    answer = (
                        f"Here are the results for: *{question}*\n\n"
                        f"Found {len(result_df)} rows."
                    )

                except Exception as e:
                    answer = f"Query error: {str(e)}\n\nSQL attempted:\n```sql\n{sql}\n```"

                st.session_state.messages.append({"role": "assistant", "content": answer})

                # ── Save to MongoDB ───────────────────────────────
                try:
                    st.session_state.mongo_history.append({"role": "user", "content": question})
                    st.session_state.mongo_history.append({"role": "assistant", "content": sql})

                    mongo_client = MongoClient(
                    os.getenv("MONGO_URI"),
                    tls=True,
                    tlsAllowInvalidCertificates=True
            )
                    collection = mongo_client["ai_analyst"]["conversations"]

                    collection.update_one(
                        {"session_id": st.session_state.session_id},
                        {"$set": {
                            "session_id": st.session_state.session_id,
                            "started_at": datetime.now(),
                            "messages":   st.session_state.mongo_history,
                            "page":       "dashboard"
                        }},
                        upsert=True
                    )
                    st.caption("✓ Saved to MongoDB")

                except Exception as mongo_err:
                    st.caption(f"MongoDB error: {mongo_err}")
