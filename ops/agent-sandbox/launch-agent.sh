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
# IMPORTANT: Never persist tokens in plaintext. Use environment variable
# injection only — no credential.helper store, no file writes with tokens.
configure_git() {
    if [ -n "$GIT_TOKEN" ]; then
        # Use GIT_CONFIG environment variables for ephemeral credential config
        # This does NOT write any file — the token stays in memory only
        export GIT_CONFIG_COUNT=3
        export GIT_CONFIG_KEY_0="credential\x20helper"
        export GIT_CONFIG_VALUE_0="cache --timeout=300"
        export GIT_CONFIG_KEY_1="credential\x20useHttpPath"
        export GIT_CONFIG_VALUE_1="true"
        export GIT_CONFIG_KEY_2="url\x20https://github.com/.insteadOf"
        export GIT_CONFIG_VALUE_2="git@github.com:"
        echo "Git configured with ephemeral settings (no token persistence)"
    else
        echo "WARNING: No Git token configured — Git operations may fail"
    fi
}

# Launch Junie CLI in headless mode
# NOTE: --sandbox flag is ONLY available in dev/nightly/experimental builds.
# Release builds do NOT support --sandbox. The container isolation provides
# the sandbox guarantees, not the Junie CLI flag.
launch_junie() {
    if [ -z "$JUNIE_API_KEY" ]; then
        echo "ERROR: JUNIE_API_KEY not set — cannot authenticate"
        exit 1
    fi

    # Check if --sandbox is supported by this Junie version
    # Release builds will NOT have --sandbox; container isolation is the sandbox
    if junie --help 2>&1 | grep -q -- --sandbox; then
        SANDBOX_FLAG="--sandbox"
        echo "Junie CLI supports --sandbox flag"
    else
        SANDBOX_FLAG=""
        echo "WARNING: Junie CLI does not support --sandbox (release build)"
        echo "Container isolation provides sandbox guarantees instead"
    fi

    if [ -n "$TASK" ]; then
        echo "Starting Junie in headless mode with task..."
        junie --auth="$JUNIE_API_KEY" $SANDBOX_FLAG "$TASK"
    else
        echo "Starting Junie in headless mode..."
        junie --auth="$JUNIE_API_KEY" $SANDBOX_FLAG
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
    echo "Junie CLI found at: $(command -v junie)"
    launch_junie
else
    echo "ERROR: Junie CLI not found in PATH"
    echo "This container requires Junie CLI to be installed."
    echo "The Dockerfile attempts to install it, but installation may have failed."
    echo "Container cannot proceed without Junie CLI — exiting with error."
    exit 1
fi
