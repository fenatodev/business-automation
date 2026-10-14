"""Static safety contract for the inactive n8n F2 synthetic workflow."""

import json
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "n8n"
    / "f2-commercial-sandbox.json"
)


def _load() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_workflow_importable_and_inactive() -> None:
    workflow = _load()
    assert workflow["id"] == "f2-commercial-demo"
    assert isinstance(workflow["versionId"], str)
    assert workflow["active"] is False
    assert workflow.get("credentials") is None
    assert workflow["settings"]["timezone"] == "America/Sao_Paulo"


def test_only_manual_schedule_and_code_nodes() -> None:
    workflow = _load()
    nodes = workflow["nodes"]
    assert len(nodes) == 5
    assert {node["type"] for node in nodes} == {
        "n8n-nodes-base.manualTrigger",
        "n8n-nodes-base.scheduleTrigger",
        "n8n-nodes-base.code",
    }
    assert {node["name"] for node in nodes} == {
        "Manual Sandbox Trigger",
        "Daily Simulation Trigger",
        "Fictitious Cases Only",
        "Deterministic Commercial Policy",
        "Safety Assertion and Audit",
    }
    assert all(not node.get("credentials") for node in nodes)


def test_synthetic_only_and_fail_closed() -> None:
    workflow = _load()
    code = {
        node["name"]: node["parameters"]["jsCode"]
        for node in workflow["nodes"]
        if node["type"] == "n8n-nodes-base.code"
    }
    assert "client0-demo" in code["Fictitious Cases Only"]
    assert "other-tenant" in code["Fictitious Cases Only"]
    policy = code["Deterministic Commercial Policy"]
    assert "opt_out===true" in policy
    assert "opt_in!==true" in policy
    assert "template_approved!==true" in policy
    assert "tenant_scope" in policy
    assert "duplicate_event" in policy
    assert "dispatch:'disabled'" in policy
    assert "simulation_only:true" in policy
    audit = code["Safety Assertion and Audit"]
    assert "outbound_messages_sent:0" in audit
    assert "rows.length!==9" in audit
    assert "dispatch!=='disabled'" in audit


def test_all_graph_connections_remain_internal() -> None:
    workflow = _load()
    names = {node["name"] for node in workflow["nodes"]}
    graph = workflow["connections"]
    assert set(graph).issubset(names)
    for links in graph.values():
        for outputs in links.values():
            for items in outputs:
                assert {item["node"] for item in items}.issubset(names)
