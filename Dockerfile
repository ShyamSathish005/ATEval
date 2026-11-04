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
COPY pyproject.toml uv.lock README.md LICENSE NOTICE THIRD_PARTY_NOTICES.md ./
COPY ateval ./ateval
COPY --from=frontend-build /app/frontend/dist/client ./ateval/static
COPY --from=frontend-build /app/frontend/dist/client ./frontend/dist/client
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.2 uv==0.13.6 \
    && uv export --locked --no-dev --extra ui-server --extra writing-docs --no-emit-project --format requirements.txt --output-file /tmp/requirements.txt \
    && python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt \
    && python -m pip install --no-cache-dir --no-deps . \
    && rm -f /tmp/requirements.txt \
    && useradd --system --uid 10001 --create-home --home-dir /home/ateval ateval \
    && mkdir -p /data \
    && chown -R ateval:ateval /data /app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import os, urllib.request; p = int(os.environ.get('PORT', '8000')); assert 1 <= p <= 65535; urllib.request.urlopen(f'http://127.0.0.1:{p}/api/v1/health', timeout=2)" || exit 1
STOPSIGNAL SIGTERM
CMD ["python", "-m", "ateval", "api", "--host", "0.0.0.0"]
