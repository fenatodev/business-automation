"""WP-280: opportunity conversation panel uses explicit contact ownership."""

from datetime import datetime, timezone
from pathlib import Path


def test_unlinked_opportunity_has_no_linked_conversations(client, admin_headers, operator_a_headers):
    company = client.post("/companies", headers=admin_headers,
                          json={"name": "Linked conversations", "slug": "linked-conversations"}).json()
    opportunity = client.post("/opportunities", headers=operator_a_headers, json={
        "source": "manual", "external_url": "https://example.test/wp280",
        "title": "Synthetic", "description": "Synthetic",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    })
    assert opportunity.status_code == 200
    response = client.get(f"/opportunities/{opportunity.json()['id']}/linked-conversations",
                          headers=operator_a_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_linked_conversations_excludes_other_contact(client, admin_headers, operator_a_headers):
    company = client.post("/companies", headers=admin_headers,
                          json={"name": "Linked conversations", "slug": "linked-conversations-a"}).json()
    lead = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company["id"], "name": "Linked", "phone": "5511999999999", "source": "manual",
    }).json()
    other = client.post("/leads", headers=operator_a_headers, json={
        "company_id": company["id"], "name": "Other", "phone": "5511888888888", "source": "manual",
    }).json()
    opportunity = client.post("/opportunities", headers=operator_a_headers, json={
        "source": "manual", "external_url": "https://example.test/wp280-a",
        "title": "Synthetic", "description": "Synthetic",
        "captured_at": datetime.now(timezone.utc).isoformat(), "lead_id": lead["id"],
    }).json()
    linked = client.post("/conversations", headers=operator_a_headers,
                         json={"company_id": company["id"], "channel": "web", "lead_id": lead["id"]}).json()
    client.post("/conversations", headers=operator_a_headers,
                json={"company_id": company["id"], "channel": "web", "lead_id": other["id"]})
    response = client.get(f"/opportunities/{opportunity['id']}/linked-conversations",
                          headers=operator_a_headers)
    assert [item["id"] for item in response.json()] == [linked["id"]]


def test_ui_uses_linked_conversation_route():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert '/opportunities/" + id + "/linked-conversations' in js
    assert 'item.addEventListener("keydown", (event) => {' in js
    assert 'item.setAttribute("aria-label", "Abrir conversa #"' in js
    assert "expectedVersion !== selectionVersion" in js


def test_customer_linked_conversations_are_returned(client, admin_headers, operator_a_headers):
    company = client.post("/companies", headers=admin_headers,
                          json={"name": "Customer conversations", "slug": "customer-conversations"}).json()
    customer = client.post("/customers", headers=operator_a_headers, json={
        "company_id": company["id"], "name": "Customer", "phone": "5511777777777",
    }).json()
    opportunity = client.post("/opportunities", headers=operator_a_headers, json={
        "source": "manual", "external_url": "https://example.test/wp280-customer",
        "title": "Synthetic", "description": "Synthetic",
        "captured_at": datetime.now(timezone.utc).isoformat(), "customer_id": customer["id"],
    }).json()
    conversation = client.post("/conversations", headers=operator_a_headers, json={
        "company_id": company["id"], "channel": "web", "customer_id": customer["id"],
    }).json()
    response = client.get(f"/opportunities/{opportunity['id']}/linked-conversations",
                          headers=operator_a_headers)
    assert [item["id"] for item in response.json()] == [conversation["id"]]


def test_linked_conversations_hides_other_tenant_opportunity(
    client, admin_headers, operator_a_headers, operator_b_headers,
):
    client.post("/companies", headers=admin_headers,
                json={"name": "Tenant A", "slug": "linked-tenant-a"})
    company_b = client.post("/companies", headers=admin_headers,
                            json={"name": "Tenant B", "slug": "linked-tenant-b"}).json()
    lead_b = client.post("/leads", headers=operator_b_headers, json={
        "company_id": company_b["id"], "name": "Private", "phone": "5511666666666", "source": "manual",
    }).json()
    opportunity = client.post("/opportunities", headers=operator_b_headers, json={
        "source": "manual", "external_url": "https://example.test/wp280-private",
        "title": "Private", "description": "Private",
        "captured_at": datetime.now(timezone.utc).isoformat(), "lead_id": lead_b["id"],
    }).json()
    response = client.get(f"/opportunities/{opportunity['id']}/linked-conversations",
                          headers=operator_a_headers)
    assert response.status_code == 404
