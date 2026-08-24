# app.py
import duckdb
import streamlit as st

from src.domain.entities import CustomerProfile
from src.domain.policy import UnderwritingPolicy
from src.infra.agents.agent_tools import (
    get_customer_financial_profile,
    get_sanitized_customer_notes,
)
from src.infra.agents.agents import run_audit_committee
from src.infra.config import DUCKDB_PATH

# ------------------------------------------------------------------
# Streamlit Page Setup
# ------------------------------------------------------------------
st.set_page_config(
    page_title="AI Credit Underwriting Platform",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ Enterprise AI Credit Underwriting Platform")
st.caption("Powered by DuckDB, XGBoost, and Local Llama 3.1 Multi-Agent System")

st.divider()

# ------------------------------------------------------------------
# Sidebar: Customer Selection
# ------------------------------------------------------------------
st.sidebar.header("Customer Selection")


def get_all_customers():
    """Fetches list of available customers from DuckDB."""
    with duckdb.connect(str(DUCKDB_PATH), read_only=True) as conn:
        df = conn.execute("SELECT customer_id, full_name FROM customers ORDER BY customer_id").df()
    return df


try:
    customers_df = get_all_customers()
    customer_options = {
        f"ID {row['customer_id']} - {row['full_name']}": row["customer_id"]
        for _, row in customers_df.iterrows()
    }
    selected_label = st.sidebar.selectbox("Select Customer Profile:", list(customer_options.keys()))
    selected_id = customer_options[selected_label]
except Exception as e:
    st.error(f"Failed to connect to DuckDB: {e}")
    st.stop()

# ------------------------------------------------------------------
# Main View: Customer Financial Profile
# ------------------------------------------------------------------
profile = get_customer_financial_profile(selected_id)

notes = get_sanitized_customer_notes(selected_id)

st.subheader(f"Financial Profile: {profile.get('full_name', 'Unknown')}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Credit Score", profile.get("credit_score", "N/A"))
with col2:
    st.metric("Debt-to-Income (DTI)", f"{profile.get('debt_to_income_ratio', 0.0) * 100:.1f}%")
with col3:
    st.metric("Annual Income", f"${profile.get('annual_income', 0):,.2f}")
with col4:
    xgb_score = float(profile.get("live_xgb_risk_score", 0.0))
    try:
        xgb_score = float(xgb_score) if xgb_score is not None else 0.0
    except (TypeError, ValueError):
        xgb_score = 0.0
    st.metric(
        "XGBoost Risk Score",
        f"{xgb_score:.4f}",
        delta="High Default Risk" if xgb_score > 0.5 else "Low Risk",
        delta_color="inverse",
    )

# PII Protection Status
st.info(f"**PII Masking Active:** CPF: `{profile.get('cpf')}` | Email: `{profile.get('email')}`")

with st.expander("View Sanitized Customer History / Underwriter Notes"):
    st.text_area("Raw Context Logs (Sanitized):", notes, height=100, disabled=True)

st.divider()

# ------------------------------------------------------------------
# Multi-Agent Audit Trigger
# ------------------------------------------------------------------
st.subheader("Multi-Agent Risk Audit Committee")

if st.button("Run AI Underwriting Audit Committee", type="primary", use_container_width=True):
    with st.spinner("Running 3-Agent Llama 3 Pipeline..."):
        # 1. Map raw DuckDB dictionary into CustomerProfile Domain Entity
        customer_entity = CustomerProfile.from_db_record(profile)

        # 2. Compute Quantitative Standing via Domain Policy
        quant_standing = UnderwritingPolicy.evaluate_quantitative_standing(
            credit_score=customer_entity.credit_score,
            dti=customer_entity.dti,
            xgb_score=xgb_score
        )

        # 3. Call Orchestrator Function (returns a dict with keys: 'quant_report', 'qual_report', 'cro_report')
        audit_results = run_audit_committee(
            profile=customer_entity,
            sanitized_notes=notes,
            xgb_score=xgb_score,
            quant_standing=quant_standing
        )

    st.success("Audit Complete!")

    # Render Results in Tabs
    tab1, tab2, tab3 = st.tabs(
        [
            "🏛️ CRO Executive Decision",
            "📊 Quantitative Report",
            "🔍 Qualitative Audit"
        ]
    )

    with tab1:
        st.markdown("### Final Executive Decision")

        cro_text = audit_results.get("cro_decision", "")
        if "REJECTED" in cro_text.upper():
            st.error("🔴 **FINAL DECISION: REJECTED**")
        elif "APPROVED" in cro_text.upper():
            st.success("🟢 **FINAL DECISION: APPROVED**")
        else:
            st.warning("🟡 **FINAL DECISION: MANUAL REVIEW REQUIRED**")

        st.markdown(cro_text)

    with tab2:
        st.markdown("### Quantitative Analyst Insights")
        st.write(audit_results.get("quant_analysis", ""))

    with tab3:
        st.markdown("### Qualitative & Behavioral Audit Insights")
        st.write(audit_results.get("qual_analysis", ""))
