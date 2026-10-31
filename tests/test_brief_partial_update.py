"""WP-174 — Partial update of proposal brief.

Tests that PATCH /proposal-brief accepts partial updates,
only modifying the fields provided while leaving others unchanged.
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, title="Opp"):
    res = client.post(
        "/opportunities", headers=headers,
        json={
            "source": "manual",
            "external_url": f"https://example.com/{title}",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 200
    return res.json()


def _triage_to_prepare(client, headers, opp_id):
    res = client.patch(
        f"/opportunities/{opp_id}/triage", headers=headers,
        json={"next_action": "prepare_proposal"},
    )
    assert res.status_code == 200
    return res.json()


def _create_brief(client, headers, opp_id):
    res = client.post(
        f"/opportunities/{opp_id}/proposal-brief", headers=headers,
        json={
            "offer_reference": "site-v1",
            "diagnosis": "Cliente precisa de site",
            "scope": "Site institucional",
            "deliverables": "Design + desenvolvimento",
            "acceptance_criteria": "Cliente aprova layout",
            "assumptions": "Cliente fornece conteúdo",
            "risks": "Prazo apertado",
        },
    )
    assert res.status_code == 200
    return res.json()


class TestBriefPartialUpdate:
    """Test PATCH /opportunities/{id}/proposal-brief with partial data."""

    def test_update_single_field(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="SingleCo")
        opp = _create_opportunity(client, operator_a_headers, title="SingleOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        resp = client.patch(
            f"/opportunities/{opp['id']}/proposal-brief", headers=operator_a_headers,
            json={"diagnosis": "Diagnóstico atualizado"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["diagnosis"] == "Diagnóstico atualizado"
        assert data["offer_reference"] == "site-v1"
        assert data["scope"] == "Site institucional"

    def test_update_multiple_fields(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="MultiCo")
        opp = _create_opportunity(client, operator_a_headers, title="MultiOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        resp = client.patch(
            f"/opportunities/{opp['id']}/proposal-brief", headers=operator_a_headers,
            json={
                "scope": "Escopo expandido",
                "deliverables": "Design + dev + deploy",
                "risks": "Risco atualizado",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scope"] == "Escopo expandido"
        assert data["deliverables"] == "Design + dev + deploy"
        assert data["risks"] == "Risco atualizado"
        assert data["diagnosis"] == "Cliente precisa de site"
        assert data["offer_reference"] == "site-v1"

    def test_update_status_only(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="StatusCo")
        opp = _create_opportunity(client, operator_a_headers, title="StatusOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        resp = client.patch(
            f"/opportunities/{opp['id']}/proposal-brief", headers=operator_a_headers,
            json={"status": "ready_for_review"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready_for_review"

    def test_update_assumptions_to_null(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="NullCo")
        opp = _create_opportunity(client, operator_a_headers, title="NullOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        resp = client.patch(
            f"/opportunities/{opp['id']}/proposal-brief", headers=operator_a_headers,
            json={"assumptions": None},
        )
        assert resp.status_code == 200
        assert resp.json()["assumptions"] is None

    def test_empty_body_preserves_brief(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="EmptyCo")
        opp = _create_opportunity(client, operator_a_headers, title="EmptyOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        resp = client.patch(
            f"/opportunities/{opp['id']}/proposal-brief", headers=operator_a_headers,
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["offer_reference"] == "site-v1"
        assert data["diagnosis"] == "Cliente precisa de site"
        assert data["status"] == "draft"

    def test_update_offer_reference(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="OfferCo")
        opp = _create_opportunity(client, operator_a_headers, title="OfferOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        resp = client.patch(
            f"/opportunities/{opp['id']}/proposal-brief", headers=operator_a_headers,
            json={"offer_reference": "site-v2"},
        )
        assert resp.status_code == 200
        assert resp.json()["offer_reference"] == "site-v2"

    def test_update_acceptance_criteria(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="AcceptCo")
        opp = _create_opportunity(client, operator_a_headers, title="AcceptOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        resp = client.patch(
            f"/opportunities/{opp['id']}/proposal-brief", headers=operator_a_headers,
            json={"acceptance_criteria": "Critérios revisados"},
        )
        assert resp.status_code == 200
        assert resp.json()["acceptance_criteria"] == "Critérios revisados"

    def test_tenant_isolation(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="TenantCo")
        _create_company(client, admin_headers, name="TenantCo2")
        opp = _create_opportunity(client, operator_a_headers, title="TenantOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        # Try to edit a brief from a different company (nonexistent for this operator)
        resp = client.patch(
            "/opportunities/99999/proposal-brief", headers=operator_a_headers,
            json={"diagnosis": "Tentativa cross-tenant"},
        )
        assert resp.status_code in (403, 404)

    def test_requires_auth(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, name="AuthCo")
        opp = _create_opportunity(client, operator_a_headers, title="AuthOpp")
        _triage_to_prepare(client, operator_a_headers, opp["id"])
        _create_brief(client, operator_a_headers, opp["id"])

        resp = client.patch(
            f"/opportunities/{opp['id']}/proposal-brief",
            json={"diagnosis": "Sem auth"},
        )
        assert resp.status_code in (401, 403)

    def test_update_nonexistent_opportunity(self, client, operator_a_headers):
        resp = client.patch(
            "/opportunities/99999/proposal-brief", headers=operator_a_headers,
            json={"diagnosis": "Não existe"},
        )
        assert resp.status_code == 404
