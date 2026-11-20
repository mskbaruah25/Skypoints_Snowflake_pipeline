# syntax=docker/dockerfile:1
# BuildKit selects one named target per service. This does not run every service
# inside one container. Compose starts the project stack.

ARG AIRFLOW_BASE_IMAGE=apache/airflow:3.4.0-python3.11
ARG PYTHON_BASE_IMAGE=python:3.11.14-slim-bookworm
ARG JAVA_BASE_IMAGE=eclipse-temurin:17-jre-jammy
ARG GO_VERSION=1.24.8

# Compile the pinned Community server without relying on upstream latest images.
FROM golang:${GO_VERSION}-bookworm AS minio-builder
ARG MINIO_RELEASE=RELEASE.2025-10-15T17-29-55Z
ENV CGO_ENABLED=0
RUN GOBIN=/out go install github.com/minio/minio@${MINIO_RELEASE}

FROM debian:bookworm-slim AS minio
RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 minio \
    && useradd --uid 10001 --gid minio --no-create-home minio \
    && mkdir -p /data /queue \
    && chown -R minio:minio /data /queue
COPY --from=minio-builder /out/minio /usr/local/bin/minio
USER minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]

FROM ${JAVA_BASE_IMAGE} AS java-runtime

# Shared by the Airflow API, scheduler, DAG processor, and one-shot setup jobs.
FROM ${AIRFLOW_BASE_IMAGE} AS airflow
USER root
COPY --from=java-runtime /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"
RUN python -m venv /opt/spark-venv \
    && mkdir -p /opt/spark-extra-jars \
    && chown -R airflow:0 /opt/spark-venv /opt/spark-extra-jars
USER airflow
ARG PYSPARK_VERSION=3.5.7
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_BUNDLE_VERSION=1.12.262
ARG SNOWFLAKE_SPARK_VERSION=3.2.0-spark_3.5
ARG SNOWFLAKE_JDBC_VERSION=4.0.2
COPY --chown=airflow:0 requirements.lock requirements-spark.lock /tmp/
RUN pip install --no-cache-dir "apache-airflow==3.4.0" -r /tmp/requirements.lock \
    && /opt/spark-venv/bin/pip install --no-cache-dir \
       "pyspark==${PYSPARK_VERSION}" -r /tmp/requirements-spark.lock
# Fetch pinned Maven artifacts and verify repository-published checksums.
COPY --chown=airflow:0 scripts/download_spark_jars.py /tmp/download_spark_jars.py
RUN python /tmp/download_spark_jars.py \
    --hadoop-aws "${HADOOP_AWS_VERSION}" \
    --aws-sdk-bundle "${AWS_SDK_BUNDLE_VERSION}" \
    --snowflake-spark "${SNOWFLAKE_SPARK_VERSION}" \
    --snowflake-jdbc "${SNOWFLAKE_JDBC_VERSION}" \
    --output /opt/spark-extra-jars
COPY --chown=airflow:0 src /opt/airflow/src
COPY --chown=airflow:0 dags /opt/airflow/dags
COPY --chown=airflow:0 sql /opt/airflow/sql
COPY --chown=airflow:0 scripts /opt/airflow/scripts
ENV PYTHONPATH=/opt/airflow/src
ENV SKYPOINTS_SPARK_JARS=/opt/spark-extra-jars
# Retain the official Airflow entrypoint. Compose selects the Airflow command.

# Thin HTTP receiver; has no Java/Spark installation or Snowflake key.
FROM ${PYTHON_BASE_IMAGE} AS event-handler
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
COPY requirements-event-handler.lock /tmp/requirements-event-handler.lock
RUN pip install --no-cache-dir -r /tmp/requirements-event-handler.lock \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app
COPY src /app/src
USER app
CMD ["uvicorn", "skypoints.event_handler:app", "--host", "0.0.0.0", "--port", "8000"]

# The private generator is a named context supplied only for this build target.
# Its source remains outside the pipeline folder; no Git operation is involved.
FROM ${PYTHON_BASE_IMAGE} AS data-generator
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=generator_source /requirements.txt /tmp/generator-requirements.txt
RUN pip install --no-cache-dir -r /tmp/generator-requirements.txt \
    && groupadd --gid 10001 generator \
    && useradd --uid 10001 --gid generator --no-create-home generator \
    && mkdir -p /output \
    && chown generator:generator /output
# Copy only the generator's application directory, not its private seed datasets.
COPY --from=generator_source /app/ /app/
USER generator
CMD ["python", "/app/generate.py"]
