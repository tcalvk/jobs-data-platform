import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import plotly.express as px

st.set_page_config(page_title="Jobs Dashboard", layout="wide")

def get_bq_client():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(
        credentials=credentials,
        project=st.secrets["gcp_service_account"]["project_id"],
    )

@st.cache_data(ttl=600)
def load_data():
    client = get_bq_client()
    query = """
        SELECT
            DATE(created_at_utc) AS created_date,
            search_term,
            COUNT(job_id) AS job_count
        FROM `projects-portfolio-446806.reporting.jobs_detail_report`
        GROUP BY 1, 2
        ORDER BY 1
    """
    return client.query(query).to_dataframe()

@st.cache_data(ttl=600)
def load_summary_metrics(selected_terms: tuple):
    client = get_bq_client()
    term_filter = f"AND search_term IN UNNEST({list(selected_terms)})" if selected_terms else ""

    active_jobs = client.query(f"""
        SELECT COUNT(*) AS cnt
        FROM `projects-portfolio-446806.reporting.jobs_detail_report`
        WHERE listing_status = 'Active' {term_filter}
    """).to_dataframe()["cnt"][0]

    new_jobs = client.query(f"""
        SELECT COUNT(*) AS cnt
        FROM `projects-portfolio-446806.reporting.jobs_detail_report`
        WHERE posted_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) {term_filter}
    """).to_dataframe()["cnt"][0]

    companies = client.query(f"""
        SELECT COUNT(DISTINCT company_name) AS cnt
        FROM `projects-portfolio-446806.reporting.jobs_detail_report`
        WHERE 1=1 {term_filter}
    """).to_dataframe()["cnt"][0]

    return int(active_jobs), int(new_jobs), int(companies)


df = load_data()

all_terms = sorted(df["search_term"].dropna().unique().tolist())
selected_terms = st.multiselect("Search Term", options=all_terms, default=all_terms)

active_jobs, new_jobs, companies_hiring = load_summary_metrics(tuple(selected_terms))

st.header("Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Active Jobs", f"{active_jobs:,}")
col2.metric("New Jobs (Last 7 Days)", f"{new_jobs:,}")
col3.metric("Companies Hiring", f"{companies_hiring:,}")

st.divider()

filtered = df[df["search_term"].isin(selected_terms)] if selected_terms else df

st.subheader("Jobs Created over Time")

pivot = (
    filtered.pivot_table(
        index="created_date", columns="search_term", values="job_count", aggfunc="sum", fill_value=0
    )
    .reset_index()
)

fig = px.bar(
    pivot,
    x="created_date",
    y=[c for c in pivot.columns if c != "created_date"],
    labels={"created_date": "Date", "value": "Job Count", "variable": "Search Term"},
    barmode="stack",
)
fig.update_layout(legend_title_text="Search Term", xaxis_title="Date", yaxis_title="Job Count")

st.plotly_chart(fig, use_container_width=True)
