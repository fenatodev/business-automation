"""WP-029: contract tests for a usable but deliberately unapproved sales pack.

Public Markdown contains no customer data, no prices and no claim of fiscal
issuance, approval, receipt or ERPNext readiness.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/operations"
TEMPLATES = DOCS / "templates"
FILES = {
    "proposal": TEMPLATES / "client0-proposal.template.md",
    "acceptance": TEMPLATES / "client0-acceptance.template.md",
    "financial": TEMPLATES / "client0-financial-check.template.md",
}
PACK = DOCS / "client0-manual-commercial-pack.md"
DECISIONS = DOCS / "client0-launch-decisions.md"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("key", list(FILES))
def test_public_templates_are_explicitly_unapproved_drafts(key: str) -> None:
    content = text(FILES[key])
    assert content.startswith("# ")
    assert "RASCUNHO / NÃO ENVIAR" in content
    assert content.strip().endswith("**ESTADO DESTE MODELO: RASCUNHO / NÃO ENVIAR.**")
    assert "client0-integration-flow-v1" in content
    assert len(content) < 15_000
    assert "[a " in content or "[a" in content or "[ID" in content
    assert "[pendente" in content.lower() or "PENDENTE" in content


def test_proposal_has_scope_tests_limits_and_client_deps() -> None:
    content = text(FILES["proposal"])
    for item in (
        "um fluxo", "Critério de aceite técnico", "Tratamento de dados",
        "Exclusões", "Dependências", "Mudança de escopo",
        "Suporte", "Preço", "tribut", "G4a", "G4b", "G5",
        "verificável", "timeout", "licenças",
    ):
        assert item.casefold() in content.casefold(), item
    assert not re.search(r"R\$\s*\d", content)
    assert "ROI" in content and "sem dados" in content


def test_authorization_sending_and_acceptance_are_independent() -> None:
    content = text(FILES["acceptance"])
    for gate in ("G4a", "G4b", "G5", "G6/G7"):
        assert gate in content
    for status in (
        "PENDENTE", "NÃO ENVIADO", "ACEITE NÃO CONFIRMADO",
    ):
        assert status in content
    assert "Silêncio" in content
    assert "SHA-256" in content
    assert "Hash não é assinatura" in content
    assert "autorização" in content.lower()


def test_financial_template_requires_legitimate_issuer_and_bank_source() -> None:
    content = text(FILES["financial"])
    for term in (
        "RASCUNHO / NÃO ENVIAR", "G8", "G9", "unknown",
        "partial", "settled", "reversed", "overdue", "as_of",
        "Nota", "portal", "regime", "emissor", "fonte financeira",
        "ID do recebível", "banc", "data",
    ):
        assert term.casefold() in content.casefold(), term
    assert "não é nfs-e" in content.lower()
    assert "NÃO" in content


@pytest.mark.parametrize("path", [*FILES.values(), PACK, DECISIONS])
def test_public_commercial_files_contain_no_example_customer_or_price(
    path: Path,
) -> None:
    content = text(path)
    assert not re.search(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)", content)
    assert not re.search(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)", content)
    assert not re.search(r"R\$\s*\d", content)
    assert not re.search(r"(?<!\w)(?:ghp_|sk-proj-)[A-Za-z0-9]+", content)
    assert not re.search(r"https?://127\.0\.0\.1:[0-9]+", content)


def test_operator_backoffice_is_not_replaced_by_faux_erp() -> None:
    content = text(PACK)
    for item in (
        "fallback", "ERPNext", "Quotation", "Sales Invoice",
        "Payment Entry", "autoridade", "documento fiscal",
        "Simples Nacional", "1º/11/2026", "G4a", "G4b", "G5",
        "G8", "G9", "settled", "unknown", "99Freelas",
    ):
        assert item.casefold() in content.casefold(), item
    assert "Nenhuma proposta foi enviada" in content
    assert "F2" in content
    assert "https://www.gov.br/" in content
    assert "https://docs.frappe.io/erpnext/" in content


def test_go_live_has_finite_human_decision_list() -> None:
    content = text(DECISIONS)
    assert len(re.findall(r"\| D\d{2} —", content)) == 9
    for item in ("D01", "D02", "D03", "D04", "D05", "D06",
                 "D07", "D08", "D09"):
        assert item in content
    for flag in ("NÃO AUTORIZADA", "PENDENTE", "MXQ4K",
                 "backup", "fiscal", "prospecção", "recebimento"):
        assert flag.casefold() in content.casefold(), flag
    assert "Não continuar criando WPs sintéticos" in content


def test_all_local_markdown_links_resolve_without_network() -> None:
    for path in (*FILES.values(), PACK, DECISIONS):
        content = text(path)
        for uri in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", content):
            if uri.startswith(("https://", "http://", "#")):
                continue
            link = (path.parent / uri.split("#", 1)[0]).resolve()
            assert link.is_file(), (path.name, uri)


def test_document_pack_does_not_modify_service_contracts() -> None:
    assert (ROOT / "app").is_dir()
    assert (ROOT / "operations").is_dir()
    assert (ROOT / "client0_workspace").is_dir()
    assert "PROPOSTA COMERCIAL" in text(FILES["proposal"])
    assert "CONTATO" not in text(DECISIONS).upper() or "prospecção" in text(DECISIONS)
