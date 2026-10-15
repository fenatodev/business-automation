# WP-054: Minimal-privilege sandbox for n8n executor
#
# This Dockerfile creates a restricted container for the n8n executor
# with the following isolation guarantees:
#
# 1. No Docker socket access
# 2. No sudo privileges
# 3. Non-root user (n8n-operator) with /bin/sh shell (not nologin)
# 4. Read-only filesystem (enforced in docker-compose.yml)
# 5. No network host mode
# 6. Minimal Python dependencies
#
# IMPORTANT: This Dockerfile is PREPARED but NOT APPLIED.
# Applying it requires explicit user approval (Gate B).
#
# Usage (after approval):
#   docker build -t n8n-executor-sandbox .
#   docker compose -f ops/sandbox/docker-compose.yml up -d

FROM python:3.12-slim

# Do NOT install sudo, curl, or other privileged tools
# Only install minimal dependencies for the executor

# Create restricted user with /bin/sh shell (not nologin — CMD needs a shell)
RUN groupadd -r n8n-operator && \
    useradd -r -g n8n-operator -d /home/n8n-operator -s /bin/sh n8n-operator

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY pyproject.toml uv.lock ./
# Install minimal dependencies with version control from lockfile
# cryptography is required for Ed25519 asymmetric signature verification
RUN pip install --no-cache-dir httpx cryptography==50.0.2

# Copy __init__.py so that 'from app.services.xxx import ...' works inside the container
COPY app/__init__.py app/
COPY app/services/__init__.py app/services/

# Copy application code — only the services needed by the executor
COPY app/services/approval_gate.py app/services/
COPY app/services/n8n_executor.py app/services/

# Copy healthcheck and executor entry-point scripts
COPY ops/sandbox/healthcheck.py /app/healthcheck.py
COPY ops/sandbox/run_executor.py /app/run_executor.py

# Create journal directory with proper permissions
RUN mkdir -p /var/log/n8n-executor && \
    chown n8n-operator:n8n-operator /var/log/n8n-executor

# Switch to non-root user
USER n8n-operator

# Environment variables (set at runtime via docker-compose)
# - N8N_BASE_URL: n8n API URL
# - N8N_API_KEY: n8n API key
# - ED25519_PUBLIC_KEY: Ed25519 public key PEM (NO private key in executor)
# - LEDGER_PATH: Path to approval ledger SQLite database

# Health check: verify n8n API connectivity
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

# The executor runs as a long-lived polling loop waiting for approved operations.
# In the sandbox, it reads operations from a queue file and executes them
# after validating the Ed25519-signed approval (public key only, no private key).
CMD ["python", "/app/run_executor.py"]
