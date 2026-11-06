"""Render real API results without overriding server ordering or pagination."""
import json
import subprocess

import pytest

from test_opportunity_export_order import ordered_opportunities


@pytest.mark.parametrize("sort", ["id", "created_at", "next_action", "priority"])
@pytest.mark.parametrize("offset", [0, 1])
def test_opportunity_api_order_reaches_cards(client, operator_a_headers, ordered_opportunities, sort, offset):
    if sort == "priority":
        path = "/opportunities/priority?limit=3"
    else:
        path = f"/opportunities?sort={sort}&limit=2&offset={offset}&exclude_archived=true"
    response = client.get(path, headers=operator_a_headers)
    assert response.status_code == 200
    rows = response.json()
    assert rows
    subprocess.run(["node", "tests/js/opportunity_render_order.cjs"],
                   input=json.dumps(rows), text=True, check=True)


def test_opportunity_empty_cards():
    subprocess.run(["node", "tests/js/opportunity_render_order.cjs"],
                   input="[]", text=True, check=True)
