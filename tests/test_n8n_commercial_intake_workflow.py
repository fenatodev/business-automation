import json
from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / "ops"
    / "n8n"
    / "workflows"
    / "client0-commercial-intake-review.json"
)


def _load():
    return json.loads(WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_is_inactive_and_import_only():
    workflow = _load()
    assert workflow["active"] is False
    assert workflow["name"].endswith("(INACTIVE)")


def test_workflow_uses_only_expected_nodes():
    workflow = _load()
    node_types = {node["type"] for node in workflow["nodes"]}
    assert node_types == {
        "n8n-nodes-base.webhook",
        "n8n-nodes-base.code",
        "n8n-nodes-base.removeDuplicates",
        "n8n-nodes-base.httpRequest",
        "n8n-nodes-base.dataTable",
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
    node = next(node for node in workflow["nodes"] if node["name"] == "Evaluate Private Intake API")
    assert node["parameters"]["method"] == "POST"
    assert node["parameters"]["url"] == (
        "http://host.docker.internal:8000/internal/commercial-intake/evaluate"
    )
    assert node["parameters"]["authentication"] == "genericCredentialType"
    assert node["parameters"]["genericAuthType"] == "httpBearerAuth"
    assert node["parameters"]["options"]["redirect"]["redirect"]["followRedirects"] is False


def test_review_queue_uses_named_local_data_table():
    workflow = _load()
    node = next(node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.dataTable")
    assert node["parameters"]["resource"] == "row"
    assert node["parameters"]["operation"] == "insert"
    locator = node["parameters"]["dataTableId"]
    assert locator["mode"] == "name"
    assert locator["value"] == "client0_commercial_review_queue"
    schema = {column["id"] for column in node["parameters"]["columns"]["schema"]}
    assert schema == {
        "event_id",
        "status",
        "intent",
        "draft_reply",
        "needs_human_review",
        "flags_json",
        "received_at",
    }


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


def test_rate_guard_and_output_safety_checks_exist():
    workflow = _load()
    rate = next(node for node in workflow["nodes"] if node["name"] == "Coarse Rate Guard")
    assert "maxPerWindow = 10" in rate["parameters"]["jsCode"]
    assert "60_000" in rate["parameters"]["jsCode"]

    safety = next(node for node in workflow["nodes"] if node["name"] == "Build Review Queue Row")
    code = safety["parameters"]["jsCode"]
    assert "d.can_send !== false" in code
    assert "d.simulation_only !== true" in code
