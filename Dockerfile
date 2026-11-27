# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Keep uv's managed Python outside /root so the non-root user can run it.
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python

RUN pip install --no-cache-dir uv \
    && useradd --create-home --uid 10001 mcp

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/

RUN uv sync --frozen --no-dev && chown -R mcp:mcp /app

USER mcp

# Inside the container only; publish the port on the host's loopback (see README).
ENV MANAGER_MCP_TRANSPORT=http
ENV MANAGER_MCP_HTTP_HOST=0.0.0.0
ENV MANAGER_MCP_HTTP_PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=5s --start-period=20s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"

CMD ["/app/.venv/bin/manager-mcp"]
