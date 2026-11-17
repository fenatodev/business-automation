"""Company reply-templates endpoints: CRUD /companies/{id}/reply-templates.

Cobre criação, listagem, atualização, exclusão, tenant isolation e
autenticação dos endpoints de reply templates por company.
"""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def test_list_reply_templates_empty(client, admin_headers, operator_a_headers):
    """GET reply-templates returns empty list for new company."""
    company = _create_company(client, admin_headers, name="EmptyCo")
    res = client.get(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json() == []


def test_create_reply_template(client, admin_headers, operator_a_headers):
    """POST reply-templates creates a new template."""
    company = _create_company(client, admin_headers, name="CreateCo")
    res = client.post(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
        json={"name": "Saudação", "content": "Olá! Como posso ajudar?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Saudação"
    assert data["content"] == "Olá! Como posso ajudar?"
    assert "id" in data


def test_create_and_list_reply_template(client, admin_headers, operator_a_headers):
    """Created template appears in list."""
    company = _create_company(client, admin_headers, name="ListCo")
    before = client.get(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
    ).json()
    client.post(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
        json={"name": "Adeus", "content": "Até mais!"},
    )
    res = client.get(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) == len(before) + 1
    assert any(t["name"] == "Adeus" for t in templates)


def test_update_reply_template(client, admin_headers, operator_a_headers):
    """PUT reply-templates/{id} updates an existing template."""
    company = _create_company(client, admin_headers, name="UpdateCo")
    create_res = client.post(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
        json={"name": "Original", "content": "Original content"},
    )
    template_id = create_res.json()["id"]

    res = client.put(
        f"/companies/{company['id']}/reply-templates/{template_id}",
        headers=operator_a_headers,
        json={"name": "Atualizado", "content": "New content"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Atualizado"
    assert data["content"] == "New content"
    assert data["id"] == template_id


def test_update_nonexistent_reply_template(client, admin_headers, operator_a_headers):
    """PUT reply-templates/{id} for nonexistent template returns 404."""
    company = _create_company(client, admin_headers, name="NotFoundCo")
    res = client.put(
        f"/companies/{company['id']}/reply-templates/99999",
        headers=operator_a_headers,
        json={"name": "Ghost", "content": "Ghost content"},
    )
    assert res.status_code == 404


def test_delete_reply_template(client, admin_headers, operator_a_headers):
    """DELETE reply-templates/{id} removes the template."""
    company = _create_company(client, admin_headers, name="DeleteCo")
    before = client.get(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
    ).json()
    create_res = client.post(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
        json={"name": "Remover", "content": "Será removido"},
    )
    template_id = create_res.json()["id"]

    res = client.delete(
        f"/companies/{company['id']}/reply-templates/{template_id}",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["deleted"] is True

    list_res = client.get(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
    )
    assert len(list_res.json()) == len(before)


def test_delete_nonexistent_reply_template(client, admin_headers, operator_a_headers):
    """DELETE reply-templates/{id} for nonexistent template returns 404."""
    company = _create_company(client, admin_headers, name="DelNotFoundCo")
    res = client.delete(
        f"/companies/{company['id']}/reply-templates/99999",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_reply_templates_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot access Operator A's reply templates."""
    company = _create_company(client, admin_headers, name="IsoCo")
    client.post(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
        json={"name": "Privado", "content": "Conteúdo privado"},
    )
    res = client.get(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_b_headers,
    )
    assert res.status_code == 403


def test_reply_templates_requires_auth(client, admin_headers, operator_a_headers):
    """GET reply-templates without auth returns 401."""
    company = _create_company(client, admin_headers, name="AuthCo")
    res = client.get(f"/companies/{company['id']}/reply-templates")
    assert res.status_code in (401, 403)


def test_multiple_reply_templates(client, admin_headers, operator_a_headers):
    """Multiple templates can be created and listed."""
    company = _create_company(client, admin_headers, name="MultiCo")
    before = client.get(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
    ).json()
    for name in ["Template 1", "Template 2", "Template 3"]:
        client.post(
            f"/companies/{company['id']}/reply-templates",
            headers=operator_a_headers,
            json={"name": name, "content": f"Conteúdo de {name}"},
        )
    res = client.get(
        f"/companies/{company['id']}/reply-templates",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert len(res.json()) == len(before) + 3
