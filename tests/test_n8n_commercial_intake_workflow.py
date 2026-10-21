import json
import uuid
from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / "ops"
    / "n8n"
    / "workflows"
    / "client0-commercial-intake-review.json"
)

IMPORT_COPY = (
    Path(__file__).resolve().parents[1]
    / "ops"
    / "n8n"
    / "workflows"
    / "client0-commercial-intake-review-import-copy.json"
)


def _load():
    return json.loads(WORKFLOW.read_text(encoding="utf-8"))


def _load_import_copy():
    return json.loads(IMPORT_COPY.read_text(encoding="utf-8"))


def test_workflow_is_inactive_and_import_only():
    workflow = _load()
    assert workflow["active"] is False
    assert workflow["name"].endswith("(INACTIVE)")


def test_workflow_has_required_top_level_uuid_id():
    workflow = _load()
    workflow_id = workflow["id"]
    parsed = uuid.UUID(workflow_id)
    assert str(parsed) == workflow_id
    assert parsed.version == 4


def test_workflow_uses_only_expected_nodes():
    workflow = _load()
    node_types = {node["type"] for node in workflow["nodes"]}
    # Workflow now calls FastAPI review_queue/synthetic-trigger directly
    # instead of evaluate + n8n Data Table
    assert node_types == {
        "n8n-nodes-base.webhook",
        "n8n-nodes-base.code",
        "n8n-nodes-base.removeDuplicates",
        "n8n-nodes-base.httpRequest",
    }


def test_no_literal_secrets_or_real_credentials_are_committed():
    text = WORKFLOW.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "authorization: bearer" not in lowered
    assert "api_key" not in lowered
    assert "password" not in lowered
    assert "token_sha256" not in lowered
    assert "replace_local_header_credential_id" in lowered
    assert "replace_local_bearer_credential_id" in lowered


def test_webhook_requires_header_auth():
    workflow = _load()
    webhook = next(node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.webhook")
    assert webhook["parameters"]["authentication"] == "headerAuth"
    assert webhook["parameters"]["httpMethod"] == "POST"
    assert webhook["parameters"]["responseMode"] == "onReceived"


def test_persistent_dedupe_is_by_event_id():
    workflow = _load()
    node = next(node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.removeDuplicates")
    assert node["typeVersion"] == 2
    assert node["parameters"]["operation"] == "removeItemsSeenInPreviousExecutions"
    assert node["parameters"]["logic"] == "removeItemsWithAlreadySeenKeyValues"
    assert "event_id" in node["parameters"]["dedupeValue"]
    assert node["parameters"]["options"]["scope"] == "workflow"


def test_private_api_call_is_fixed_and_authenticated():
    workflow = _load()
    # Workflow now calls review_queue/synthetic-trigger directly
    node = next(node for node in workflow["nodes"] if node["name"] == "Queue to Review (FastAPI)")
    assert node["parameters"]["method"] == "POST"
    assert node["parameters"]["url"] == (
        "http://ba-intake-private:8000/review-queue/synthetic-trigger"
    )
    assert node["parameters"]["authentication"] == "genericCredentialType"
    assert node["parameters"]["genericAuthType"] == "httpBearerAuth"
    assert node["parameters"]["options"]["redirect"]["redirect"]["followRedirects"] is False


def test_review_queue_calls_fastapi_endpoint():
    """Workflow now persists to PostgreSQL via FastAPI, not n8n Data Table."""
    workflow = _load()
    node = next(node for node in workflow["nodes"] if node["name"] == "Queue to Review (FastAPI)")
    assert node["type"] == "n8n-nodes-base.httpRequest"
    params = node["parameters"]
    assert params["method"] == "POST"
    assert "/review-queue/synthetic-trigger" in params["url"]
    # Body sends channel, message, event_id to FastAPI for triage + persistence
    assert "channel" in params["body"]
    assert "message" in params["body"]
    assert "event_id" in params["body"]
    # No n8n Data Table node should exist
    data_table_nodes = [n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.dataTable"]
    assert len(data_table_nodes) == 0, "Should not use n8n Data Table; use FastAPI review_queue"


def test_no_external_channel_or_send_node_present():
    workflow = _load()
    serialized = json.dumps(workflow).lower()
    forbidden = (
        "whatsapp",
        "telegram",
        "gmail",
        "smtp",
        "twilio",
        "slack",
        "facebook",
        "instagram",
    )
    assert not any(term in serialized for term in forbidden)


def test_rate_guard_exists():
    workflow = _load()
    rate = next(node for node in workflow["nodes"] if node["name"] == "Coarse Rate Guard")
    assert "maxPerWindow = 10" in rate["parameters"]["jsCode"]
    assert "60_000" in rate["parameters"]["jsCode"]


def test_workflow_flows_to_fastapi_review_queue():
    """Verify the complete flow: Webhook → Normalize → Dedupe → Rate Guard → FastAPI."""
    workflow = _load()
    conns = workflow["connections"]
    # Coarse Rate Guard should connect to the FastAPI node
    rate_guard_out = conns["Coarse Rate Guard"]["main"][0][0]
    assert rate_guard_out["node"] == "Queue to Review (FastAPI)"
    # No dangling connections to removed nodes
    for src, targets in conns.items():
        for group in targets.get("main", []):
            for t in group:
                assert t["node"] in [n["name"] for n in workflow["nodes"]], \
                    f"Connection to non-existent node: {t['node']}"


# --- Import copy validation (WP-058) ---


def test_import_copy_exists_and_is_inactive():
    """Import copy should exist and remain inactive."""
    assert IMPORT_COPY.exists(), "Import copy file not found"
    wf = _load_import_copy()
    assert wf["active"] is False


def test_import_copy_has_distinct_id_from_original():
    """Import copy must have a different ID from the original workflow."""
    original = _load()
    copy = _load_import_copy()
    assert copy["id"] != original["id"], "Import copy should have distinct ID"
    # Both should be valid UUIDs
    uuid.UUID(original["id"])
    uuid.UUID(copy["id"])


def test_import_copy_has_distinct_name():
    """Import copy should have a distinct name from the original."""
    original = _load()
    copy = _load_import_copy()
    assert copy["name"] != original["name"], "Import copy should have distinct name"
    assert "IMPORT COPY" in copy["name"]


def test_import_copy_preserves_node_count():
    """Import copy should preserve the same number of nodes as original."""
    original = _load()
    copy = _load_import_copy()
    assert len(copy["nodes"]) == len(original["nodes"])


def test_import_copy_preserves_node_types():
    """Import copy should preserve the same node types as original."""
    original = _load()
    copy = _load_import_copy()
    original_types = {n["type"] for n in original["nodes"]}
    copy_types = {n["type"] for n in copy["nodes"]}
    assert copy_types == original_types


def test_import_copy_preserves_node_names():
    """Import copy should preserve the same node names as original."""
    original = _load()
    copy = _load_import_copy()
    original_names = {n["name"] for n in original["nodes"]}
    copy_names = {n["name"] for n in copy["nodes"]}
    assert copy_names == original_names


def test_import_copy_has_distinct_node_ids():
    """Import copy nodes should have different IDs from original nodes."""
    original = _load()
    copy = _load_import_copy()
    original_ids = {n["id"] for n in original["nodes"]}
    copy_ids = {n["id"] for n in copy["nodes"]}
    assert original_ids.isdisjoint(copy_ids), "Import copy node IDs should be distinct"


def test_import_copy_preserves_connections():
    """Import copy should preserve the same connection structure as original."""
    original = _load()
    copy = _load_import_copy()
    assert set(copy["connections"].keys()) == set(original["connections"].keys())


def test_import_copy_no_secrets():
    """Import copy should not contain literal secrets."""
    text = IMPORT_COPY.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "authorization: bearer" not in lowered
    assert "replace_local_header_credential_id" in lowered
    assert "replace_local_bearer_credential_id" in lowered


def test_import_copy_webhook_requires_auth():
    """Import copy webhook should require header authentication."""
    copy = _load_import_copy()
    webhook = next(node for node in copy["nodes"] if node["type"] == "n8n-nodes-base.webhook")
    assert webhook["parameters"]["authentication"] == "headerAuth"
    assert webhook["parameters"]["httpMethod"] == "POST"


def test_import_copy_calls_fastapi_review_queue():
    """Import copy should call the same FastAPI endpoint as original."""
    copy = _load_import_copy()
    node = next(node for node in copy["nodes"] if node["name"] == "Queue to Review (FastAPI)")
    assert node["parameters"]["method"] == "POST"
    assert "/review-queue/synthetic-trigger" in node["parameters"]["url"]
    assert node["parameters"]["authentication"] == "genericCredentialType"


def test_import_copy_no_external_channels():
    """Import copy should not contain external channel nodes."""
    copy = _load_import_copy()
    serialized = json.dumps(copy).lower()
    forbidden = (
        "whatsapp",
        "telegram",
        "gmail",
        "smtp",
        "twilio",
        "slack",
        "facebook",
        "instagram",
    )
    assert not any(term in serialized for term in forbidden)
