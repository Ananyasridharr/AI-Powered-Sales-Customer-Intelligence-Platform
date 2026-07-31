import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import requests
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

load_dotenv()

st.set_page_config(page_title="NexusIQ", page_icon="📊", layout="wide")
os.environ["no_proxy"] = "*"

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"), keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5)

def run_query(query):
    try:
        conn = get_connection()
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def run_cursor(sql):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return rows, cols

@st.cache_data(ttl=300)
def load_risk_scores():
    return run_query("SELECT name, city, segment, churn_risk_score, risk_level, total_orders, total_spent, ticket_count, avg_satisfaction, days_since_last_order FROM warehouse.customer_risk_scores ORDER BY churn_risk_score DESC")

@st.cache_data(ttl=300)
def load_revenue_by_category():
    return run_query("SELECT p.category, SUM(o.price) AS total_revenue, COUNT(o.order_id) AS total_orders FROM warehouse.fact_orders o JOIN warehouse.dim_product p ON o.product_id = p.product_id GROUP BY p.category ORDER BY total_revenue DESC")

@st.cache_data(ttl=300)
def load_revenue_by_city():
    return run_query("SELECT c.city, SUM(o.price) AS total_revenue, COUNT(DISTINCT o.customer_id) AS customers FROM warehouse.fact_orders o JOIN warehouse.dim_customer c ON o.customer_id = c.customer_id GROUP BY c.city ORDER BY total_revenue DESC LIMIT 15")

@st.cache_data(ttl=300)
def load_marketing_performance():
    query = """
    SELECT
        dc.source,
        SUM(f.spend) AS total_spend,
        SUM(f.revenue) AS total_revenue,
        ROUND(
            (SUM(f.revenue) / NULLIF(SUM(f.spend), 0))::numeric,
            2
        ) AS roas
    FROM warehouse.fact_marketing_perf f
    JOIN warehouse.dim_campaign dc
        ON f.campaign_id = dc.campaign_id
    GROUP BY dc.source
    ORDER BY roas DESC;
    """
    return run_query(query)
@st.cache_data(ttl=300)
def load_support_summary():
    return run_query("SELECT issue_type, COUNT(*) AS ticket_count, ROUND(AVG(resolution_hours)::numeric, 1) AS avg_hours, ROUND(AVG(satisfaction_score)::numeric, 2) AS avg_satisfaction FROM warehouse.fact_support_tickets GROUP BY issue_type ORDER BY avg_hours DESC")

st.sidebar.title("NexusIQ")
st.sidebar.caption("Sales Intelligence Platform")
page = st.sidebar.radio("Navigate", ["Overview", "Customer Risk", "Marketing", "Support", "AI Analyst"])

if page == "Overview":
    st.title("Sales & Customer Intelligence")
    st.caption("Powered by Neon PostgreSQL + AI")
    risk_df = load_risk_scores()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", f"{len(risk_df):,}")
    col2.metric("High Risk", f"{(risk_df['risk_level']=='High Risk').sum():,}", delta="-needs attention", delta_color="inverse")
    col3.metric("Avg Risk Score", f"{risk_df['churn_risk_score'].mean():.1f}/100")
    col4.metric("Total Revenue", f"${risk_df['total_spent'].sum():,.0f}")
    st.divider()
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Revenue by product category")
        cat_df = load_revenue_by_category()
        fig = px.bar(cat_df, x="category", y="total_revenue", color="total_revenue", color_continuous_scale="purples", labels={"total_revenue": "Revenue ($)", "category": "Category"})
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        st.subheader("Top 15 cities by revenue")
        city_df = load_revenue_by_city()
        fig2 = px.bar(city_df, x="total_revenue", y="city", orientation="h", color="total_revenue", color_continuous_scale="teal", labels={"total_revenue": "Revenue ($)", "city": "City"})
        fig2.update_layout(showlegend=False, coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig2, use_container_width=True)

elif page == "Customer Risk":
    st.title("Customer Churn Risk")
    st.caption("Scores from Random Forest ML model")
    risk_df = load_risk_scores()
    col1, col2, col3 = st.columns(3)
    col1.metric("High Risk", f"{(risk_df['risk_level']=='High Risk').sum():,}", delta="above 75")
    col2.metric("Medium Risk", f"{(risk_df['risk_level']=='Medium Risk').sum():,}", delta="50-75")
    col3.metric("Low Risk", f"{(risk_df['risk_level']=='Low Risk').sum():,}", delta="below 50")
    st.divider()
    col_left, col_right = st.columns([1, 2])
    with col_left:
        st.subheader("Risk distribution")
        dist_df = risk_df["risk_level"].value_counts().reset_index()
        dist_df.columns = ["Risk Level", "Count"]
        fig = px.pie(dist_df, names="Risk Level", values="Count", color="Risk Level", color_discrete_map={"High Risk": "#E24B4A", "Medium Risk": "#BA7517", "Low Risk": "#1D9E75"})
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        st.subheader("Risk score vs days inactive")
        fig2 = px.scatter(risk_df.sample(min(2000, len(risk_df))), x="days_since_last_order", y="churn_risk_score", color="risk_level", color_discrete_map={"High Risk": "#E24B4A", "Medium Risk": "#BA7517", "Low Risk": "#1D9E75"}, hover_data=["name", "city", "segment"], opacity=0.6)
        st.plotly_chart(fig2, use_container_width=True)
    st.divider()
    st.subheader("Customer risk table")
    risk_filter = st.selectbox("Filter by risk level", ["All", "High Risk", "Medium Risk", "Low Risk"])
    filtered = risk_df if risk_filter == "All" else risk_df[risk_df["risk_level"] == risk_filter]
    st.dataframe(filtered[["name","city","segment","churn_risk_score","risk_level","total_orders","total_spent","ticket_count","avg_satisfaction","days_since_last_order"]].reset_index(drop=True), use_container_width=True, height=400)

elif page == "Marketing":

    st.title("Marketing Performance")

    mkt_df = load_marketing_performance()

    if mkt_df.empty:
        st.warning("No marketing data available.")
        st.stop()

    for _, row in mkt_df.iterrows():
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Channel", row["source"])
        col2.metric("Total Spend", f"${row['total_spend']:,.0f}")
        col3.metric("Total Revenue", f"${row['total_revenue']:,.0f}")
        col4.metric("ROAS", f"{row['roas']}x")

        st.divider()

    fig = px.bar(
        mkt_df,
        x="source",
        y=["total_spend", "total_revenue"],
        barmode="group",
        labels={
            "value": "Amount ($)",
            "variable": "Metric",
            "source": "Channel"
        },
        color_discrete_map={
            "total_spend": "#AFA9EC",
            "total_revenue": "#534AB7"
        }
    )

    fig.update_layout(
        xaxis_title="Marketing Channel",
        yaxis_title="Amount ($)",
        legend_title=""
    )

    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(
        mkt_df,
        x="source",
        y="roas",
        text="roas",
        color="roas",
        color_continuous_scale="Purples",
        labels={
            "source": "Channel",
            "roas": "ROAS"
        }
    )

    fig2.update_traces(texttemplate="%{text:.2f}x", textposition="outside")

    st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(mkt_df, use_container_width=True)
elif page == "Support":
    st.title("Support Performance")
    sup_df = load_support_summary()
    fig = px.bar(sup_df, x="avg_hours", y="issue_type", orientation="h", color="avg_satisfaction", color_continuous_scale="RdYlGn", labels={"avg_hours": "Avg resolution hours", "issue_type": "Issue type", "avg_satisfaction": "Avg satisfaction"})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sup_df, use_container_width=True)

elif page == "AI Analyst":
    st.title("AI Analyst")
    st.caption("Ask anything about your data in plain English")
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    SCHEMA = """You are an expert SQL analyst. Use these PostgreSQL tables in the warehouse schema:
    - warehouse.fact_orders: order_id, customer_id, product_id, order_date, quantity, price
    - warehouse.dim_customer: customer_id, name, city, segment, signup_date
    - warehouse.dim_product: product_id, product_name, category, brand, price_min, price_max
    - warehouse.fact_support_tickets: ticket_id, customer_id, issue_type, resolution_hours, satisfaction_score, resolution_status, channel
    - warehouse.fact_marketing_perf: campaign_id, start_date, impressions, clicks, spend, revenue
    - warehouse.dim_campaign: campaign_id, campaign_name, source, goal
    - warehouse.customer_risk_scores: customer_id, name, churn_risk_score, risk_level, total_orders, total_spent, days_since_last_order
    Return ONLY raw SQL ending with semicolon. No markdown. No explanation. Always use warehouse. prefix."""
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
                response = requests.post(url="https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, json={"model": "mistralai/mistral-7b-instruct:free", "messages": [{"role": "system", "content": SCHEMA}] + st.session_state.messages})
                response_json = response.json()
                if "choices" not in response_json:
                    st.error(f"OpenRouter error: {response_json}")
                    st.stop()
                sql = response_json["choices"][0]["message"]["content"].strip()
                try:
                    rows, cols = run_cursor(sql)
                    result_df = pd.DataFrame(rows, columns=cols)
                    st.markdown("**SQL generated:**")
                    st.code(sql, language="sql")
                    st.markdown("**Results:**")
                    st.dataframe(result_df, use_container_width=True)
                    st.caption(f"{len(result_df):,} rows returned")
                    answer = f"Results for: *{question}* — {len(result_df):,} rows."
                except Exception as e:
                    answer = f"Query error: {str(e)}\n\nSQL:\n```sql\n{sql}\n```"
                    st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                try:
                    st.session_state.mongo_history.append({"role": "user", "content": question})
                    st.session_state.mongo_history.append({"role": "assistant", "content": sql})
                    mongo_client = MongoClient(os.getenv("MONGO_URI"), tls=True, tlsAllowInvalidCertificates=True)
                    collection = mongo_client["ai_analyst"]["conversations"]
                    collection.update_one({"session_id": st.session_state.session_id}, {"$set": {"session_id": st.session_state.session_id, "started_at": datetime.now(), "messages": st.session_state.mongo_history}}, upsert=True)
                    st.caption("Saved to MongoDB")
                except Exception as mongo_err:
                    st.caption(f"MongoDB: {mongo_err}")
