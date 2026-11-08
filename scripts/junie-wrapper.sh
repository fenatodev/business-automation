#!/usr/bin/env bash
# junie-wrapper.sh — Invoke Junie CLI via direct Java execution.
#
# The jpackage ELF binary may be broken on some systems. This wrapper
# invokes Junie directly via the Java runtime bundled with the installation.
#
# Usage: scripts/junie-wrapper.sh --task="Your task description"
#        scripts/junie-wrapper.sh "Your task description"
#
# Environment:
#   JUNIE_DATA   — Junie data directory (default: ~/.local/share/junie)
#   JUNIE_API_KEY — API key for authentication (required for CLI mode)

set -euo pipefail

JUNIE_DATA="${JUNIE_DATA:-$HOME/.local/share/junie}"
CURRENT_LINK="$JUNIE_DATA/current"

# Resolve current version
if [[ ! -L "$CURRENT_LINK" ]]; then
  echo "Error: Junie current version symlink not found: $CURRENT_LINK" >&2
  exit 1
fi

VERSION_DIR="$(readlink "$CURRENT_LINK")"
JUNIE_APP="$VERSION_DIR/junie-app"

# Find the JAR file
JAR_FILE="$(ls "$JUNIE_APP/lib/app"/junie-release-*.jar 2>/dev/null | head -1)"
if [[ -z "$JAR_FILE" ]]; then
  echo "Error: Junie JAR not found in $JUNIE_APP/lib/app/" >&2
  exit 1
fi

JAVA_BIN="$JUNIE_APP/lib/runtime/bin/java"
if [[ ! -x "$JAVA_BIN" ]]; then
  echo "Error: Java binary not found: $JAVA_BIN" >&2
  exit 1
fi

# Extract version from JAR filename
VERSION="$(basename "$JAR_FILE" | sed 's/junie-release-//;s/\.jar//')"

export EJ_RUNNER_PWD="$(pwd)"
export JUNIE_DATA

# Build Java command
JAVA_CMD=("$JAVA_BIN" -Djpackage.app-version="$VERSION" -cp "$JAR_FILE" \
  com.intellij.ml.llm.matterhorn.ej.app.cli.standalone.MainKt)

# Pass through all arguments (including --auth, --task, etc.)
exec "${JAVA_CMD[@]}" "$@"
