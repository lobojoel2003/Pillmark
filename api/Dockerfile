# syntax=docker/dockerfile:1.7
# Pillmark API and importer.
#   docker run ghcr.io/lobojoel2003/pillmark-api               -> serves the API on :8000
#   docker run ghcr.io/lobojoel2003/pillmark-api pillmark ...  -> runs the importer CLI

FROM python:3.13-slim AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip wheel --wheel-dir /wheels .

FROM python:3.13-slim
ARG VERSION=0.0.0-dev
ARG BUILD=local
ARG COMMIT=unknown
LABEL org.opencontainers.image.title="pillmark-api" \
      org.opencontainers.image.description="Pillmark open pill identifier: public API and DailyMed importer" \
      org.opencontainers.image.source="https://github.com/lobojoel2003/Pillmark" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${COMMIT}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PILLMARK_BUILD=${BUILD} \
    PILLMARK_COMMIT=${COMMIT}
RUN useradd --system --uid 10001 --create-home --home-dir /app pillmark
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
WORKDIR /app
USER pillmark
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health', timeout=4)"]
CMD ["uvicorn", "pillmark.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
