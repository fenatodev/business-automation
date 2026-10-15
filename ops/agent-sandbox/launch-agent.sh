#!/bin/sh
# WP-057: Junie Agent Launcher
#
# This script launches the Junie CLI in an isolated environment.
# It handles authentication, workspace setup, and safety checks.
#
# The launcher runs inside the sandbox container and does NOT have access to:
# - Docker socket
# - sudo/LXD
# - User's real home directory
# - n8n SQLite database
# - SSH agent or ~/.config
# - MCP servers that can control the host
#
# Usage:
#   /workspace/launch-agent.sh
#
# Environment variables (set at runtime via docker-compose):
#   JUNIE_API_KEY: Junie API key for authentication (required)
#   GIT_TOKEN: Reduced-scope Git token for repository access (optional)
#   TASK: The task to execute in headless mode (optional)

set -e

# Safety checks — fail if any host resource is accessible
check_isolation() {
    # Docker socket must NOT be accessible
    if [ -S /var/run/docker.sock ]; then
        echo "ERROR: Docker socket is accessible — isolation compromised"
        exit 1
    fi

    # LXD socket must NOT be accessible
    if [ -S /var/lib/lxd/unix.socket ] || [ -S /var/lib/lxd/socket ]; then
        echo "ERROR: LXD socket is accessible — isolation compromised"
        exit 1
    fi

    # User's real home must NOT be mounted
    if [ -d /home/fenatodev/.ssh ]; then
        echo "ERROR: User's SSH directory is accessible — isolation compromised"
        exit 1
    fi

    # n8n data must NOT be mounted
    if [ -d /var/lib/n8n ]; then
        echo "ERROR: n8n data directory is accessible — isolation compromised"
        exit 1
    fi

    # SSH agent must NOT be accessible
    if [ -n "$SSH_AUTH_SOCK" ] && [ -S "$SSH_AUTH_SOCK" ]; then
        echo "ERROR: SSH agent socket is accessible — isolation compromised"
        exit 1
    fi

    echo "Isolation checks passed"
}

# Configure Git with reduced-scope token if available
configure_git() {
    if [ -n "$GIT_TOKEN" ]; then
        git config --global credential.helper 'store --file=/var/log/junie-agent/.git-credentials'
        echo "https://x-access-token:${GIT_TOKEN}@github.com" > /var/log/junie-agent/.git-credentials
        echo "Git configured with reduced-scope token"
    else
        echo "WARNING: No Git token configured — Git operations may fail"
    fi
}

# Launch Junie CLI in headless mode
launch_junie() {
    if [ -z "$JUNIE_API_KEY" ]; then
        echo "ERROR: JUNIE_API_KEY not set — cannot authenticate"
        exit 1
    fi

    if [ -n "$TASK" ]; then
        echo "Starting Junie in headless mode with task..."
        junie --auth="$JUNIE_API_KEY" --sandbox "$TASK"
    else
        echo "Starting Junie in sandbox mode..."
        junie --auth="$JUNIE_API_KEY" --sandbox
    fi
}

# Main execution
echo "Junie Agent Launcher starting..."
echo "================================"
echo "User: $(whoami)"
echo "Home: $HOME"
echo "Junie Home: $JUNIE_HOME"
echo "================================"

check_isolation
configure_git

if command -v junie >/dev/null 2>&1; then
    launch_junie
else
    echo "WARNING: Junie CLI not found in PATH — running Python tests instead"
    echo "This is expected in a build-only container"
    echo "To run Junie CLI, install it first or use the full image"
    
    # Fallback: run project tests to validate the environment
    if [ -f /workspace/pyproject.toml ]; then
        echo "Running project tests..."
        cd /workspace
        python -m pytest tests/ -v --tb=short || true
    fi
fi

echo "Junie Agent Launcher finished"
