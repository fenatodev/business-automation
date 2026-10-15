"""Health check script for the n8n executor sandbox container.

This script verifies that the executor process is alive and can reach
the n8n API endpoint. It is called by the Docker healthcheck.

Returns 0 (success) if the executor is healthy, 1 (failure) otherwise.
"""

import httpx
import os
import sys


def main() -> int:
    """Check if the executor can reach the n8n API.

    Returns:
        0 if healthy, 1 if unhealthy.
    """
    base_url = os.environ.get("N8N_BASE_URL", "http://n8n:5678")
    api_key = os.environ.get("N8N_API_KEY", "")

    try:
        client = httpx.Client(
            base_url=base_url,
            timeout=5.0,
            follow_redirects=False,
        )
        headers = {}
        if api_key:
            headers["X-N8N-API-KEY"] = api_key

        # Check if n8n API is reachable
        response = client.get("/api/v1/workflows", headers=headers, timeout=5.0)

        # 200 means n8n is reachable
        # 401/403 means n8n is reachable but auth may be misconfigured
        # Both are "healthy" from a connectivity standpoint
        if response.status_code in (200, 401, 403):
            return 0
        else:
            return 1

    except Exception:
        # Cannot reach n8n — unhealthy
        return 1


if __name__ == "__main__":
    sys.exit(main())
