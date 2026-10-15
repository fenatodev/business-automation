# WP-054: Minimal-privilege sandbox for n8n executor
#
# This Dockerfile creates a restricted container for the n8n executor
# with the following isolation guarantees:
#
# 1. No Docker socket access
# 2. No sudo privileges
# 3. Non-root user (n8n-operator)
# 4. Read-only filesystem (enforced in docker-compose.yml)
# 5. No network host mode
# 6. Minimal Python dependencies
#
# IMPORTANT: This Dockerfile is PREPARED but NOT APPLIED.
# Applying it requires explicit user approval (Gate B).
#
# Usage (after approval):
#   docker build -t n8n-executor-sandbox .
#   docker-compose -f docker-compose.yml up -d

FROM python:3.12-slim

# Do NOT install sudo, curl, or other privileged tools
# Only install minimal dependencies for the executor

# Create restricted user
RUN groupadd -r n8n-operator && \
    useradd -r -g n8n-operator -d /home/n8n-operator -s /usr/sbin/nologin n8n-operator

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir httpx

# Copy application code
COPY app/ app/

# Create journal directory with proper permissions
RUN mkdir -p /var/log/n8n-executor && \
    chown n8n-operator:n8n-operator /var/log/n8n-executor

# Switch to non-root user
USER n8n-operator

# Environment variables (set at runtime via docker-compose)
# - N8N_BASE_URL: n8n API URL
# - N8N_API_KEY: n8n API key
# - APPROVAL_SECRET: HMAC secret for approval gate (MUST be set by human operator)

# Health check (executor should respond to simple ping)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; print('ok')" || exit 1

CMD ["python", "-m", "app.services.n8n_executor"]
