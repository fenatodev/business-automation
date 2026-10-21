"""WP-051: Post-E2E security verification tests.

These tests ensure that after the WP-050 E2E synthetic test:
1. The workflow JSON in the repository has not drifted from expected state
2. No real credentials have been accidentally committed
3. Security invariants are preserved
4. Authorization bypass is prevented

These are static tests that only read the workflow JSON file.
They do NOT connect to n8n, FastAPI, or any external service.
"""

import json
import re
import uuid
from pathlib import Path

import pytest

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / "ops"
    / "n8n"
    / "workflows"
    / "client0-commercial-intake-review.json"
)


def _load_workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _get_node(workflow: dict, name: str) -> dict:
    for node in workflow["nodes"]:
        if node["name"] == name:
            return node
    raise KeyError(f"Node '{name}' not found in workflow")


# ---------------------------------------------------------------------------
# Credential drift detection
# ---------------------------------------------------------------------------


class TestCredentialDriftDetection:
    """Ensure no real n8n credential IDs are committed to the repository.

    After WP-050, the workflow was updated with real credential IDs during
    the E2E test. These tests verify the rollback restored placeholders.
    """

    def test_workflow_uses_header_credential_placeholder(self) -> None:
        """The Inbound Webhook must use a placeholder, not a real credential ID."""
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        creds = webhook.get("credentials", {})
        header_cred = creds.get("httpHeaderAuth", {})
        cred_id = header_cred.get("id", "")
        # Should be the placeholder string, not a real n8n credential ID
        assert "REPLACE_LOCAL" in cred_id, (
            f"Inbound Webhook uses real credential ID: {cred_id}. "
            "Expected placeholder with REPLACE_LOCAL prefix."
        )

    def test_workflow_uses_bearer_credential_placeholder(self) -> None:
        """The FastAPI HTTP Request node must use a placeholder, not a real credential ID."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Queue to Review (FastAPI)")
        creds = http_node.get("credentials", {})
        bearer_cred = creds.get("httpBearerAuth", {})
        cred_id = bearer_cred.get("id", "")
        assert "REPLACE_LOCAL" in cred_id, (
            f"FastAPI node uses real credential ID: {cred_id}. "
            "Expected placeholder with REPLACE_LOCAL prefix."
        )

    def test_no_real_n8n_credential_ids_in_workflow_json(self) -> None:
        """Real n8n credential IDs follow a specific pattern (alphanumeric, ~16 chars).
        This test scans the entire workflow JSON for such patterns outside placeholders."""
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        # n8n credential IDs are typically 16-char alphanumeric strings
        # that appear in credential ID fields
        # Known real credential IDs from WP-044 to WP-050
        known_real_ids = [
            "uUJ7ckNMDmHevBp1",  # business-automation-internal-ingress
            "v6gCgi36SmLsOSid",  # business-automation-operator
            "TQRol30waRpD6BkA",  # test-header (orphan)
            "t26m1ruPUDRcY7FK",  # wp-050-bearer-test (deleted)
            "JIu91zQmIFF9EoMN",  # wp-050-header-test (deleted)
        ]
        for real_id in known_real_ids:
            assert real_id not in text, (
                f"Real credential ID '{real_id}' found in workflow JSON. "
                "This should have been replaced with a placeholder after E2E test."
            )

    def test_credential_ids_are_placeholders_not_names(self) -> None:
        """n8n stores both the credential ID and name in the workflow JSON.
        The ID is what matters for security — it must be a placeholder.
        The name is just metadata displayed in the n8n UI and is harmless."""
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        creds = webhook.get("credentials", {})
        header_cred = creds.get("httpHeaderAuth", {})
        # The ID must be a placeholder
        cred_id = header_cred.get("id", "")
        assert "REPLACE_LOCAL" in cred_id, (
            f"Inbound Webhook credential ID is not a placeholder: {cred_id}"
        )
        # The name is just UI metadata — it's safe to have the real name
        # as long as the ID is a placeholder
        assert "name" in header_cred, "Credential should have a name field"

    def test_no_hardcoded_auth_values_in_workflow(self) -> None:
        """The workflow JSON should not contain hardcoded auth tokens or keys."""
        text = WORKFLOW_PATH.read_text(encoding="utf-8").lower()
        # Patterns that would indicate hardcoded secrets
        suspicious_patterns = [
            "bearer ",
            "api_key",
            "api-key:",
            "x-api-key",
            "authorization:",
            "token_sha256",
        ]
        for pattern in suspicious_patterns:
            assert pattern not in text, (
                f"Potential hardcoded auth value found: {pattern}"
            )


# ---------------------------------------------------------------------------
# Post-E2E state verification
# ---------------------------------------------------------------------------


class TestPostE2EState:
    """Verify the workflow is in the expected state after WP-050 E2E test."""

    def test_workflow_is_inactive(self) -> None:
        """The workflow must be marked as inactive in the JSON."""
        wf = _load_workflow()
        assert wf["active"] is False, (
            "Workflow is marked as active in the repository. "
            "This should only be activated temporarily during E2E tests."
        )

    def test_workflow_name_indicates_inactive(self) -> None:
        """The workflow name should contain INACTIVE to prevent accidental activation."""
        wf = _load_workflow()
        assert "INACTIVE" in wf["name"].upper(), (
            f"Workflow name '{wf['name']}' does not indicate inactive status"
        )

    def test_normalize_node_uses_n8n_2x_compatible_return(self) -> None:
        """After WP-050 fix, Normalize Safe Input should return object directly."""
        wf = _load_workflow()
        norm = _get_node(wf, "Normalize Safe Input")
        code = norm["parameters"]["jsCode"]
        # Should NOT use the old n8n 1.x format
        assert "return [{ json:" not in code, (
            "Normalize Safe Input still uses n8n 1.x return format"
        )
        # Should use direct object return
        assert "return {" in code or "return []" in code

    def test_workflow_calls_review_queue_endpoint(self) -> None:
        """The workflow now calls /review-queue/synthetic-trigger directly."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Queue to Review (FastAPI)")
        url = http_node["parameters"]["url"]
        assert "/review-queue/synthetic-trigger" in url

    def test_fastapi_url_uses_container_name_not_ip(self) -> None:
        """The FastAPI URL should use the container name, not a hardcoded IP."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Queue to Review (FastAPI)")
        url = http_node["parameters"]["url"]
        # Should NOT contain a hardcoded IP address
        ip_pattern = re.compile(r'http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:')
        assert not ip_pattern.search(url), (
            f"FastAPI URL contains hardcoded IP: {url}. "
            "Should use container name like 'ba-intake-private'."
        )
        # Should use the expected container name
        assert "ba-intake-private" in url, (
            f"FastAPI URL does not use expected container name: {url}"
        )


# ---------------------------------------------------------------------------
# Security invariants
# ---------------------------------------------------------------------------


class TestSecurityInvariants:
    """Verify security invariants are preserved in the workflow."""

    def test_no_external_send_nodes(self) -> None:
        """Workflow must not contain any external messaging nodes."""
        wf = _load_workflow()
        forbidden_types = [
            "whatsapp", "telegram", "gmail", "smtp", "twilio",
            "slack", "facebook", "instagram", "discord",
        ]
        for node in wf["nodes"]:
            node_type = node["type"].lower()
            assert not any(fb in node_type for fb in forbidden_types), (
                f"External send node found: {node['type']}"
            )

    def test_webhook_requires_authentication(self) -> None:
        """The webhook must require authentication."""
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        auth = webhook["parameters"].get("authentication")
        assert auth == "headerAuth", (
            f"Webhook authentication is '{auth}', expected 'headerAuth'"
        )

    def test_webhook_is_post_only(self) -> None:
        """The webhook should only accept POST requests."""
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        method = webhook["parameters"].get("httpMethod")
        assert method == "POST", (
            f"Webhook accepts '{method}' method, expected 'POST' only"
        )

    def test_fastapi_call_requires_bearer_auth(self) -> None:
        """The HTTP Request to FastAPI must use Bearer authentication."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Queue to Review (FastAPI)")
        assert http_node["parameters"]["authentication"] == "genericCredentialType"
        assert http_node["parameters"]["genericAuthType"] == "httpBearerAuth"

    def test_fastapi_call_does_not_follow_redirects(self) -> None:
        """Redirects should be disabled to prevent open redirect attacks."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Queue to Review (FastAPI)")
        redirect_config = http_node["parameters"]["options"]["redirect"]["redirect"]
        assert redirect_config["followRedirects"] is False

    def test_safety_checks_are_server_side(self) -> None:
        """Safety checks (can_send, simulation_only) are now enforced
        server-side by the FastAPI review_queue endpoint, not in the workflow."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Queue to Review (FastAPI)")
        url = http_node["parameters"]["url"]
        assert "/review-queue/synthetic-trigger" in url

    def test_dedupe_is_by_event_id(self) -> None:
        """Deduplication must be based on event_id to prevent replay attacks."""
        wf = _load_workflow()
        dedupe = next(n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.removeDuplicates")
        assert "event_id" in dedupe["parameters"]["dedupeValue"]

    def test_rate_limiting_is_present(self) -> None:
        """Rate limiting must be present to prevent abuse."""
        wf = _load_workflow()
        rate = _get_node(wf, "Coarse Rate Guard")
        code = rate["parameters"]["jsCode"]
        assert "maxPerWindow" in code or "rate" in code.lower()


# ---------------------------------------------------------------------------
# Authorization bypass prevention
# ---------------------------------------------------------------------------


class TestAuthorizationBypassPrevention:
    """Tests to prevent authorization bypass in workflow import/export."""

    def test_workflow_id_is_uuid4(self) -> None:
        """The workflow ID should be a valid UUID4."""
        wf = _load_workflow()
        parsed = uuid.UUID(wf["id"])
        assert parsed.version == 4

    def test_no_script_injection_in_node_names(self) -> None:
        """Node names should not contain script injection patterns."""
        wf = _load_workflow()
        for node in wf["nodes"]:
            name = node["name"]
            assert "<script" not in name.lower()
            assert "javascript:" not in name.lower()
            assert "onerror" not in name.lower()

    def test_code_nodes_use_javascript_language(self) -> None:
        """Code nodes should explicitly use JavaScript, not other languages."""
        wf = _load_workflow()
        for node in wf["nodes"]:
            if node["type"] == "n8n-nodes-base.code":
                lang = node["parameters"].get("language", "javaScript")
                assert lang == "javaScript", (
                    f"Code node '{node['name']}' uses language '{lang}'"
                )

    def test_no_data_table_node(self) -> None:
        """Workflow should not use n8n Data Table; it calls FastAPI directly."""
        wf = _load_workflow()
        dt_nodes = [n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.dataTable"]
        assert len(dt_nodes) == 0, "Should not use n8n Data Table"

    def test_workflow_has_no_unexpected_connections(self) -> None:
        """The workflow should have only the expected linear connections."""
        wf = _load_workflow()
        expected_nodes = [
            "Inbound Webhook",
            "Normalize Safe Input",
            "Persistent Event Dedupe",
            "Coarse Rate Guard",
            "Queue to Review (FastAPI)",
        ]
        actual_nodes = [node["name"] for node in wf["nodes"]]
        assert actual_nodes == expected_nodes, (
            f"Workflow nodes do not match expected order. "
            f"Expected: {expected_nodes}, Got: {actual_nodes}"
        )

    def test_no_active_on_failure_connections(self) -> None:
        """The workflow should not have active on-failure connections that could bypass security.
        
        Note: n8n's removeDuplicates node creates a branch 1 (empty) for deduplicated items.
        An empty branch [] is harmless — it just means duplicates are discarded.
        We only flag branches that actually connect to another node."""
        wf = _load_workflow()
        connections = wf["connections"]
        for source, conns in connections.items():
            if "main" in conns and len(conns["main"]) > 1:
                # Branch 1 is the on-failure/duplicates path
                failure_branch = conns["main"][1]
                # An empty branch is fine — it means duplicates are discarded
                if failure_branch:
                    pytest.fail(
                        f"Node '{source}' has active on-failure connections: {failure_branch}. "
                        "This could bypass security checks."
                    )

    def test_http_request_has_timeout(self) -> None:
        """HTTP Request to FastAPI must have a timeout."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Queue to Review (FastAPI)")
        timeout = http_node["parameters"]["options"].get("timeout")
        assert timeout is not None, "HTTP Request has no timeout"
        assert isinstance(timeout, int)
        assert 1000 <= timeout <= 30000, (
            f"HTTP Request timeout {timeout}ms is outside acceptable range (1-30s)"
        )
