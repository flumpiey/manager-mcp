# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# tzdata gives glibc's localtime() (and hence `%(asctime)s` in logs) access
# to named zones via the TZ env var; python:3.12-slim doesn't include it.
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/

RUN uv sync --frozen --no-dev

ENV MANAGER_MCP_TRANSPORT=http
ENV MANAGER_MCP_HTTP_HOST=0.0.0.0
ENV MANAGER_MCP_HTTP_PORT=8080
# MANAGER_MCP_BANK_FEED_CONFIG_PATH defaults to /app/feeds.config
# (feeds_config.py), this WORKDIR, so no ENV override is needed here for a
# standalone container; a deployment that wants it on a mounted volume
# instead sets that env var to point there.
EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=5s --start-period=20s \
  CMD python3 -c "import socket; socket.create_connection(('127.0.0.1', 8080), timeout=3)"

CMD ["uv", "run", "manager-mcp"]
