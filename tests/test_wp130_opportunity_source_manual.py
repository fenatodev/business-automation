"""WP-130 — Fonte configurável na captura manual de oportunidades.

Testa que todas as fontes do Literal são aceitas na criação de oportunidades
e que fontes inválidas são rejeitadas com 422.
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, source="manual", title="Test Opp"):
    res = client.post(
        "/opportunities", headers=headers,
        json={
            "source": source,
            "external_url": f"https://example.com/{title}",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return res


VALID_SOURCES = ["99freelas", "intake", "review_queue", "manual", "import"]


def test_create_opportunity_with_manual_source(client, admin_headers, operator_a_headers):
    """Creating opportunity with source=manual is accepted."""
    _create_company(client, admin_headers, name="ManualCo")
    res = _create_opportunity(client, operator_a_headers, source="manual")
    assert res.status_code == 200
    assert res.json()["source"] == "manual"


def test_create_opportunity_with_99freelas_source(client, admin_headers, operator_a_headers):
    """Creating opportunity with source=99freelas is accepted."""
    _create_company(client, admin_headers, name="FreelasCo")
    res = _create_opportunity(client, operator_a_headers, source="99freelas")
    assert res.status_code == 200
    assert res.json()["source"] == "99freelas"


def test_create_opportunity_with_intake_source(client, admin_headers, operator_a_headers):
    """Creating opportunity with source=intake is accepted."""
    _create_company(client, admin_headers, name="IntakeCo")
    res = _create_opportunity(client, operator_a_headers, source="intake")
    assert res.status_code == 200
    assert res.json()["source"] == "intake"


def test_create_opportunity_with_review_queue_source(client, admin_headers, operator_a_headers):
    """Creating opportunity with source=review_queue is accepted."""
    _create_company(client, admin_headers, name="ReviewCo")
    res = _create_opportunity(client, operator_a_headers, source="review_queue")
    assert res.status_code == 200
    assert res.json()["source"] == "review_queue"


def test_create_opportunity_with_import_source(client, admin_headers, operator_a_headers):
    """Creating opportunity with source=import is accepted."""
    _create_company(client, admin_headers, name="ImportCo")
    res = _create_opportunity(client, operator_a_headers, source="import")
    assert res.status_code == 200
    assert res.json()["source"] == "import"


def test_create_opportunity_with_invalid_source_returns_422(client, admin_headers, operator_a_headers):
    """Creating opportunity with invalid source returns 422."""
    _create_company(client, admin_headers, name="InvalidCo")
    res = client.post(
        "/opportunities", headers=operator_a_headers,
        json={
            "source": "invalid_source",
            "external_url": "https://example.com/test",
            "title": "Test",
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 422


def test_all_valid_sources_accepted(client, admin_headers, operator_a_headers):
    """All valid sources in the Literal are accepted."""
    _create_company(client, admin_headers, name="AllSourceCo")
    for source in VALID_SOURCES:
        res = _create_opportunity(client, operator_a_headers, source=source, title=f"Opp-{source}")
        assert res.status_code == 200, f"source={source} should be accepted"
        assert res.json()["source"] == source


def test_opportunity_source_reflects_in_list(client, admin_headers, operator_a_headers):
    """Opportunity source is reflected in the list endpoint."""
    _create_company(client, admin_headers, name="ListSourceCo")
    res = _create_opportunity(client, operator_a_headers, source="manual")
    assert res.status_code == 200

    res = client.get("/opportunities", headers=operator_a_headers)
    assert res.status_code == 200
    opps = res.json()
    found = [o for o in opps if o["source"] == "manual"]
    assert len(found) >= 1


def test_opportunity_source_reflects_in_count(client, admin_headers, operator_a_headers):
    """Opportunity source is reflected in the count endpoint."""
    _create_company(client, admin_headers, name="CountSourceCo")
    res = _create_opportunity(client, operator_a_headers, source="manual")
    assert res.status_code == 200

    res = client.get("/opportunities/count?source=manual", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_opportunity_source_reflects_in_export(client, admin_headers, operator_a_headers):
    """Opportunity source is reflected in the export CSV endpoint."""
    _create_company(client, admin_headers, name="ExportSourceCo")
    res = _create_opportunity(client, operator_a_headers, source="manual")
    assert res.status_code == 200

    res = client.get("/opportunities/export.csv?source=manual", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/csv; charset=utf-8"
