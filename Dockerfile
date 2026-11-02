# Build the React UI in an isolated stage; model weights are never downloaded.
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts=false
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ATEVAL_HOME=/data \
    ATEVAL_UPLOAD_LIMIT_BYTES=26214400 \
    PORT=8000
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE THIRD_PARTY_NOTICES.md ./
COPY ateval ./ateval
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir '.[ui-server,writing-docs]' \
    && useradd --system --uid 10001 --create-home --home-dir /home/ateval ateval \
    && mkdir -p /data \
    && chown -R ateval:ateval /data /app
COPY --from=frontend-build --chown=ateval:ateval /app/frontend/dist/client /app/frontend/dist/client
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)" || exit 1
STOPSIGNAL SIGTERM
CMD ["python", "-m", "ateval", "api", "--host", "0.0.0.0"]
