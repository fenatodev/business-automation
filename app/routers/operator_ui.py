"""Página interna de operação privada: somente arquivos estáticos, sem dados.

O acesso aos dados continua exclusivamente pelas APIs Bearer existentes.
Essa página não faz login, não altera auth e não concede acesso tenant.
"""

from pathlib import Path
import ipaddress

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse


router = APIRouter(prefix="/operator", include_in_schema=False)

_ASSETS = Path(__file__).resolve().parents[1] / "operator_ui"
_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "testserver"}

_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; form-action 'self'; base-uri 'none'; "
        "frame-ancestors 'none'; object-src 'none'"
    ),
    "Cross-Origin-Resource-Policy": "same-origin",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _local_only(request: Request) -> None:
    client = request.client
    hostname = request.url.hostname
    # TestClient usa client=testclient, host=testserver.
    if client is not None and client.host == "testclient":
        if hostname == "testserver":
            return
    else:
        try:
            is_loopback = client is not None and ipaddress.ip_address(
                client.host
            ).is_loopback
        except ValueError:
            is_loopback = False
        if is_loopback and hostname in _ALLOWED_HOSTS - {"testserver"}:
            return

    raise HTTPException(status_code=404, detail="Not found")


def _static_response(request: Request, filename: str, media_type: str):
    _local_only(request)
    return FileResponse(
        _ASSETS / filename,
        media_type=media_type,
        headers=_HEADERS,
    )


@router.get("")
def operator_page(request: Request):
    return _static_response(request, "index.html", "text/html")


@router.get("/app.js")
def operator_script(request: Request):
    return _static_response(request, "app.js", "text/javascript")


@router.get("/styles.css")
def operator_styles(request: Request):
    return _static_response(request, "styles.css", "text/css")
