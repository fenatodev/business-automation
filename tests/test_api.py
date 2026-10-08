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



def create_opportunity(
    client,
    headers,
    external_url="https://example.invalid/project/123",
    title="Automacao de processo",
):
    response = client.post(
        "/opportunities",
        headers=headers,
        json={
            "source": "99freelas",
            "external_url": external_url,
            "title": title,
            "description": "Descricao sintetica",
            "budget": "R$ 1.000 - R$ 2.000",
            "deadline": "7 dias",
            "requirements": "Python, API",
            "captured_at": "2026-10-08T12:00:00-03:00",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_opportunity_capture_triage_and_source_validation(
    client,
    admin_headers,
    operator_a_headers,
):
    company = create_company(client, admin_headers)

    opportunity = create_opportunity(
        client,
        operator_a_headers,
    )

    assert opportunity["company_id"] == company["id"]
    assert opportunity["source"] == "99freelas"
    assert opportunity["next_action"] == "pending"
    assert opportunity["triage_note"] is None

    invalid_source = client.post(
        "/opportunities",
        headers=operator_a_headers,
        json={
            "source": "other-source",
            "external_url": "https://example.invalid/project/456",
            "title": "Outra oportunidade",
            "description": "Descricao",
            "captured_at": "2026-10-08T12:00:00-03:00",
        },
    )
    assert invalid_source.status_code == 422

    triage = client.patch(
        f"/opportunities/{opportunity['id']}/triage",
        headers=operator_a_headers,
        json={
            "next_action": "prepare_proposal",
            "triage_note": "Bom fit tecnico; revisar escopo e prazo.",
        },
    )
    assert triage.status_code == 200
    assert triage.json()["next_action"] == "prepare_proposal"
    assert (
        triage.json()["triage_note"]
        == "Bom fit tecnico; revisar escopo e prazo."
    )


def test_opportunity_duplicate_is_scoped_per_company(
    client,
    admin_headers,
    operator_a_headers,
    operator_b_headers,
):
    create_company(
        client,
        admin_headers,
        name="Company A",
        slug="company-a",
    )
    create_company(
        client,
        admin_headers,
        name="Company B",
        slug="company-b",
    )

    url = "https://example.invalid/project/shared"

    first_a = create_opportunity(
        client,
        operator_a_headers,
        external_url=url,
        title="A",
    )
    first_b = create_opportunity(
        client,
        operator_b_headers,
        external_url=url,
        title="B",
    )
    duplicate_a = client.post(
        "/opportunities",
        headers=operator_a_headers,
        json={
            "source": "99freelas",
            "external_url": url,
            "title": "Duplicada",
            "description": "Descricao",
            "captured_at": "2026-10-08T12:00:00-03:00",
        },
    )

    assert first_a["company_id"] != first_b["company_id"]
    assert duplicate_a.status_code == 409
    assert duplicate_a.json() == {
        "detail": "Opportunity already captured"
    }


def test_opportunity_tenant_scope(
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

    opportunity_a = create_opportunity(
        client,
        operator_a_headers,
        external_url="https://example.invalid/project/a",
        title="A",
    )
    opportunity_b = create_opportunity(
        client,
        operator_b_headers,
        external_url="https://example.invalid/project/b",
        title="B",
    )

    list_a = client.get(
        "/opportunities",
        headers=operator_a_headers,
    )
    get_a = client.get(
        f"/opportunities/{opportunity_a['id']}",
        headers=operator_a_headers,
    )
    get_b_as_a = client.get(
        f"/opportunities/{opportunity_b['id']}",
        headers=operator_a_headers,
    )
    patch_b_as_a = client.patch(
        f"/opportunities/{opportunity_b['id']}/triage",
        headers=operator_a_headers,
        json={
            "next_action": "ignore",
            "triage_note": "Cross tenant must not work.",
        },
    )

    assert opportunity_a["company_id"] == company_a["id"]
    assert opportunity_b["company_id"] == company_b["id"]
    assert list_a.status_code == 200
    assert [item["id"] for item in list_a.json()] == [
        opportunity_a["id"]
    ]
    assert get_a.status_code == 200
    assert get_a.json()["id"] == opportunity_a["id"]
    assert get_b_as_a.status_code == 404
    assert patch_b_as_a.status_code == 404


def test_opportunity_routes_require_operator(
    client,
    admin_headers,
    operator_a_headers,
):
    create_company(client, admin_headers)
    opportunity = create_opportunity(
        client,
        operator_a_headers,
    )

    unauthenticated = client.get("/opportunities")
    admin_list = client.get(
        "/opportunities",
        headers=admin_headers,
    )
    admin_create = client.post(
        "/opportunities",
        headers=admin_headers,
        json={
            "source": "99freelas",
            "external_url": "https://example.invalid/project/admin",
            "title": "Admin must not create",
            "description": "Descricao",
            "captured_at": "2026-10-08T12:00:00-03:00",
        },
    )
    admin_patch = client.patch(
        f"/opportunities/{opportunity['id']}/triage",
        headers=admin_headers,
        json={
            "next_action": "follow",
            "triage_note": None,
        },
    )

    assert unauthenticated.status_code == 401
    assert admin_list.status_code == 403
    assert admin_create.status_code == 403
    assert admin_patch.status_code == 403



def prepare_opportunity_for_proposal(
    client,
    headers,
    external_url="https://example.invalid/project/proposal",
    title="Proposal candidate",
):
    opportunity = create_opportunity(
        client,
        headers,
        external_url=external_url,
        title=title,
    )

    response = client.patch(
        f"/opportunities/{opportunity['id']}/triage",
        headers=headers,
        json={
            "next_action": "prepare_proposal",
            "triage_note": "Ready for internal proposal preparation.",
        },
    )
    assert response.status_code == 200
    return response.json()


def proposal_brief_payload(**overrides):
    payload = {
        "offer_reference": "client0-automation-integration-v1",
        "diagnosis": "Manual repetitive workflow.",
        "scope": "Automate validation and handoff.",
        "deliverables": "Implemented flow, tests and runbook.",
        "acceptance_criteria": "End-to-end flow completes with evidence.",
        "assumptions": "Required API access will be provided.",
        "risks": "External provider may rate limit requests.",
    }
    payload.update(overrides)
    return payload


def test_proposal_brief_create_get_update_and_status_validation(
    client,
    admin_headers,
    operator_a_headers,
):
    create_company(client, admin_headers)
    opportunity = prepare_opportunity_for_proposal(
        client,
        operator_a_headers,
    )

    create_response = client.post(
        f"/opportunities/{opportunity['id']}/proposal-brief",
        headers=operator_a_headers,
        json=proposal_brief_payload(),
    )
    assert create_response.status_code == 200

    brief = create_response.json()
    assert brief["opportunity_id"] == opportunity["id"]
    assert brief["status"] == "draft"
    assert brief["offer_reference"] == "client0-automation-integration-v1"

    get_response = client.get(
        f"/opportunities/{opportunity['id']}/proposal-brief",
        headers=operator_a_headers,
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == brief["id"]

    update_payload = proposal_brief_payload(
        diagnosis="Revised diagnosis.",
        scope="Revised scope.",
        deliverables="Revised deliverables.",
        acceptance_criteria="Revised acceptance criteria.",
        assumptions=None,
        risks="Revised risk.",
    )
    update_payload["status"] = "ready_for_review"

    update_response = client.patch(
        f"/opportunities/{opportunity['id']}/proposal-brief",
        headers=operator_a_headers,
        json=update_payload,
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "ready_for_review"
    assert update_response.json()["diagnosis"] == "Revised diagnosis."

    invalid_status = dict(update_payload)
    invalid_status["status"] = "approved"

    invalid_response = client.patch(
        f"/opportunities/{opportunity['id']}/proposal-brief",
        headers=operator_a_headers,
        json=invalid_status,
    )
    assert invalid_response.status_code == 422


def test_proposal_brief_requires_prepare_proposal(
    client,
    admin_headers,
    operator_a_headers,
):
    create_company(client, admin_headers)

    for index, state in enumerate(
        ["pending", "ignore", "follow"],
        start=1,
    ):
        opportunity = create_opportunity(
            client,
            operator_a_headers,
            external_url=f"https://example.invalid/project/not-ready-{index}",
            title=f"Not ready {index}",
        )

        if state != "pending":
            triage = client.patch(
                f"/opportunities/{opportunity['id']}/triage",
                headers=operator_a_headers,
                json={
                    "next_action": state,
                    "triage_note": "Not ready for proposal.",
                },
            )
            assert triage.status_code == 200

        response = client.post(
            f"/opportunities/{opportunity['id']}/proposal-brief",
            headers=operator_a_headers,
            json=proposal_brief_payload(),
        )
        assert response.status_code == 409
        assert response.json() == {
            "detail": "Opportunity is not ready for proposal preparation"
        }


def test_proposal_brief_duplicate_and_forbidden_extra_fields(
    client,
    admin_headers,
    operator_a_headers,
):
    create_company(client, admin_headers)

    opportunity = prepare_opportunity_for_proposal(
        client,
        operator_a_headers,
        external_url="https://example.invalid/project/brief-duplicate",
    )

    first = client.post(
        f"/opportunities/{opportunity['id']}/proposal-brief",
        headers=operator_a_headers,
        json=proposal_brief_payload(),
    )
    assert first.status_code == 200

    duplicate = client.post(
        f"/opportunities/{opportunity['id']}/proposal-brief",
        headers=operator_a_headers,
        json=proposal_brief_payload(),
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "Proposal brief already exists"
    }

    company_extra_opportunity = prepare_opportunity_for_proposal(
        client,
        operator_a_headers,
        external_url="https://example.invalid/project/company-extra",
    )
    company_extra = proposal_brief_payload(company_id=999)

    company_extra_response = client.post(
        (
            f"/opportunities/{company_extra_opportunity['id']}"
            "/proposal-brief"
        ),
        headers=operator_a_headers,
        json=company_extra,
    )
    assert company_extra_response.status_code == 422

    price_extra_opportunity = prepare_opportunity_for_proposal(
        client,
        operator_a_headers,
        external_url="https://example.invalid/project/price-extra",
    )
    price_extra = proposal_brief_payload(price="R$ 10.000")

    price_extra_response = client.post(
        f"/opportunities/{price_extra_opportunity['id']}/proposal-brief",
        headers=operator_a_headers,
        json=price_extra,
    )
    assert price_extra_response.status_code == 422


def test_proposal_brief_cross_tenant_is_hidden(
    client,
    admin_headers,
    operator_a_headers,
    operator_b_headers,
):
    create_company(
        client,
        admin_headers,
        name="Company A",
        slug="company-a",
    )
    create_company(
        client,
        admin_headers,
        name="Company B",
        slug="company-b",
    )

    opportunity_b = prepare_opportunity_for_proposal(
        client,
        operator_b_headers,
        external_url="https://example.invalid/project/company-b-brief",
        title="Company B opportunity",
    )

    create_as_a = client.post(
        f"/opportunities/{opportunity_b['id']}/proposal-brief",
        headers=operator_a_headers,
        json=proposal_brief_payload(),
    )
    assert create_as_a.status_code == 404
    assert create_as_a.json() == {"detail": "Opportunity not found"}

    create_as_b = client.post(
        f"/opportunities/{opportunity_b['id']}/proposal-brief",
        headers=operator_b_headers,
        json=proposal_brief_payload(),
    )
    assert create_as_b.status_code == 200

    get_as_a = client.get(
        f"/opportunities/{opportunity_b['id']}/proposal-brief",
        headers=operator_a_headers,
    )
    assert get_as_a.status_code == 404

    update_payload = proposal_brief_payload()
    update_payload["status"] = "ready_for_review"
    patch_as_a = client.patch(
        f"/opportunities/{opportunity_b['id']}/proposal-brief",
        headers=operator_a_headers,
        json=update_payload,
    )
    assert patch_as_a.status_code == 404


def test_proposal_brief_routes_require_operator(
    client,
    admin_headers,
    operator_a_headers,
):
    create_company(client, admin_headers)
    opportunity = prepare_opportunity_for_proposal(
        client,
        operator_a_headers,
        external_url="https://example.invalid/project/operator-only-brief",
    )

    path = f"/opportunities/{opportunity['id']}/proposal-brief"

    unauthenticated = client.get(path)
    admin_create = client.post(
        path,
        headers=admin_headers,
        json=proposal_brief_payload(),
    )
    admin_get = client.get(
        path,
        headers=admin_headers,
    )

    update_payload = proposal_brief_payload()
    update_payload["status"] = "draft"
    admin_patch = client.patch(
        path,
        headers=admin_headers,
        json=update_payload,
    )

    assert unauthenticated.status_code == 401
    assert admin_create.status_code == 403
    assert admin_get.status_code == 403
    assert admin_patch.status_code == 403
