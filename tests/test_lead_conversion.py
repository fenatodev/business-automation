"""WP-514 — Lead to Customer conversion."""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Lead"):
    res = client.post(
        "/leads", headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": "5511999999999",
            "source": "website",
        },
    )
    assert res.status_code == 200
    return res.json()


def _create_conversation(client, headers, company_id, lead_id=None, customer_id=None):
    payload = {"company_id": company_id, "channel": "whatsapp", "subject": "Test"}
    if lead_id is not None:
        payload["lead_id"] = lead_id
    if customer_id is not None:
        payload["customer_id"] = customer_id
    res = client.post("/conversations", headers=headers, json=payload)
    assert res.status_code == 200
    return res.json()


# --- Conversion tests ---


def test_convert_lead_to_customer(client, admin_headers, operator_a_headers):
    """Converting a lead creates a customer and marks the lead as converted."""
    company = _create_company(client, admin_headers, name="ConvCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="ConvLead")

    res = client.post(
        f"/leads/{lead['id']}/convert",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    customer = res.json()
    assert customer["name"] == "ConvLead"
    assert customer["phone"] == "5511999999999"
    assert customer["lead_id"] == lead["id"]

    # Lead should be marked as converted
    res = client.get(f"/leads/{lead['id']}", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "converted"


def test_convert_lead_idempotent(client, admin_headers, operator_a_headers):
    """Converting an already converted lead returns the existing customer."""
    company = _create_company(client, admin_headers, name="IdemCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="IdemLead")

    res1 = client.post(f"/leads/{lead['id']}/convert", headers=operator_a_headers)
    assert res1.status_code == 200
    customer1 = res1.json()

    res2 = client.post(f"/leads/{lead['id']}/convert", headers=operator_a_headers)
    assert res2.status_code == 200
    customer2 = res2.json()

    assert customer1["id"] == customer2["id"]


def test_convert_lead_links_conversations(client, admin_headers, operator_a_headers):
    """Converting a lead links existing conversations to the new customer."""
    company = _create_company(client, admin_headers, name="ConvConvCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="ConvConvLead")

    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])
    conv_id = conv["id"]

    client.post(f"/leads/{lead['id']}/convert", headers=operator_a_headers)

    # Conversation should now have customer_id set
    res = client.get(f"/conversations/{conv_id}", headers=operator_a_headers)
    assert res.status_code == 200
    conv_data = res.json()
    assert conv_data["customer_id"] is not None


def test_convert_lead_requires_auth(client):
    """Converting a lead requires authentication."""
    res = client.post("/leads/999/convert")
    assert res.status_code in (401, 403)


def test_convert_lead_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot convert Operator B's lead."""
    _create_company(client, admin_headers, name="IsoA")
    company_b = _create_company(client, admin_headers, name="IsoB")

    lead_b = _create_lead(client, operator_b_headers, company_b["id"], name="IsoBLead")

    res = client.post(
        f"/leads/{lead_b['id']}/convert",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_convert_nonexistent_lead(client, operator_a_headers):
    """Converting a non-existent lead returns 404."""
    res = client.post(
        "/leads/99999/convert",
        headers=operator_a_headers,
    )
    assert res.status_code == 404
