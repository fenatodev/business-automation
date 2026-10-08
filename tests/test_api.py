from app.services.agent import AgentServiceError


def create_company(
    client,
    admin_headers,
    name="Acme",
    slug="acme",
):
    response = client.post(
        "/companies",
        headers=admin_headers,
        json={"name": name, "slug": slug},
    )
    assert response.status_code == 200
    return response.json()


def create_lead(
    client,
    headers,
    company_id,
    name="Maria",
):
    response = client.post(
        "/leads",
        headers=headers,
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


def create_customer(
    client,
    headers,
    company_id,
    name="Joao",
):
    response = client.post(
        "/customers",
        headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": "11888888888",
            "email": "joao@example.com",
        },
    )
    assert response.status_code == 200
    return response.json()


def create_conversation(
    client,
    headers,
    company_id,
    lead_id=None,
    customer_id=None,
):
    response = client.post(
        "/conversations",
        headers=headers,
        json={
            "company_id": company_id,
            "channel": "whatsapp",
            "lead_id": lead_id,
            "customer_id": customer_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_root_is_public(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Fenato Business Automation API",
        "status": "running",
    }


def test_domain_requires_valid_bearer(client):
    missing = client.get("/leads")
    invalid = client.get(
        "/leads",
        headers={"Authorization": "Bearer definitely-invalid"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json() == {"detail": "Invalid or missing credentials"}
    assert invalid.json() == {"detail": "Invalid or missing credentials"}
    assert "definitely-invalid" not in invalid.text


def test_company_routes_are_admin_only(
    client,
    admin_headers,
    operator_a_headers,
):
    create_response = client.post(
        "/companies",
        headers=operator_a_headers,
        json={"name": "Denied", "slug": "denied"},
    )
    list_response = client.get(
        "/companies",
        headers=operator_a_headers,
    )

    assert create_response.status_code == 403
    assert list_response.status_code == 403

    company = create_company(client, admin_headers)
    admin_list = client.get("/companies", headers=admin_headers)

    assert admin_list.status_code == 200
    assert admin_list.json() == [company]


def test_admin_has_no_implicit_tenant_access(
    client,
    admin_headers,
):
    create_company(client, admin_headers)

    for method, path, body in [
        ("get", "/leads", None),
        ("get", "/customers", None),
        ("get", "/conversations/1", None),
        (
            "post",
            "/leads",
            {
                "company_id": 1,
                "name": "Maria",
                "phone": "11999999999",
                "source": "site",
            },
        ),
    ]:
        kwargs = {"headers": admin_headers}
        if body is not None:
            kwargs["json"] = body

        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403


def test_create_company_duplicate_slug_returns_409(
    client,
    admin_headers,
):
    create_company(client, admin_headers)

    response = client.post(
        "/companies",
        headers=admin_headers,
        json={"name": "Acme 2", "slug": "acme"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Company slug already exists"


def test_operator_lead_scope_and_company_consistency(
    client,
    admin_headers,
    operator_a_headers,
    operator_b_headers,
):
    company_a = create_company(
        client,
        admin_headers,
        name="Company A",
        slug="company-a",
    )
    company_b = create_company(
        client,
        admin_headers,
        name="Company B",
        slug="company-b",
    )

    lead_a = create_lead(
        client,
        operator_a_headers,
        company_a["id"],
        name="Alice",
    )
    lead_b = create_lead(
        client,
        operator_b_headers,
        company_b["id"],
        name="Bob",
    )

    list_a = client.get("/leads", headers=operator_a_headers)
    get_b_as_a = client.get(
        f"/leads/{lead_b['id']}",
        headers=operator_a_headers,
    )
    update_b_as_a = client.patch(
        f"/leads/{lead_b['id']}",
        headers=operator_a_headers,
        json={"status": "qualified"},
    )
    wrong_payload = client.post(
        "/leads",
        headers=operator_a_headers,
        json={
            "company_id": company_b["id"],
            "name": "Wrong Tenant",
            "phone": "11777777777",
            "source": "site",
        },
    )
    wrong_path = client.get(
        f"/companies/{company_b['id']}/leads",
        headers=operator_a_headers,
    )

    assert list_a.status_code == 200
    assert [item["id"] for item in list_a.json()] == [lead_a["id"]]
    assert get_b_as_a.status_code == 404
    assert update_b_as_a.status_code == 404
    assert wrong_payload.status_code == 403
    assert wrong_path.status_code == 403


def test_create_lead_requires_existing_bound_company(
    client,
    operator_a_headers,
):
    response = client.post(
        "/leads",
        headers=operator_a_headers,
        json={
            "company_id": 1,
            "name": "Maria",
            "phone": "11999999999",
            "source": "site",
            "interest": "automacao",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_customer_scope_and_conversion_are_tenant_safe(
    client,
    admin_headers,
    operator_a_headers,
    operator_b_headers,
):
    company_a = create_company(
        client,
        admin_headers,
        name="Company A",
        slug="company-a",
    )
    company_b = create_company(
        client,
        admin_headers,
        name="Company B",
        slug="company-b",
    )
    customer_a = create_customer(
        client,
        operator_a_headers,
        company_a["id"],
        name="Ana",
    )
    customer_b = create_customer(
        client,
        operator_b_headers,
        company_b["id"],
        name="Bruno",
    )
    lead_b = create_lead(
        client,
        operator_b_headers,
        company_b["id"],
        name="Lead B",
    )

    list_a = client.get("/customers", headers=operator_a_headers)
    get_b_as_a = client.get(
        f"/customers/{customer_b['id']}",
        headers=operator_a_headers,
    )
    convert_b_as_a = client.post(
        f"/leads/{lead_b['id']}/convert",
        headers=operator_a_headers,
    )
    wrong_payload = client.post(
        "/customers",
        headers=operator_a_headers,
        json={
            "company_id": company_b["id"],
            "name": "Wrong",
            "phone": "11666666666",
        },
    )
    wrong_path = client.get(
        f"/companies/{company_b['id']}/customers",
        headers=operator_a_headers,
    )

    assert list_a.status_code == 200
    assert [item["id"] for item in list_a.json()] == [customer_a["id"]]
    assert get_b_as_a.status_code == 404
    assert convert_b_as_a.status_code == 404
    assert wrong_payload.status_code == 403
    assert wrong_path.status_code == 403


def test_convert_lead_to_customer_success(
    client,
    admin_headers,
    operator_a_headers,
):
    company = create_company(client, admin_headers)
    lead = create_lead(
        client,
        operator_a_headers,
        company["id"],
    )

    response = client.post(
        f"/leads/{lead['id']}/convert",
        headers=operator_a_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == company["id"]
    assert data["lead_id"] == lead["id"]

    second = client.post(
        f"/leads/{lead['id']}/convert",
        headers=operator_a_headers,
    )
    assert second.status_code == 409


def test_create_conversation_rules_are_tenant_safe(
    client,
    admin_headers,
    operator_a_headers,
    operator_b_headers,
):
    company_a = create_company(
        client,
        admin_headers,
        name="Company A",
        slug="company-a",
    )
    company_b = create_company(
        client,
        admin_headers,
        name="Company B",
        slug="company-b",
    )
    lead_a = create_lead(
        client,
        operator_a_headers,
        company_a["id"],
    )
    lead_b = create_lead(
        client,
        operator_b_headers,
        company_b["id"],
        name="Other",
    )
    customer_a = create_customer(
        client,
        operator_a_headers,
        company_a["id"],
    )

    missing_owner = client.post(
        "/conversations",
        headers=operator_a_headers,
        json={
            "company_id": company_a["id"],
            "channel": "whatsapp",
            "lead_id": None,
            "customer_id": None,
        },
    )
    both_owners = client.post(
        "/conversations",
        headers=operator_a_headers,
        json={
            "company_id": company_a["id"],
            "channel": "whatsapp",
            "lead_id": lead_a["id"],
            "customer_id": customer_a["id"],
        },
    )
    foreign_lead = client.post(
        "/conversations",
        headers=operator_a_headers,
        json={
            "company_id": company_a["id"],
            "channel": "whatsapp",
            "lead_id": lead_b["id"],
            "customer_id": None,
        },
    )
    wrong_company = client.post(
        "/conversations",
        headers=operator_a_headers,
        json={
            "company_id": company_b["id"],
            "channel": "whatsapp",
            "lead_id": lead_a["id"],
            "customer_id": None,
        },
    )
    success = client.post(
        "/conversations",
        headers=operator_a_headers,
        json={
            "company_id": company_a["id"],
            "channel": "whatsapp",
            "lead_id": lead_a["id"],
            "customer_id": None,
        },
    )

    assert missing_owner.status_code == 400
    assert both_owners.status_code == 400
    assert foreign_lead.status_code == 404
    assert wrong_company.status_code == 403
    assert success.status_code == 200
    assert success.json()["company_id"] == company_a["id"]


def test_conversation_and_message_scope(
    client,
    admin_headers,
    operator_a_headers,
    operator_b_headers,
):
    company_a = create_company(
        client,
        admin_headers,
        name="Company A",
        slug="company-a",
    )
    company_b = create_company(
        client,
        admin_headers,
        name="Company B",
        slug="company-b",
    )
    lead_a = create_lead(
        client,
        operator_a_headers,
        company_a["id"],
        name="A",
    )
    lead_b = create_lead(
        client,
        operator_b_headers,
        company_b["id"],
        name="B",
    )
    conversation_a = create_conversation(
        client,
        operator_a_headers,
        company_a["id"],
        lead_id=lead_a["id"],
    )
    conversation_b = create_conversation(
        client,
        operator_b_headers,
        company_b["id"],
        lead_id=lead_b["id"],
    )

    list_a = client.get(
        f"/companies/{company_a['id']}/conversations",
        headers=operator_a_headers,
    )
    get_b_as_a = client.get(
        f"/conversations/{conversation_b['id']}",
        headers=operator_a_headers,
    )
    create_message_b_as_a = client.post(
        f"/conversations/{conversation_b['id']}/messages",
        headers=operator_a_headers,
        json={"sender_type": "human", "content": "no"},
    )
    list_messages_b_as_a = client.get(
        f"/conversations/{conversation_b['id']}/messages",
        headers=operator_a_headers,
    )
    wrong_company_path = client.get(
        f"/companies/{company_b['id']}/conversations",
        headers=operator_a_headers,
    )

    assert list_a.status_code == 200
    assert [item["id"] for item in list_a.json()] == [conversation_a["id"]]
    assert get_b_as_a.status_code == 404
    assert create_message_b_as_a.status_code == 404
    assert list_messages_b_as_a.status_code == 404
    assert wrong_company_path.status_code == 403


def test_agent_reply_persists_customer_and_agent_messages(
    client,
    admin_headers,
    operator_a_headers,
    monkeypatch,
):
    company = create_company(client, admin_headers)
    lead = create_lead(
        client,
        operator_a_headers,
        company["id"],
    )
    conversation = create_conversation(
        client,
        operator_a_headers,
        company["id"],
        lead_id=lead["id"],
    )

    def fake_generate_agent_reply(message, history):
        assert message == "Ola"
        assert history == []
        return "Resposta do agente"

    monkeypatch.setattr(
        "app.routers.conversations.generate_agent_reply",
        fake_generate_agent_reply,
    )

    response = client.post(
        f"/conversations/{conversation['id']}/agent-reply",
        headers=operator_a_headers,
        json={"content": "Ola"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": conversation["id"],
        "reply": "Resposta do agente",
    }

    messages_response = client.get(
        f"/conversations/{conversation['id']}/messages",
        headers=operator_a_headers,
    )

    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) == 2
    assert messages[0]["sender_type"] == "customer"
    assert messages[0]["content"] == "Ola"
    assert messages[1]["sender_type"] == "agent"
    assert messages[1]["content"] == "Resposta do agente"


def test_agent_reply_cannot_cross_tenant(
    client,
    admin_headers,
    operator_a_headers,
    operator_b_headers,
    monkeypatch,
):
    company_a = create_company(
        client,
        admin_headers,
        name="Company A",
        slug="company-a",
    )
    company_b = create_company(
        client,
        admin_headers,
        name="Company B",
        slug="company-b",
    )
    lead_b = create_lead(
        client,
        operator_b_headers,
        company_b["id"],
    )
    conversation_b = create_conversation(
        client,
        operator_b_headers,
        company_b["id"],
        lead_id=lead_b["id"],
    )

    def must_not_run(message, history):
        raise AssertionError("agent should not run across tenant boundary")

    monkeypatch.setattr(
        "app.routers.conversations.generate_agent_reply",
        must_not_run,
    )

    response = client.post(
        f"/conversations/{conversation_b['id']}/agent-reply",
        headers=operator_a_headers,
        json={"content": "Ola"},
    )

    assert company_a["id"] != company_b["id"]
    assert response.status_code == 404


def test_agent_reply_keeps_customer_message_when_agent_service_fails(
    client,
    admin_headers,
    operator_a_headers,
    monkeypatch,
):
    company = create_company(client, admin_headers)
    lead = create_lead(
        client,
        operator_a_headers,
        company["id"],
    )
    conversation = create_conversation(
        client,
        operator_a_headers,
        company["id"],
        lead_id=lead["id"],
    )

    def fake_generate_agent_reply(message, history):
        raise AgentServiceError("Ollama unavailable")

    monkeypatch.setattr(
        "app.routers.conversations.generate_agent_reply",
        fake_generate_agent_reply,
    )

    response = client.post(
        f"/conversations/{conversation['id']}/agent-reply",
        headers=operator_a_headers,
        json={"content": "Ola"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Agent service unavailable"}

    messages_response = client.get(
        f"/conversations/{conversation['id']}/messages",
        headers=operator_a_headers,
    )

    messages = messages_response.json()
    assert len(messages) == 1
    assert messages[0]["sender_type"] == "customer"
    assert messages[0]["content"] == "Ola"


def test_agent_error_does_not_expose_internal_details(
    client,
    admin_headers,
    operator_a_headers,
    monkeypatch,
):
    company = create_company(client, admin_headers)
    lead = create_lead(
        client,
        operator_a_headers,
        company["id"],
    )
    conversation = create_conversation(
        client,
        operator_a_headers,
        company["id"],
        lead_id=lead["id"],
    )

    def fake_generate_agent_reply(message, history):
        raise AgentServiceError(
            "Connection refused http://localhost:11434/api/chat qwen3:8b"
        )

    monkeypatch.setattr(
        "app.routers.conversations.generate_agent_reply",
        fake_generate_agent_reply,
    )

    response = client.post(
        f"/conversations/{conversation['id']}/agent-reply",
        headers=operator_a_headers,
        json={"content": "Ola"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Agent service unavailable"}
    assert "Connection refused" not in response.text
    assert "http://localhost:11434/api/chat" not in response.text
    assert "qwen3:8b" not in response.text


def test_invalid_access_config_does_not_expose_internal_details(
    client,
    monkeypatch,
):
    from app.database import settings

    monkeypatch.setattr(
        settings,
        "access_identities_json",
        "{not-valid-json",
    )

    response = client.get(
        "/leads",
        headers={"Authorization": "Bearer synthetic-test-token"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}
    assert "config" not in response.text.lower()
    assert "token" not in response.text.lower()
    assert "hash" not in response.text.lower()
