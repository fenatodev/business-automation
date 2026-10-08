"""UI operativa: endpoints estáticos, bloqueio de rede e auth de domínio."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_operator_page_is_static_local_and_never_embeds_credentials(client):
    response = client.get("/operator")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Business Automation" in response.text
    assert 'id="workspace" hidden' in response.text
    assert 'id="operator-token"' in response.text
    assert 'src="/operator/app.js"' in response.text
    assert 'href="/operator/styles.css"' in response.text
    assert "<script>" not in response.text
    assert "<style>" not in response.text
    assert "test-operator-a-token" not in response.text
    assert "BA_ACCESS_IDENTITIES_JSON" not in response.text

    for key in ("Cache-Control", "Content-Security-Policy", "X-Frame-Options"):
        assert key in response.headers
    assert response.headers["cache-control"] == "no-store"
    csp = response.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "'unsafe-inline'" not in csp
    assert "http" not in csp
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"


def test_operator_assets_are_fixed_read_only_and_private_cache(client):
    script = client.get("/operator/app.js")
    styles = client.get("/operator/styles.css")
    assert script.status_code == 200
    assert styles.status_code == 200
    assert "text/javascript" in script.headers["content-type"]
    assert "text/css" in styles.headers["content-type"]
    for response in (script, styles):
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-security-policy"].startswith("default-src 'none'")

    assert "Authorization" in script.text
    assert 'credentials: "omit"' in script.text
    assert 'redirect: "error"' in script.text
    assert ".textContent" in script.text
    assert "if (epoch !== sessionEpoch)" in script.text
    assert 'window.addEventListener("pagehide"' in script.text
    assert '$("triage-form").reset()' in script.text
    assert '$(id).textContent = ""' in script.text
    assert 'new Date().toISOString()' in script.text
    assert 'source: "99freelas"' in script.text
    assert '/proposal-brief' in script.text

    for prohibited in (
        "localStorage", "sessionStorage", "document.cookie", "innerHTML",
        "insertAdjacentHTML", "console.log", "eval(", "window.open",
    ):
        assert prohibited not in script.text


def test_ui_is_not_an_authentication_bypass(
    client,
    admin_headers,
    operator_a_headers,
):
    assert client.get("/operator").status_code == 200
    assert client.get("/opportunities").status_code == 401
    assert client.post("/opportunities", json={}).status_code == 401
    assert client.get("/opportunities", headers=admin_headers).status_code == 403
    assert client.get("/opportunities", headers=operator_a_headers).status_code == 200
    assert client.post("/operator").status_code == 405
    assert client.post("/operator/app.js").status_code == 405
    assert "/operator" not in client.get("/openapi.json").json()["paths"]


def test_operator_ui_rejects_remote_client_and_nonlocal_host():
    with TestClient(
        app, base_url="http://localhost", client=("198.51.100.23", 54321)
    ) as remote:
        for route in ("/operator", "/operator/app.js", "/operator/styles.css"):
            assert remote.get(route).status_code == 404

    with TestClient(app, base_url="http://attacker.example") as spoofed_host:
        assert spoofed_host.get("/operator").status_code == 404

    with TestClient(
        app, base_url="http://localhost", client=("127.0.0.1", 54321)
    ) as local:
        assert local.get("/operator").status_code == 200
        assert local.get("/operator/app.js").status_code == 200


def test_client0_form_has_all_required_fields_without_price_or_submission(client):
    page = client.get("/operator").text
    for required in (
        'name="title"', 'name="external_url"', 'name="description"',
        'name="requirements"', 'name="budget"', 'name="deadline"',
        'name="next_action"', 'name="triage_note"',
        'name="offer_reference"', 'name="diagnosis"', 'name="scope"',
        'name="deliverables"', 'name="acceptance_criteria"',
        'name="assumptions"', 'name="risks"', 'name="status"',
    ):
        assert required in page
    assert 'value="ready_for_review"' in page
    assert 'value="approved"' not in page
    assert 'name="price"' not in page
    assert 'name="company_id"' not in page

    # A UI não pode receber paths dinâmicos/estáticos arbitrários.
    for invalid in ("/operator/data.json", "/operator/test.env", "/operator/debug"):
        assert client.get(invalid).status_code == 404
