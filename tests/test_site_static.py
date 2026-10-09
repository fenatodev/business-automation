"""WP-021 — structural and security checks for the public static site.

Tests never start the private API, import its settings or touch a database.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
HTML = (SITE / "index.html").read_text(encoding="utf-8")
CSS = (SITE / "styles.css").read_text(encoding="utf-8")


class Elements(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))

    def selected(self, name: str) -> list[dict[str, str | None]]:
        return [attrs for tag, attrs in self.tags if tag == name]


def parsed() -> Elements:
    document = Elements()
    document.feed(HTML)
    document.close()
    return document


def test_site_assets_exist_and_do_not_depend_on_a_build_step() -> None:
    assert (SITE / "index.html").is_file()
    assert (SITE / "styles.css").is_file()
    favicon = (SITE / "favicon.svg").read_text(encoding="utf-8")
    assert "<svg" in favicon and 'xmlns="http://www.w3.org/2000/svg"' in favicon
    assert not (SITE / "node_modules").exists()
    assert not (SITE / ".env").exists()


def test_html_has_language_title_mobile_viewport_and_landmarks() -> None:
    document = parsed()
    assert document.selected("html")[0].get("lang") == "pt-BR"
    assert len(document.selected("title")) == 1
    assert len(document.selected("h1")) == 1
    assert len(document.selected("main")) == 1
    assert len(document.selected("nav")) == 1
    assert any(meta.get("name") == "viewport" for meta in document.selected("meta"))
    assert any(meta.get("name") == "description" for meta in document.selected("meta"))


def test_in_page_links_resolve_and_identifiers_are_unique() -> None:
    document = parsed()
    identifiers = [attrs["id"] for _, attrs in document.tags if attrs.get("id")]
    assert len(identifiers) == len(set(identifiers))
    for link in document.selected("a"):
        href = link.get("href")
        assert href is not None
        if href.startswith("#"):
            assert href[1:] in identifiers, href
    assert {"inicio", "servicos", "metodo", "evidencias", "contato", "conteudo"}.issubset(
        set(identifiers)
    )


def test_outgoing_links_only_reference_known_public_profiles_or_projects() -> None:
    document = parsed()
    external = 0
    for link in document.selected("a"):
        href = link["href"]
        if href is None or href.startswith("#"):
            continue
        parsed_url = urlparse(href)
        assert parsed_url.scheme == "https", href
        assert parsed_url.username is None and parsed_url.password is None, href
        assert parsed_url.query == "" and parsed_url.fragment == "", href
        assert parsed_url.hostname in {"github.com", "www.linkedin.com"}, href
        if parsed_url.hostname == "github.com":
            assert parsed_url.path.startswith("/fenatodev"), href
        else:
            assert parsed_url.path == "/in/fenatodev/", href
        assert link.get("target") == "_blank", href
        assert {"noopener", "noreferrer"}.issubset(
            set((link.get("rel") or "").split())
        ), href
        external += 1
    assert external >= 4


def test_no_network_loaders_forms_trackers_or_private_endpoints() -> None:
    document = parsed()
    prohibited_tags = {"script", "form", "iframe", "video", "audio", "object", "embed"}
    assert not any(tag in prohibited_tags for tag, _ in document.tags)
    assert all(tag != "input" for tag, _ in document.tags)
    assert all(tag != "img" for tag, _ in document.tags)
    for tag, attrs in document.tags:
        assert not any(k.startswith("on") for k in attrs), tag
        assert "style" not in attrs, tag
    for asset in document.selected("link"):
        href = asset.get("href") or ""
        assert href in {"./styles.css", "./favicon.svg"}
    # Only deployable assets are scanned; the README documents a safe localhost preview.
    for file in (SITE / "index.html", SITE / "styles.css", SITE / "favicon.svg"):
        value = file.read_text(encoding="utf-8")
        assert "127.0.0.1" not in value
        assert "localhost" not in value
        assert "BA_ACCESS_IDENTITIES_JSON" not in value
        assert "CLIENT0_OPERATOR_TOKEN" not in value
        assert "DATABASE_URL" not in value
        assert "site-de-vendas-de-instrumentos-musicais" not in value
        assert "99freelas.com.br/project" not in value
    assert "@import" not in CSS
    assert not re.search(r"url\(\s*['\"]?https?://", CSS)


def test_static_meta_csp_blocks_scripts_forms_and_remote_connections() -> None:
    document = parsed()
    policies = [
        meta.get("content") or ""
        for meta in document.selected("meta")
        if (meta.get("http-equiv") or "").lower() == "content-security-policy"
    ]
    assert len(policies) == 1
    policy = policies[0]
    for fragment in (
        "default-src 'none'",
        "style-src 'self'",
        "img-src 'self'",
        "connect-src 'none'",
        "form-action 'none'",
        "object-src 'none'",
        "base-uri 'none'",
    ):
        assert fragment in policy


def test_technical_demo_and_honest_limitations_are_visible() -> None:
    document = parsed()
    repo_links = [a.get("href") for a in document.selected("a")]
    assert "https://github.com/fenatodev/business-automation/tree/main/examples" in repo_links
    assert "https://github.com/fenatodev/ai-coding-evaluation" in repo_links
    assert "https://github.com/fenatodev/lai-harness" in repo_links
    assert "DEMO EXECUTÁVEL" in HTML
    assert "DADOS FICTÍCIOS" in HTML
    assert "Não é uma integração de cliente" in HTML
    assert "Não implicam clientes atendidos" in HTML
    assert "Não há formulário ou envio automático" in HTML


def test_mobile_keyboard_and_reduced_motion_rules_exist() -> None:
    document = parsed()
    assert any(
        a.get("href") == "#conteudo" and a.get("class") == "skip-link"
        for a in document.selected("a")
    )
    assert ":focus-visible" in CSS
    assert "prefers-reduced-motion: reduce" in CSS
    assert "@media (max-width: 680px)" in CSS
    assert "@media (max-width: 390px)" in CSS
    assert "overflow-x: hidden" not in CSS


def test_contact_requires_user_to_navigate_to_external_service() -> None:
    document = parsed()
    links = [a.get("href") for a in document.selected("a")]
    assert "https://www.linkedin.com/in/fenatodev/" in links
    assert "https://github.com/fenatodev" in links
    assert not any((a or "").startswith(("mailto:", "tel:", "javascript:")) for a in links)
