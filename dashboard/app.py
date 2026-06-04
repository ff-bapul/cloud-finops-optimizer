import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api")
API_KEY = os.getenv("API_KEY", "my-super-secret-api-key-123")
HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(page_title="Cloud Cost Optimizer", layout="wide", page_icon="☁️")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    /* Global Font & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    /* Reduce top padding without hiding header */
    .block-container, [data-testid="block-container"] {
        padding-top: 3rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        font-weight: 700;
        color: var(--text-color);
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #4f46e5;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #4338ca;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    /* Metrics Highlighting */
    div[data-testid="stMetricValue"] {
        color: #4f46e5;
        font-size: 2.2rem;
        font-weight: 800;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-color);
    }
    
    /* Containers & Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px;
        border: 1px solid var(--faded-text-10);
        background-color: var(--background-color);
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        padding: 1rem;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-color);
    }
    </style>
""", unsafe_allow_html=True)

st.title("☁️ Cloud Cost Optimizer & Remediation")
st.markdown("Automate cloud waste detection and orchestrate CLI remediation with dynamic metadata rules. Built with FastAPI and Streamlit.")

# --- DATA FETCHING ---
@st.cache_data(ttl=5)
def fetch_findings():
    try:
        r = requests.get(f"{API_URL}/findings", headers=HEADERS)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=5)
def fetch_rules():
    try:
        r = requests.get(f"{API_URL}/rules", headers=HEADERS)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=5)
def fetch_remediations():
    try:
        r = requests.get(f"{API_URL}/remediation", headers=HEADERS)
        return r.json() if r.status_code == 200 else []
    except:
        return []

findings = fetch_findings()
rules = fetch_rules()
remediations = fetch_remediations()

# --- PREPARE DATA ---
df_findings = pd.DataFrame(findings) if findings else pd.DataFrame(columns=["id", "status", "potential_savings", "rule_id"])
df_rules = pd.DataFrame(rules) if rules else pd.DataFrame(columns=["id", "severity", "resource_type", "enabled", "provider"])

if not df_findings.empty and not df_rules.empty:
    df_merged = pd.merge(df_findings, df_rules, left_on="rule_id", right_on="id", suffixes=("_finding", "_rule"))
    
    # Handle duplicate provider column after adding provider to findings schema
    if "provider_rule" in df_merged.columns:
        df_merged["provider"] = df_merged["provider_rule"]
        
    high_severity_count = len(df_merged[df_merged["severity"] == "High"])
else:
    df_merged = pd.DataFrame(columns=["severity", "potential_savings", "resource_type", "provider"])
    high_severity_count = 0

total_findings = len(df_findings)
potential_savings = df_findings["potential_savings"].sum() if not df_findings.empty else 0.0

# --- METRICS ROW ---
st.markdown("### 📊 Platform Overview")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Findings", total_findings)
with col2:
    st.metric("Potential Savings", f"${potential_savings:,.2f}")
with col3:
    st.metric("High Severity", high_severity_count)
with col4:
    st.metric("Active Rules", len([r for r in rules if r.get('enabled')]))

st.divider()

# --- ACTIONS ---
st.markdown("### ⚙️ Engine Controls")
col_upload, col_analyze = st.columns([1.3, 1])

with col_upload:
    with st.container(border=True):
        st.subheader("📥 Data Ingestion")
        st.markdown("Upload standard AWS/Azure billing exports (`.csv` or `.json`).")
        with st.form("upload_form", clear_on_submit=True):
            uploaded_file = st.file_uploader("Select Billing File", type=["csv", "json"], label_visibility="collapsed")
            provider = st.selectbox("Cloud Provider", ["AWS", "Azure"])
            submit_upload = st.form_submit_button("Ingest Data", use_container_width=True)
            
            if submit_upload and uploaded_file is not None:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {"provider": provider}
                with st.spinner("Ingesting resources..."):
                    try:
                        res = requests.post(f"{API_URL}/upload", files=files, data=data, headers=HEADERS)
                        if res.status_code == 200:
                            st.success(res.json().get("message", "Success"))
                            fetch_findings.clear()
                            st.rerun()
                        else:
                            st.error(res.text)
                    except Exception as e:
                        st.error(f"Backend Connection Error: {e}")

with col_analyze:
    with st.container(border=True):
        st.subheader("🧠 Rule Engine")
        st.markdown("Evaluate ingested resources against the active rule catalog.")
        st.write("") # spacing
        st.write("") # spacing
        if st.button("🚀 Analyze & Generate Remediations", use_container_width=True):
            with st.spinner("Executing simpleeval expressions..."):
                try:
                    res = requests.post(f"{API_URL}/analyze", headers=HEADERS)
                    if res.status_code == 200:
                        st.success(res.json().get("message", "Analysis complete"))
                        fetch_findings.clear()
                        fetch_remediations.clear()
                        st.rerun()
                    else:
                        st.error(res.text)
                except Exception as e:
                    st.error(f"Backend Connection Error: {e}")

st.divider()

# --- VISUALIZATIONS ---
st.markdown("### 📈 Optimization Insights")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    with st.container(border=True):
        if not df_merged.empty:
            sev_counts = df_merged["severity"].value_counts().reset_index()
            sev_counts.columns = ["Severity", "Count"]
            fig1 = px.pie(
                sev_counts, 
                names="Severity", 
                values="Count", 
                title="Findings Distributed by Severity", 
                hole=0.5,
                color="Severity",
                color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}
            )
            fig1.update_layout(margin=dict(t=50, b=20, l=20, r=20))
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No data available for severity chart. Run an analysis.")

with chart_col2:
    with st.container(border=True):
        if not df_merged.empty:
            res_savings = df_merged.groupby(["provider", "resource_type"])["potential_savings"].sum().reset_index()
            fig2 = px.bar(
                res_savings, 
                x="resource_type", 
                y="potential_savings", 
                title="Potential Savings by Resource Type & Provider", 
                labels={"resource_type":"Resource Type", "potential_savings":"Savings ($)", "provider": "Provider"},
                color="provider",
                barmode="group",
                color_discrete_sequence=["#3b82f6", "#8b5cf6", "#ec4899", "#10b981"]
            )
            fig2.update_layout(margin=dict(t=50, b=20, l=20, r=20))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data available for savings chart. Run an analysis.")

st.divider()

# --- TABLES ---
st.markdown("### 📋 Platform Data Explorer")
tab1, tab2, tab3 = st.tabs(["🎯 Open Findings", "🔧 Remediation Queue", "📚 Rule Catalog"])

with tab1:
    if not df_findings.empty:
        st.dataframe(df_findings, use_container_width=True, hide_index=True)
    else:
        st.info("No findings currently open.")

with tab2:
    if remediations:
        df_rem = pd.DataFrame(remediations)
        st.dataframe(df_rem, use_container_width=True, hide_index=True)
    else:
        st.info("No remediations generated.")

with tab3:
    if rules:
        df_full_rules = pd.DataFrame(rules)
        st.dataframe(df_full_rules, use_container_width=True, hide_index=True)
    else:
        st.info("No rules configured. Please seed the database.")
