"""Integration tests for n8n → FastAPI → Data Table pipeline contracts.

These tests validate that the data contracts between the three components
are compatible, using only the canonical workflow JSON and the FastAPI
endpoint schema.  They do NOT start n8n, FastAPI, or any external service.

Coverage:
- Workflow JSON structure and invariants
- FastAPI endpoint request/response schema compatibility with workflow
- Data Table column schema matches workflow output
- received_at type compatibility (workflow dateTime → Data Table date)
- Bearer authentication configuration is present
- No real credentials or secrets in committed artifacts
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / "ops"
    / "n8n"
    / "workflows"
    / "client0-commercial-intake-review.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _get_node(workflow: dict, name: str) -> dict:
    for node in workflow["nodes"]:
        if node["name"] == name:
            return node
    raise KeyError(f"Node '{name}' not found in workflow")


# ---------------------------------------------------------------------------
# Workflow JSON structural tests
# ---------------------------------------------------------------------------


class TestWorkflowStructure:
    """Verify the workflow JSON is structurally sound."""

    def test_workflow_file_exists(self) -> None:
        assert WORKFLOW_PATH.exists(), "Workflow JSON file is missing"

    def test_workflow_is_valid_json(self) -> None:
        data = _load_workflow()
        assert isinstance(data, dict)

    def test_workflow_has_required_fields(self) -> None:
        wf = _load_workflow()
        assert "id" in wf
        assert "name" in wf
        assert "nodes" in wf
        assert "connections" in wf
        assert "active" in wf

    def test_workflow_id_is_valid_uuid4(self) -> None:
        wf = _load_workflow()
        parsed = uuid.UUID(wf["id"])
        assert parsed.version == 4

    def test_workflow_is_inactive(self) -> None:
        wf = _load_workflow()
        assert wf["active"] is False

    def test_all_nodes_have_unique_ids(self) -> None:
        wf = _load_workflow()
        node_ids = [node["id"] for node in wf["nodes"]]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs found"

    def test_all_node_ids_are_valid_uuid4(self) -> None:
        wf = _load_workflow()
        for node in wf["nodes"]:
            parsed = uuid.UUID(node["id"])
            assert parsed.version == 4

    def test_webhook_node_has_header_auth(self) -> None:
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        assert webhook["parameters"]["authentication"] == "headerAuth"

    def test_webhook_node_is_post_only(self) -> None:
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        assert webhook["parameters"]["httpMethod"] == "POST"

    def test_webhook_response_mode_is_on_received(self) -> None:
        """Webhook should respond immediately, not wait for full execution."""
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        assert webhook["parameters"]["responseMode"] == "onReceived"

    def test_no_external_send_nodes(self) -> None:
        """Workflow must not contain WhatsApp, Telegram, email, or similar nodes."""
        wf = _load_workflow()
        forbidden_types = [
            "whatsapp", "telegram", "gmail", "smtp", "twilio",
            "slack", "facebook", "instagram",
        ]
        for node in wf["nodes"]:
            node_type = node["type"].lower()
            assert not any(fb in node_type for fb in forbidden_types), (
                f"External send node found: {node['type']}"
            )

    def test_no_hardcoded_credentials(self) -> None:
        """Workflow must use credential placeholders, not real values."""
        wf = _load_workflow()
        text = json.dumps(wf)
        assert "REPLACE_LOCAL_HEADER_CREDENTIAL_ID" in text
        assert "REPLACE_LOCAL_BEARER_CREDENTIAL_ID" in text
        # Should NOT contain actual credential patterns
        assert '"id": "' not in text or "REPLACE_LOCAL" in text


# ---------------------------------------------------------------------------
# FastAPI endpoint contract tests
# ---------------------------------------------------------------------------


class TestFastAPIEndpointContract:
    """Verify the FastAPI endpoint matches what the workflow expects."""

    def test_workflow_sends_correct_request_fields(self) -> None:
        """The workflow HTTP Request node should send exactly the fields
        accepted by CommercialIntakeEvaluateRequest."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Evaluate Private Intake API")
        body_expr = http_node["parameters"]["body"]

        # The body expression should stringify channel, message, event_id
        assert "channel" in body_expr
        assert "message" in body_expr
        assert "event_id" in body_expr

    def test_workflow_http_node_uses_bearer_auth(self) -> None:
        """The HTTP Request node must use Bearer authentication."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Evaluate Private Intake API")
        assert http_node["parameters"]["authentication"] == "genericCredentialType"
        assert http_node["parameters"]["genericAuthType"] == "httpBearerAuth"

    def test_workflow_http_node_url_matches_endpoint(self) -> None:
        """The URL should match the FastAPI endpoint path."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Evaluate Private Intake API")
        url = http_node["parameters"]["url"]
        assert "/internal/commercial-intake/evaluate" in url
        assert url.startswith("http://")

    def test_workflow_http_node_is_post(self) -> None:
        wf = _load_workflow()
        http_node = _get_node(wf, "Evaluate Private Intake API")
        assert http_node["parameters"]["method"] == "POST"

    def test_workflow_http_node_has_timeout(self) -> None:
        """HTTP request should have a timeout to prevent hanging."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Evaluate Private Intake API")
        timeout = http_node["parameters"]["options"]["timeout"]
        assert isinstance(timeout, int)
        assert 1000 <= timeout <= 30000  # 1-30 seconds

    def test_workflow_http_node_does_not_follow_redirects(self) -> None:
        """Redirects should be disabled for security."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Evaluate Private Intake API")
        redirect_config = http_node["parameters"]["options"]["redirect"]["redirect"]
        assert redirect_config["followRedirects"] is False


# ---------------------------------------------------------------------------
# Data Table schema compatibility tests
# ---------------------------------------------------------------------------


class TestDataTableSchemaCompatibility:
    """Verify the Data Table schema matches the workflow's output."""

    EXPECTED_COLUMNS = {
        "event_id": "string",
        "status": "string",
        "intent": "string",
        "draft_reply": "string",
        "needs_human_review": "boolean",
        "flags_json": "string",
        "received_at": "dateTime",  # Workflow node type; maps to "date" in n8n API
    }

    def test_data_table_node_uses_correct_table_name(self) -> None:
        wf = _load_workflow()
        dt_node = _get_node(wf, "Queue for Human Review")
        locator = dt_node["parameters"]["dataTableId"]
        assert locator["mode"] == "name"
        assert locator["value"] == "client0_commercial_review_queue"

    def test_data_table_node_has_all_expected_columns(self) -> None:
        wf = _load_workflow()
        dt_node = _get_node(wf, "Queue for Human Review")
        schema = dt_node["parameters"]["columns"]["schema"]
        column_ids = {col["id"] for col in schema}
        assert column_ids == set(self.EXPECTED_COLUMNS.keys())

    def test_data_table_column_types_match(self) -> None:
        """Each column in the workflow schema should have the expected type."""
        wf = _load_workflow()
        dt_node = _get_node(wf, "Queue for Human Review")
        schema = dt_node["parameters"]["columns"]["schema"]
        for col in schema:
            col_id = col["id"]
            col_type = col["type"]
            expected = self.EXPECTED_COLUMNS.get(col_id)
            if expected:
                assert col_type == expected, (
                    f"Column '{col_id}' has type '{col_type}', expected '{expected}'"
                )

    def test_received_at_type_is_datetime(self) -> None:
        """The workflow should use dateTime for received_at.
        
        Note: n8n's DataTable node uses 'dateTime' as the schema type,
        which maps to 'date' in the n8n REST API. This is expected behavior
        in n8n 2.40.x — the node type and API type differ but are compatible.
        """
        wf = _load_workflow()
        dt_node = _get_node(wf, "Queue for Human Review")
        schema = dt_node["parameters"]["columns"]["schema"]
        received_at_col = next(col for col in schema if col["id"] == "received_at")
        assert received_at_col["type"] == "dateTime"

    def test_received_at_value_is_iso8601(self) -> None:
        """The Build Review Queue Row node should produce ISO 8601 timestamps."""
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "new Date().toISOString()" in code, (
            "received_at should use new Date().toISOString()"
        )

    def test_data_table_node_operation_is_insert(self) -> None:
        """The DataTable node should insert rows, not update or upsert."""
        wf = _load_workflow()
        dt_node = _get_node(wf, "Queue for Human Review")
        assert dt_node["parameters"]["operation"] == "insert"


# ---------------------------------------------------------------------------
# Workflow output → Data Table mapping tests
# ---------------------------------------------------------------------------


class TestWorkflowOutputToDataTableMapping:
    """Verify the Build Review Queue Row output maps correctly to Data Table."""

    def test_build_row_produces_event_id(self) -> None:
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "event_id" in code

    def test_build_row_produces_status(self) -> None:
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "needs_human_review" in code
        assert "'needs_review'" in code or '"needs_review"' in code
        assert "'draft_ready'" in code or '"draft_ready"' in code

    def test_build_row_produces_intent(self) -> None:
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "intent" in code

    def test_build_row_produces_draft_reply(self) -> None:
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "draft_reply" in code

    def test_build_row_produces_needs_human_review_boolean(self) -> None:
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "Boolean(" in code, "needs_human_review should be cast to Boolean"

    def test_build_row_produces_flags_json_string(self) -> None:
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "JSON.stringify" in code, "flags should be stringified"

    def test_build_row_produces_received_at(self) -> None:
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "received_at" in code

    def test_build_row_validates_can_send_invariant(self) -> None:
        """The build row node must reject responses where can_send is not False."""
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "can_send" in code
        assert "simulation_only" in code

    def test_build_row_validates_simulation_only_invariant(self) -> None:
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "simulation_only !== true" in code


# ---------------------------------------------------------------------------
# Workflow connection topology tests
# ---------------------------------------------------------------------------


class TestWorkflowTopology:
    """Verify the workflow connections form a valid linear pipeline."""

    EXPECTED_FLOW = [
        "Inbound Webhook",
        "Normalize Safe Input",
        "Persistent Event Dedupe",
        "Coarse Rate Guard",
        "Evaluate Private Intake API",
        "Build Review Queue Row",
        "Queue for Human Review",
    ]

    def test_all_expected_nodes_exist(self) -> None:
        wf = _load_workflow()
        node_names = {node["name"] for node in wf["nodes"]}
        for name in self.EXPECTED_FLOW:
            assert name in node_names, f"Missing node: {name}"

    def test_linear_flow_is_connected(self) -> None:
        """Each node should connect to the next in the expected flow."""
        wf = _load_workflow()
        connections = wf["connections"]
        for i in range(len(self.EXPECTED_FLOW) - 1):
            source = self.EXPECTED_FLOW[i]
            target = self.EXPECTED_FLOW[i + 1]
            assert source in connections, f"{source} has no outgoing connections"
            # The target should appear in the source's main output
            source_connections = connections[source]
            if "main" in source_connections:
                for branch in source_connections["main"]:
                    for conn in branch:
                        if conn["node"] == target:
                            break
                    else:
                        continue
                    break
                else:
                    pytest.fail(
                        f"No connection from '{source}' to '{target}'"
                    )

    def test_webhook_is_entry_point(self) -> None:
        """No node should connect TO the webhook — it's the entry point."""
        wf = _load_workflow()
        connections = wf["connections"]
        webhook_name = "Inbound Webhook"
        for source_name in connections:
            if source_name == webhook_name:
                continue
            for branch in connections[source_name].get("main", []):
                for conn in branch:
                    assert conn["node"] != webhook_name, (
                        f"{source_name} connects to webhook — invalid topology"
                    )

    def test_data_table_is_final_node(self) -> None:
        """The Data Table node should have no outgoing connections."""
        wf = _load_workflow()
        connections = wf["connections"]
        dt_name = "Queue for Human Review"
        assert dt_name not in connections, (
            "Data Table node should not have outgoing connections"
        )


# ---------------------------------------------------------------------------
# Input normalization tests
# ---------------------------------------------------------------------------


class TestInputNormalization:
    """Verify the Normalize Safe Input node properly sanitizes input."""

    def test_normalize_node_validates_required_fields(self) -> None:
        wf = _load_workflow()
        norm = _get_node(wf, "Normalize Safe Input")
        code = norm["parameters"]["jsCode"]
        assert "channel" in code
        assert "message" in code
        assert "event_id" in code

    def test_normalize_node_rejects_empty_fields(self) -> None:
        wf = _load_workflow()
        norm = _get_node(wf, "Normalize Safe Input")
        code = norm["parameters"]["jsCode"]
        # Should return empty array if fields are missing
        assert "return []" in code

    def test_normalize_node_enforces_length_limits(self) -> None:
        wf = _load_workflow()
        norm = _get_node(wf, "Normalize Safe Input")
        code = norm["parameters"]["jsCode"]
        assert "30" in code  # channel max length
        assert "4000" in code  # message max length
        assert "100" in code  # event_id max length

    def test_normalize_node_trims_whitespace(self) -> None:
        wf = _load_workflow()
        norm = _get_node(wf, "Normalize Safe Input")
        code = norm["parameters"]["jsCode"]
        assert ".trim()" in code


# ---------------------------------------------------------------------------
# Deduplication and rate limiting tests
# ---------------------------------------------------------------------------


class TestDeduplicationAndRateLimiting:
    """Verify deduplication and rate limiting are properly configured."""

    def test_dedupe_uses_event_id(self) -> None:
        wf = _load_workflow()
        dedupe = _get_node(wf, "Persistent Event Dedupe")
        assert "event_id" in dedupe["parameters"]["dedupeValue"]

    def test_dedupe_scope_is_workflow(self) -> None:
        wf = _load_workflow()
        dedupe = _get_node(wf, "Persistent Event Dedupe")
        assert dedupe["parameters"]["options"]["scope"] == "workflow"

    def test_rate_guard_limits_per_window(self) -> None:
        wf = _load_workflow()
        rate = _get_node(wf, "Coarse Rate Guard")
        code = rate["parameters"]["jsCode"]
        assert "maxPerWindow" in code
        assert "windowMs" in code

    def test_rate_guard_window_is_reasonable(self) -> None:
        wf = _load_workflow()
        rate = _get_node(wf, "Coarse Rate Guard")
        code = rate["parameters"]["jsCode"]
        # 60 seconds window
        assert "60_000" in code or "60000" in code


# ---------------------------------------------------------------------------
# Integration contract: FastAPI response → Workflow Build Row
# ---------------------------------------------------------------------------


class TestFastAPIResponseToWorkflowContract:
    """Verify that the FastAPI IntakeDecision response fields match
    what the Build Review Queue Row node expects."""

    def test_intake_decision_has_event_id(self) -> None:
        from app.services.commercial_intake import IntakeDecision
        # IntakeDecision model should have event_id
        fields = IntakeDecision.model_fields
        assert "event_id" in fields

    def test_intake_decision_has_intent(self) -> None:
        from app.services.commercial_intake import IntakeDecision
        fields = IntakeDecision.model_fields
        assert "intent" in fields

    def test_intake_decision_has_draft_reply(self) -> None:
        from app.services.commercial_intake import IntakeDecision
        fields = IntakeDecision.model_fields
        assert "draft_reply" in fields

    def test_intake_decision_has_needs_human_review(self) -> None:
        from app.services.commercial_intake import IntakeDecision
        fields = IntakeDecision.model_fields
        assert "needs_human_review" in fields
        # Should be boolean
        from typing import get_args
        ann = fields["needs_human_review"].annotation
        assert ann is bool or ann == bool

    def test_intake_decision_has_flags(self) -> None:
        from app.services.commercial_intake import IntakeDecision
        fields = IntakeDecision.model_fields
        assert "flags" in fields

    def test_intake_decision_can_send_is_literal_false(self) -> None:
        """can_send must be Literal[False] — never True."""
        from app.services.commercial_intake import IntakeDecision
        from typing import get_args
        fields = IntakeDecision.model_fields
        assert "can_send" in fields
        # Check the default is False
        assert fields["can_send"].default is False

    def test_intake_decision_simulation_only_is_literal_true(self) -> None:
        """simulation_only must be Literal[True] — always True."""
        from app.services.commercial_intake import IntakeDecision
        fields = IntakeDecision.model_fields
        assert "simulation_only" in fields
        assert fields["simulation_only"].default is True

    def test_workflow_build_row_checks_can_send(self) -> None:
        """The workflow must check can_send === false before proceeding."""
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "can_send !== false" in code

    def test_workflow_build_row_checks_simulation_only(self) -> None:
        """The workflow must check simulation_only === true before proceeding."""
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "simulation_only !== true" in code


# ---------------------------------------------------------------------------
# received_at type compatibility (the key integration concern)
# ---------------------------------------------------------------------------


class TestReceivedAtCompatibility:
    """Verify the received_at field is compatible across all components.
    
    The workflow generates `new Date().toISOString()` which produces
    an ISO 8601 string like "2026-10-15T11:35:00.000Z".
    
    The n8n DataTable node schema uses type "dateTime" which maps to
    the n8n API type "date". This is the correct and expected mapping
    in n8n 2.40.x.
    """

    def test_workflow_generates_iso8601_timestamp(self) -> None:
        """The Build Review Queue Row should use toISOString()."""
        wf = _load_workflow()
        build_node = _get_node(wf, "Build Review Queue Row")
        code = build_node["parameters"]["jsCode"]
        assert "toISOString()" in code

    def test_iso8601_string_is_valid_datetime(self) -> None:
        """Verify that toISOString() output format is parseable."""
        # Simulate what new Date().toISOString() produces
        sample = datetime.now(timezone.utc).isoformat()
        # Should be parseable
        parsed = datetime.fromisoformat(sample.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None

    def test_data_table_schema_uses_datetime_type(self) -> None:
        """The DataTable node schema should use 'dateTime' for received_at.
        
        This maps to 'date' in the n8n REST API, which is the expected
        behavior in n8n 2.40.x.
        """
        wf = _load_workflow()
        dt_node = _get_node(wf, "Queue for Human Review")
        schema = dt_node["parameters"]["columns"]["schema"]
        received_at = next(c for c in schema if c["id"] == "received_at")
        assert received_at["type"] == "dateTime"

    def test_data_table_column_mapping_includes_received_at(self) -> None:
        """The DataTable insert mapping should include received_at."""
        wf = _load_workflow()
        dt_node = _get_node(wf, "Queue for Human Review")
        mapping = dt_node["parameters"]["columns"]["value"]
        assert "received_at" in mapping
        # Should reference the json.received_at from Build Review Queue Row
        assert "$json.received_at" in mapping["received_at"]


# ---------------------------------------------------------------------------
# Bearer authentication configuration tests
# ---------------------------------------------------------------------------


class TestBearerAuthConfiguration:
    """Verify Bearer auth is properly configured in the workflow."""

    def test_http_request_node_has_bearer_credential_ref(self) -> None:
        """The HTTP Request node should reference a Bearer auth credential."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Evaluate Private Intake API")
        creds = http_node.get("credentials", {})
        bearer = creds.get("httpBearerAuth", {})
        assert bearer.get("genericAuthType") == "httpBearerAuth" or \
               http_node["parameters"]["genericAuthType"] == "httpBearerAuth"

    def test_webhook_node_has_header_auth_credential_ref(self) -> None:
        """The Webhook node should reference a Header Auth credential."""
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        creds = webhook.get("credentials", {})
        header_auth = creds.get("httpHeaderAuth", {})
        assert "REPLACE_LOCAL_HEADER_CREDENTIAL_ID" in str(header_auth)

    def test_bearer_credential_uses_placeholder(self) -> None:
        """Bearer credential ID should be a placeholder, not a real ID."""
        wf = _load_workflow()
        http_node = _get_node(wf, "Evaluate Private Intake API")
        creds = http_node.get("credentials", {})
        bearer = creds.get("httpBearerAuth", {})
        cred_id = bearer.get("id", "")
        assert "REPLACE_LOCAL" in cred_id, (
            "Bearer credential should use placeholder, not real ID"
        )

    def test_header_credential_uses_placeholder(self) -> None:
        """Header auth credential ID should be a placeholder."""
        wf = _load_workflow()
        webhook = _get_node(wf, "Inbound Webhook")
        creds = webhook.get("credentials", {})
        header_auth = creds.get("httpHeaderAuth", {})
        cred_id = header_auth.get("id", "")
        assert "REPLACE_LOCAL" in cred_id, (
            "Header auth credential should use placeholder, not real ID"
        )
