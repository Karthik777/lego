# Use the official uv image with Python 3.13
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
# uv environment variables for optimization
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies (without project code)
COPY --link pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY --link lego/ lego/
COPY --link config-templates/ config-templates/
COPY --link static/ static/
COPY --link readme.md .
COPY --link main.py .

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Production image with matching Python version
FROM python:3.13-slim-bookworm
# Set environment variables
# Define build arguments
ARG CF_ACCESS_KEY_ID
ARG CF_SCRT_ACCESS_KEY
ARG CF_ENDPOINT
ARG PORT
ARG APP_NAME
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH" PORT=$PORT UVICORN_RELOAD=true

WORKDIR /app


# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates rclone gettext-base && rm -rf /var/lib/apt/lists/*

# Copy the application from builder stage
COPY --from=builder /app /app

# Create data directory with proper permissions
RUN mkdir -p /app/data/db /app/data/logs /app/backups /app/.config/rclone

ENV CF_ACCESS_KEY_ID=$CF_ACCESS_KEY_ID \
    CF_SCRT_ACCESS_KEY=$CF_SCRT_ACCESS_KEY \
    CF_ENDPOINT=$CF_ENDPOINT \
    RCLONE_CONFIG=/app/.config/rclone/rclone.conf \
    APP_NAME=$APP_NAME

RUN envsubst < /app/config-templates/rclone.conf > /app/.config/rclone/rclone.conf
# Set environment variables
# Define volume for persistent data
VOLUME ["/app/data"]
VOLUME ["/app/backups"]

# Expose port
EXPOSE $PORT
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5001/health')" || exit 1

# Run the application
CMD ["python", "main.py"]
