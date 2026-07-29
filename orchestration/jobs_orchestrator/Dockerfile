FROM python:3.12-slim

ARG DAGSTER_VERSION

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/jobs-data-platform

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY orchestration/jobs_orchestrator/requirements-prod.txt \
    /opt/jobs-data-platform/requirements-prod.txt

RUN pip install --no-cache-dir \
    -r /opt/jobs-data-platform/requirements-prod.txt

RUN pip install --no-cache-dir \
    "dagster-postgres==${DAGSTER_VERSION}" \
    "dagster-docker==${DAGSTER_VERSION}"

COPY orchestration/jobs_orchestrator \
    /opt/jobs-data-platform/orchestration/jobs_orchestrator

RUN pip install --no-cache-dir \
    --editable \
    /opt/jobs-data-platform/orchestration/jobs_orchestrator

EXPOSE 4000

CMD ["dagster", "api", "grpc", "--host", "0.0.0.0", "--port", "4000", "--module-name", "jobs_orchestrator.definitions"]
