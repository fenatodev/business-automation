"""WP-099 — Lead search by keywords."""
import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, operator_headers, company_id, name, interest=None, source="web"):
    res = client.post(
        "/leads",
        headers=operator_headers,
        json={"company_id": company_id, "name": name, "phone": "11999999999", "source": source, "interest": interest},
    )
    assert res.status_code == 200
    return res.json()


class TestLeadSearch:
    """Verify GET /leads?q= searches name and interest."""

    def test_search_by_name(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Maria Silva", "Automação")
        _create_lead(client, operator_a_headers, 1, "João Santos", "Marketing")
        _create_lead(client, operator_a_headers, 1, "Ana Costa", "ERP")

        res = client.get("/leads?q=maria", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 1
        assert leads[0]["name"] == "Maria Silva"

    def test_search_by_interest(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Pedro", "Automação de processos")
        _create_lead(client, operator_a_headers, 1, "Lucia", "Marketing digital")

        res = client.get("/leads?q=automação", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 1
        assert leads[0]["name"] == "Pedro"

    def test_search_case_insensitive(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Maria Silva")

        res = client.get("/leads?q=MARIA", headers=operator_a_headers)
        assert res.status_code == 200
        assert len(res.json()) == 1

        res2 = client.get("/leads?q=maria", headers=operator_a_headers)
        assert res2.status_code == 200
        assert len(res2.json()) == 1

    def test_search_combined_with_status_filter(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Maria", "Automação")
        _create_lead(client, operator_a_headers, 1, "João", "Marketing")

        res = client.get("/leads?q=maria&status=new", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 1
        assert leads[0]["name"] == "Maria"

    def test_search_no_match(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Maria")

        res = client.get("/leads?q=nãoexiste", headers=operator_a_headers)
        assert res.status_code == 200
        assert len(res.json()) == 0

    def test_search_partial_match(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Maria Silva", "Automação completa")

        res = client.get("/leads?q=silva", headers=operator_a_headers)
        assert res.status_code == 200
        assert len(res.json()) == 1

        res2 = client.get("/leads?q=completa", headers=operator_a_headers)
        assert res2.status_code == 200
        assert len(res2.json()) == 1

    def test_search_returns_all_without_q(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_lead(client, operator_a_headers, 1, "Maria")
        _create_lead(client, operator_a_headers, 1, "João")

        res = client.get("/leads", headers=operator_a_headers)
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_search_tenant_isolation(
        self, client, admin_headers, operator_a_headers, operator_b_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        _create_lead(client, operator_a_headers, 1, "Maria", "Automação")
        _create_lead(client, operator_b_headers, 2, "Maria", "Marketing")

        res = client.get("/leads?q=maria", headers=operator_a_headers)
        assert res.status_code == 200
        leads = res.json()
        assert len(leads) == 1
        assert leads[0]["interest"] == "Automação"

    def test_search_requires_auth(self, client):
        res = client.get("/leads?q=test")
        assert res.status_code in (401, 403)
