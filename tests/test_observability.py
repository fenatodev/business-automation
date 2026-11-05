import logging
import re


def test_requests_return_and_log_correlation_id(client, caplog):
    supplied = "12345678-1234-4234-8234-123456789abc"
    with caplog.at_level(logging.INFO, logger="business_automation.http"):
        response = client.get("/", headers={"X-Correlation-ID": supplied})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == supplied
    records = [record.getMessage() for record in caplog.records]
    assert any("http_request method=GET path=/ status=200" in message for message in records)
    assert any(f"correlation_id={supplied}" in message for message in records)


def test_invalid_correlation_id_is_replaced(client):
    response = client.get("/", headers={"X-Correlation-ID": "customer-phone=secret"})

    correlation_id = response.headers["X-Correlation-ID"]
    assert re.fullmatch(r"[0-9a-f-]{36}", correlation_id)
    assert "secret" not in correlation_id
