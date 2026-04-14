FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (layer caching).
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Copy application code.
COPY megalos_server/ megalos_server/

# FastMCP reads these env vars for host/port binding.
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8000

EXPOSE 8000

# DB file lives at /app/megalos_server/megalos_sessions.db — mount a volume there
# to persist across container restarts:
#   docker run -v megalos-data:/app/megalos_server megalos-mcp
CMD ["uv", "run", "python", "-m", "megalos_server.main"]
