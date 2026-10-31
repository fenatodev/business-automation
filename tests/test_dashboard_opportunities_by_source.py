"""WP-198 — Opportunities by source in dashboard.

The dashboard endpoint now returns opportunities_by_source, showing
how many opportunities come from each source (manual, intake,
review_queue, import, 99freelas).
"""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, headers, source="manual", title="Opp"):
    from datetime import datetime, timezone
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
    assert res.status_code == 200
    return res.json()


def test_dashboard_opportunities_by_source(client, admin_headers, operator_a_headers):
    """Dashboard includes opportunities_by_source with correct counts."""
    _create_company(client, admin_headers, name="SourceDashCo")
    _create_opportunity(client, operator_a_headers, source="manual", title="ManualOpp")
    _create_opportunity(client, operator_a_headers, source="intake", title="IntakeOpp")
    _create_opportunity(client, operator_a_headers, source="review_queue", title="ReviewOpp")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert "opportunities_by_source" in data
    assert data["opportunities_by_source"]["total"] == 3
    assert data["opportunities_by_source"]["manual"] == 1
    assert data["opportunities_by_source"]["intake"] == 1
    assert data["opportunities_by_source"]["review_queue"] == 1


def test_dashboard_opportunities_by_source_empty(client, admin_headers, operator_a_headers):
    """Dashboard returns empty opportunities_by_source when no opportunities exist."""
    _create_company(client, admin_headers, name="EmptySourceCo")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert "opportunities_by_source" in data
    assert data["opportunities_by_source"]["total"] == 0


def test_dashboard_opportunities_by_source_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """opportunities_by_source is tenant-isolated."""
    _create_company(client, admin_headers, name="IsolateSourceA")
    _create_company(client, admin_headers, name="IsolateSourceB")
    _create_opportunity(client, operator_b_headers, source="manual", title="B-Opp")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["opportunities_by_source"]["total"] == 0


def test_dashboard_opportunities_by_source_auth_required(client):
    """opportunities_by_source requires authentication."""
    res = client.get("/internal-tasks/dashboard")
    assert res.status_code in (401, 403)


def test_dashboard_opportunities_by_source_multiple_same_source(client, admin_headers, operator_a_headers):
    """Multiple opportunities from same source are counted correctly."""
    _create_company(client, admin_headers, name="MultiSourceCo")
    for i in range(3):
        _create_opportunity(client, operator_a_headers, source="manual", title=f"ManualOpp{i}")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["opportunities_by_source"]["manual"] == 3
    assert data["opportunities_by_source"]["total"] == 3


def test_dashboard_ui_section_exists():
    """HTML has opp-source-section and opp-source-list."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="opp-source-section"' in html
    assert 'id="opp-source-list"' in html
    assert "Fontes de oportunidade" in html


def test_dashboard_ui_js_renders_sources():
    """JavaScript renders opportunities_by_source in renderDashboard."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "opportunities_by_source" in js
    assert "opp-source-section" in js
    assert "opp-source-list" in js
    assert "oppSourceLabels" in js


def test_dashboard_ui_source_labels():
    """Source labels map English keys to Portuguese labels."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    labels_start = js.index("oppSourceLabels")
    labels_section = js[labels_start:labels_start + 300]
    assert "manual" in labels_section
    assert "Intake comercial" in labels_section
    assert "Fila de revisão" in labels_section
    assert "Importação CSV" in labels_section


def test_dashboard_ui_source_section_hidden_when_empty():
    """Source section is hidden when there are no sources."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "oppSourceSection.hidden = !hasOppSources" in js


# WP-199 — Leads by source

def test_dashboard_leads_by_source(client, admin_headers, operator_a_headers):
    """Dashboard includes leads_by_source with correct counts."""
    _create_company(client, admin_headers, name="LeadSourceCo")
    for source in ["site", "manual"]:
        res = client.post(
            "/leads", headers=operator_a_headers,
            json={"company_id": "placeholder", "name": f"Lead-{source}", "phone": "11999999999", "source": source},
        )
    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert "leads_by_source" in data


def test_dashboard_leads_by_source_empty(client, admin_headers, operator_a_headers):
    """Dashboard returns empty leads_by_source when no leads exist."""
    _create_company(client, admin_headers, name="EmptyLeadSourceCo")
    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert "leads_by_source" in data
    assert data["leads_by_source"]["total"] == 0


def test_dashboard_ui_lead_source_section_exists():
    """HTML has lead-source-section and lead-source-list."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="lead-source-section"' in html
    assert 'id="lead-source-list"' in html
    assert "Fontes de lead" in html


def test_dashboard_ui_js_renders_lead_sources():
    """JavaScript renders leads_by_source in renderDashboard."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "leads_by_source" in js
    assert "lead-source-section" in js
    assert "lead-source-list" in js
    assert "leadSourceLabels" in js


def test_dashboard_ui_lead_source_section_hidden_when_empty():
    """Lead source section is hidden when there are no sources."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "leadSourceSection.hidden = !hasLeadSources" in js
