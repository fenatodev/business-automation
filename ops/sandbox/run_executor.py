"""Executor entry point for the n8n sandbox container.

This script runs as the main process (CMD) in the sandbox container.
It polls for approved operations and executes them via N8nExecutor
with HMAC-verified approvals.

The executor reads operations from a JSON queue file in the writable
journal directory. Each operation must include a valid SignedApproval
that was created by the human operator (outside the agent's reach).

Usage:
    python /app/run_executor.py

Environment variables:
    N8N_BASE_URL: n8n API URL (e.g., http://n8n:5678)
    N8N_API_KEY: n8n API key
    APPROVAL_SECRET: HMAC secret for approval verification
    QUEUE_DIR: Directory for operation queue files (default: /var/log/n8n-executor/queue)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)


def main() -> None:
    """Run the executor polling loop."""
    base_url = os.environ.get("N8N_BASE_URL", "http://n8n:5678")
    api_key = os.environ.get("N8N_API_KEY", "")
    approval_secret = os.environ.get("APPROVAL_SECRET", "")
    queue_dir = os.environ.get("QUEUE_DIR", "/var/log/n8n-executor/queue")

    if not approval_secret:
        logger.error("APPROVAL_SECRET not set — cannot start executor")
        sys.exit(1)

    # Import here so the script fails fast if dependencies are missing
    from app.services.approval_gate import ApprovalVerifier, IntegrityJournal
    from app.services.n8n_executor import ExecutorConfig, N8nExecutor

    # Set up journal persistence
    journal_path = Path("/var/log/n8n-executor/journal.json")
    integrity_journal = IntegrityJournal(path=journal_path)

    # Create verifier — only verifies, cannot sign
    verifier = ApprovalVerifier(secret=approval_secret, journal=integrity_journal)

    # Create executor with verifier integration
    config = ExecutorConfig(
        base_url=base_url,
        api_key=api_key if api_key else None,
        timeout=10.0,
        journal_path=Path("/var/log/n8n-executor/executor_journal.json"),
    )

    # Ensure queue directory exists
    Path(queue_dir).mkdir(parents=True, exist_ok=True)

    logger.info(
        "Executor started — polling %s for approved operations",
        queue_dir,
    )

    with N8nExecutor(config) as executor:
        # Inject the verifier into the executor
        executor.set_approval_verifier(verifier)

        while True:
            try:
                # Poll for operation queue files
                queue_files = sorted(Path(queue_dir).glob("*.json"))

                for queue_file in queue_files:
                    try:
                        operation_data = json.loads(queue_file.read_text(encoding="utf-8"))
                        logger.info(
                            "Processing operation: %s",
                            operation_data.get("operation", "unknown"),
                        )

                        # Execute with approval verification
                        result = executor.execute_with_queue(operation_data)

                        logger.info(
                            "Operation completed: %s — status: %s",
                            operation_data.get("operation"),
                            result.get("status") if isinstance(result, dict) else "ok",
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to process %s: %s",
                            queue_file.name,
                            e,
                        )
                    finally:
                        # Move processed file to done directory
                        done_dir = Path(queue_dir) / "done"
                        done_dir.mkdir(parents=True, exist_ok=True)
                        queue_file.rename(done_dir / queue_file.name)

            except Exception as e:
                logger.error("Polling error: %s", e)

            # Poll interval
            time.sleep(5)


if __name__ == "__main__":
    main()
