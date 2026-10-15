# WP-057: Junie Agent Sandbox
#
# This Dockerfile creates a restricted container for the Junie agent process
# itself, not just the n8n executor. The goal is to confine the agent so that
# it cannot access Docker socket, sudo, LXD, n8n SQLite, secrets, or the
# user's real home directory.
#
# Key isolation guarantees:
# 1. Non-root user (no sudo, no docker group, no lxd group)
# 2. Read-only filesystem (with specific writable directories)
# 3. No Docker socket mount
# 4. No n8n data directory mount
# 5. No host network access (--network none for testing)
# 6. no-new-privileges security option
# 7. Resource limits (CPU/memory)
# 8. No MCP servers that can control the host
# 9. No access to user's real home directory
# 10. No SSH agent or ~/.config mount
#
# IMPORTANT: This configuration is PREPARED but NOT APPLIED.
# Applying it requires explicit user approval (Gate B).
#
# The Junie CLI can run in headless mode inside this container, but:
# - Authentication requires JUNIE_API_KEY (not browser session)
# - Git access requires a reduced-scope token or mediated transfer
# - Brave mode behavior is controlled by config, not host privileges
#
# Usage (after approval):
#   docker compose -f ops/agent-sandbox/docker-compose.yml up -d
#
# Rollback:
#   docker compose -f ops/agent-sandbox/docker-compose.yml down

FROM python:3.12-slim

# Install minimal dependencies
# Junie CLI is a Java application (JAR) installed via official curl script
# It requires JRE but does NOT support --sandbox in release builds
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Install Junie CLI officially — FAIL IMMEDIATELY if installation fails
# The official installer downloads the shim + latest release version
# NOTE: --sandbox flag is ONLY available in dev/nightly/experimental builds
# Release builds (like the one installed here) do NOT support --sandbox
RUN curl -fsSL https://junie.jetbrains.com/install.sh | bash && \
    ln -s /root/.local/bin/junie /usr/local/bin/junie

# Verify Junie CLI installation — FAIL BUILD if not installed
RUN junie --version

# Create non-root user without privileged groups
# This user has NO docker, sudo, or lxd groups
RUN groupadd -g 1000 junie-agent && \
    useradd -u 1000 -g junie-agent -m -s /bin/sh junie-agent

# Create workspace directory with proper ownership
RUN mkdir -p /workspace /var/log/junie-agent /tmp/junie-agent && \
    chown junie-agent:junie-agent /workspace /var/log/junie-agent /tmp/junie-agent

# Set working directory
WORKDIR /workspace

# Copy project files (will be mounted as volume in production)
# For build validation, we copy the project structure
COPY --chown=junie-agent:junie-agent pyproject.toml uv.lock ./
COPY --chown=junie-agent:junie-agent app/ app/
COPY --chown=junie-agent:junie-agent tests/ tests/
COPY --chown=junie-agent:junie-agent ops/ ops/

# Install Python dependencies with version control
RUN pip install --no-cache-dir httpx cryptography==50.0.2

# Copy Junie agent sandbox configuration
# IMPORTANT: These files are copied BEFORE volume mounts in docker-compose.
# The volume mounts will shadow them at runtime, but they exist in the image
# for validation purposes (docker run without volumes).
COPY --chown=junie-agent:junie-agent ops/agent-sandbox/sandbox.json /var/log/junie-agent/sandbox.json
COPY --chown=junie-agent:junie-agent ops/agent-sandbox/launch-agent.sh /workspace/launch-agent.sh
RUN chmod +x /workspace/launch-agent.sh

# Copy healthcheck script
COPY --chown=junie-agent:junie-agent ops/agent-sandbox/healthcheck.py /workspace/healthcheck.py

# Copy __init__.py files for Python package imports
COPY --chown=junie-agent:junie-agent ops/__init__.py ops/
COPY --chown=junie-agent:junie-agent ops/agent-sandbox/__init__.py ops/agent-sandbox/

# Switch to non-root user
USER junie-agent

# Set environment variables for isolated operation
ENV HOME=/workspace
ENV JUNIE_HOME=/var/log/junie-agent
ENV PATH=/usr/local/bin:/usr/bin:/bin:/workspace/.venv/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Do NOT set JUNIE_API_KEY here — it must be injected at runtime
# Do NOT mount ~/.config or ~/.junie from host
# Do NOT mount Docker socket
# Do NOT mount n8n data directory

# Health check: verify agent can start without accessing host resources
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD ["python", "/workspace/healthcheck.py"]

# The launcher script handles authentication, workspace setup, and Junie CLI invocation
CMD ["/workspace/launch-agent.sh"]
