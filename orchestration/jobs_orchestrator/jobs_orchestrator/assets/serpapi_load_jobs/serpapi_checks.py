"""Declarative data checks for transformed SerpApi job rows."""

from jobs_orchestrator.resources.duckdb_check import NotNullCheck


SERPAPI_CHECKS = (
    NotNullCheck("source_name_not_null", "$.job_data.source_name"),
    NotNullCheck("query_id_not_null", "$.job_data.query_id"),
    NotNullCheck("q_not_null", "$.job_data.q"),
    NotNullCheck("location_not_null", "$.job_data.location"),
    NotNullCheck("fetched_at_not_null", "$.job_data.fetched_at"),
    NotNullCheck("job_job_id_not_null", "$.job_data.job.job_id"),
)
