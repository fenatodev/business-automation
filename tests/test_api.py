def create_company(client, name="Acme", slug="acme"):
    response = client.post(
        "/companies",
        json={"name": name, "slug": slug},
    )
    assert response.status_code == 200
    return response.json()


def create_lead(client, company_id, name="Maria"):
    response = client.post(
        "/leads",
        json={
            "company_id": company_id,
            "name": name,
            "phone": "11999999999",
            "source": "site",
            "interest": "automacao",
        },
    )
    assert response.status_code == 200
    return response.json()


def create_customer(client, company_id, name="Joao"):
    response = client.post(
        "/customers",
        json={
            "company_id": company_id,
            "name": name,
            "phone": "11888888888",
            "email": "joao@example.com",
        },
    )
    assert response.status_code == 200
    return response.json()


def create_conversation(client, company_id, lead_id=None, customer_id=None):
    response = client.post(
        "/conversations",
        json={
            "company_id": company_id,
            "channel": "whatsapp",
            "lead_id": lead_id,
            "customer_id": customer_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_get_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Fenato Business Automation API",
        "status": "running",
    }


def test_create_company_success(client):
    response = client.post(
        "/companies",
        json={"name": "Acme", "slug": "acme"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Acme"
    assert data["slug"] == "acme"


def test_create_company_duplicate_slug_returns_409(client):
    create_company(client)

    response = client.post(
        "/companies",
        json={"name": "Acme 2", "slug": "acme"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Company slug already exists"


def test_create_lead_with_existing_company(client):
    company = create_company(client)

    response = client.post(
        "/leads",
        json={
            "company_id": company["id"],
            "name": "Maria",
            "phone": "11999999999",
            "source": "site",
            "interest": "automacao",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == company["id"]
    assert data["name"] == "Maria"
    assert data["status"] == "new"


def test_create_lead_with_missing_company_returns_404(client):
    response = client.post(
        "/leads",
        json={
            "company_id": 999,
            "name": "Maria",
            "phone": "11999999999",
            "source": "site",
            "interest": "automacao",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_create_conversation_rules(client):
    company = create_company(client, name="Company 1", slug="company-1")
    other_company = create_company(client, name="Company 2", slug="company-2")
    lead = create_lead(client, company["id"])
    other_lead = create_lead(client, other_company["id"], name="Ana")
    customer = create_customer(client, company["id"])

    missing_owner_response = client.post(
        "/conversations",
        json={
            "company_id": company["id"],
            "channel": "whatsapp",
            "lead_id": None,
            "customer_id": None,
        },
    )
    assert missing_owner_response.status_code == 400
    assert (
        missing_owner_response.json()["detail"]
        == "Conversation must belong to a lead or customer"
    )

    both_owners_response = client.post(
        "/conversations",
        json={
            "company_id": company["id"],
            "channel": "whatsapp",
            "lead_id": lead["id"],
            "customer_id": customer["id"],
        },
    )
    assert both_owners_response.status_code == 400
    assert (
        both_owners_response.json()["detail"]
        == "Conversation cannot belong to both lead and customer"
    )

    wrong_company_response = client.post(
        "/conversations",
        json={
            "company_id": company["id"],
            "channel": "whatsapp",
            "lead_id": other_lead["id"],
            "customer_id": None,
        },
    )
    assert wrong_company_response.status_code == 400
    assert wrong_company_response.json()["detail"] == "Lead does not belong to this company"

    success_response = client.post(
        "/conversations",
        json={
            "company_id": company["id"],
            "channel": "whatsapp",
            "lead_id": lead["id"],
            "customer_id": None,
        },
    )
    assert success_response.status_code == 200
    data = success_response.json()
    assert data["company_id"] == company["id"]
    assert data["lead_id"] == lead["id"]
    assert data["customer_id"] is None
    assert data["status"] == "open"


def test_agent_reply_persists_customer_and_agent_messages(client, monkeypatch):
    company = create_company(client)
    lead = create_lead(client, company["id"])
    conversation = create_conversation(
        client,
        company_id=company["id"],
        lead_id=lead["id"],
    )

    def fake_generate_agent_reply(message, history):
        assert message == "Ola"
        assert history == []
        return "Resposta do agente"

    monkeypatch.setattr(
        "app.main.generate_agent_reply",
        fake_generate_agent_reply,
    )

    response = client.post(
        f"/conversations/{conversation['id']}/agent-reply",
        json={"content": "Ola"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": conversation["id"],
        "reply": "Resposta do agente",
    }

    messages_response = client.get(f"/conversations/{conversation['id']}/messages")

    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) == 2
    assert messages[0]["sender_type"] == "customer"
    assert messages[0]["content"] == "Ola"
    assert messages[1]["sender_type"] == "agent"
    assert messages[1]["content"] == "Resposta do agente"
