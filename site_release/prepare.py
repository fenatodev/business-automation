"""Prepare the FenatoDev static site for human review, NEVER deploy.

WP-025/026. Strict source allowlist, no network, no account credentials or
publication privileges. Produces a fresh folder outside the checkout.
The default Cloudflare variant has _headers; portable assets never do.
"""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = PROJECT_ROOT / "site"
ASSETS = ("index.html", "styles.css", "favicon.svg", "_headers")
PORTABLE_ASSETS = ("index.html", "styles.css", "favicon.svg")
TARGETS = ("cloudflare-pages", "portable-static")
REPO_ONLY = frozenset(("README.md",))
MAX_SIZE = {"index.html": 128_000, "styles.css": 128_000,
            "favicon.svg": 32_000, "_headers": 16_000}
ALLOWED_EXTERNAL_HOSTS = frozenset(("github.com", "www.linkedin.com"))
FORBIDDEN_SITE_FRAGMENTS = (
    "127.0.0.1", "localhost", "CLIENT0_OPERATOR_TOKEN",
    "DATABASE_URL", "POSTGRES_PASSWORD", "BA_ACCESS_IDENTITIES_JSON",
    "99freelas.com.br/project", "/operator", "sk-proj-", "ghp_",
)
EXPECTED_HEADER_NAMES = frozenset((
    "content-security-policy", "x-content-type-options", "referrer-policy",
    "x-frame-options", "permissions-policy",
))


class ReleaseError(ValueError):
    """Fail closed without printing source contents or private paths."""


class _HTMLAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.resources: list[tuple[str, dict[str, str | None]]] = []
        self.identifiers: list[str] = []
        self.outbound_links = 0
        self.has_csp = False
        self.has_language = False
        self.has_h1 = False
        self.has_main = False
        self.has_contact = False

    def handle_starttag(self, tag: str,
                        attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"script", "style", "form", "iframe", "object", "embed", "video",
                   "audio", "input", "base", "source", "picture"}:
            raise ReleaseError("unsafe_html_element")
        if any(key.startswith("on") or key == "style" for key in values):
            raise ReleaseError("html_dynamic_attribute")
        if values.get("id") is not None:
            self.identifiers.append(values["id"] or "")
        if tag == "html" and values.get("lang") == "pt-BR":
            self.has_language = True
        if tag == "h1":
            self.has_h1 = True
        if tag == "main":
            self.has_main = True
        if values.get("id") == "contato":
            self.has_contact = True

        if tag == "meta":
            if (values.get("http-equiv") or "").casefold() == "refresh":
                raise ReleaseError("html_redirect_not_allowed")
            if (values.get("http-equiv") or "").casefold() == "content-security-policy":
                policy = values.get("content") or ""
                if ("default-src 'none'" not in policy or
                        "connect-src 'none'" not in policy or
                        "form-action 'none'" not in policy or
                        "style-src 'self'" not in policy):
                    raise ReleaseError("weak_html_csp")
                self.has_csp = True

        if tag == "link":
            if values.get("href") not in {"./styles.css", "./favicon.svg"}:
                raise ReleaseError("unexpected_loaded_asset")
        if tag == "img":
            # Reassess when adding images; images must be local and licensed.
            raise ReleaseError("image_requires_separate_review")
        if tag == "a":
            href = values.get("href")
            if not isinstance(href, str):
                raise ReleaseError("empty_link")
            if href.startswith("#"):
                if len(href) < 2:
                    raise ReleaseError("empty_anchor")
                self.resources.append((href, values))
                return
            url = urlsplit(href)
            if (url.scheme != "https" or url.hostname not in ALLOWED_EXTERNAL_HOSTS
                    or url.username or url.password or url.query
                    or url.fragment or url.port is not None):
                raise ReleaseError("external_link_unapproved")
            if url.hostname == "github.com":
                if not (url.path == "/fenatodev" or url.path.startswith("/fenatodev/")):
                    raise ReleaseError("external_link_unapproved")
            elif url.path != "/in/fenatodev/":
                raise ReleaseError("external_link_unapproved")
            if values.get("target") != "_blank" or not {
                "noopener", "noreferrer"
            }.issubset((values.get("rel") or "").split()):
                raise ReleaseError("external_link_unsafe")
            self.outbound_links += 1


def _read_regular(path: Path, max_bytes: int) -> bytes:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise ReleaseError("source_asset_not_regular_or_excessive")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            opened = os.fstat(descriptor)
            if (opened.st_ino != info.st_ino or opened.st_dev != info.st_dev
                    or not stat.S_ISREG(opened.st_mode)
                    or opened.st_size > max_bytes):
                raise ReleaseError("source_asset_changed")
            payload = os.read(descriptor, max_bytes + 1)
        finally:
            os.close(descriptor)
        if not payload or len(payload) > max_bytes:
            raise ReleaseError("source_asset_empty_or_excessive")
        return payload
    except OSError as exc:
        raise ReleaseError("source_asset_unreadable") from exc


def _audit_headers(text: str) -> None:
    lines = [line for line in text.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if not lines or lines[0] != "/*":
        raise ReleaseError("headers_scope_missing")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line.startswith("  ") or ":" not in line:
            raise ReleaseError("headers_syntax_invalid")
        key, value = line.strip().split(":", 1)
        lowered = key.casefold()
        if not re.fullmatch(r"[A-Za-z][A-Za-z-]+", key) or lowered in headers:
            raise ReleaseError("headers_duplicate_or_invalid")
        headers[lowered] = value.strip()
    if set(headers) != EXPECTED_HEADER_NAMES:
        raise ReleaseError("headers_incomplete")
    csp = headers["content-security-policy"]
    for directive in (
        "default-src 'none'", "script-src 'none'", "style-src 'self'",
        "img-src 'self'", "connect-src 'none'", "form-action 'none'",
        "object-src 'none'", "base-uri 'none'", "frame-ancestors 'none'",
    ):
        if directive not in csp:
            raise ReleaseError("csp_directive_missing")
    if headers["x-content-type-options"] != "nosniff":
        raise ReleaseError("nosniff_missing")
    if headers["x-frame-options"] != "DENY":
        raise ReleaseError("frame_protection_missing")
    if headers["referrer-policy"] != "strict-origin-when-cross-origin":
        raise ReleaseError("referrer_policy_missing")
    for permission in ("camera=()", "microphone=()", "geolocation=()",
                       "payment=()"):
        if permission not in headers["permissions-policy"]:
            raise ReleaseError("permissions_policy_missing")


def inspect_assets(*, site_root: Path = SITE_ROOT) -> dict[str, bytes]:
    """Read only four public files. Other files or symlinks stop packaging."""
    try:
        if not stat.S_ISDIR(site_root.lstat().st_mode):
            raise ReleaseError("site_source_not_regular_directory")
        present = {item.name for item in site_root.iterdir()}
    except OSError as exc:
        raise ReleaseError("site_source_missing") from exc
    if present != set(ASSETS) | REPO_ONLY:
        raise ReleaseError("unexpected_or_missing_source_asset")
    for name in present:
        try:
            if not stat.S_ISREG((site_root / name).lstat().st_mode):
                raise ReleaseError("site_contains_non_regular_file")
        except OSError as exc:
            raise ReleaseError("site_source_asset_unreadable") from exc

    assets = {name: _read_regular(site_root / name, MAX_SIZE[name])
              for name in ASSETS}
    decoded: dict[str, str] = {}
    try:
        for name, data in assets.items():
            decoded[name] = data.decode("utf-8")
    except UnicodeError as exc:
        raise ReleaseError("asset_not_utf8") from exc

    for name, value in decoded.items():
        if any(fragment.casefold() in value.casefold()
               for fragment in FORBIDDEN_SITE_FRAGMENTS):
            raise ReleaseError("private_endpoint_or_secret_marker")
        if name in {"index.html", "styles.css", "_headers"} and not value.endswith("\n"):
            raise ReleaseError("asset_missing_final_newline")

    html = decoded["index.html"]
    audit = _HTMLAudit()
    try:
        audit.feed(html)
        audit.close()
    except ValueError as exc:
        if isinstance(exc, ReleaseError):
            raise
        raise ReleaseError("invalid_html") from exc
    if (not audit.has_language or not audit.has_main or not audit.has_h1
            or not audit.has_contact or not audit.has_csp
            or audit.outbound_links < 4
            or len(audit.identifiers) != len(set(audit.identifiers))):
        raise ReleaseError("html_readiness_incomplete")
    ids = set(audit.identifiers)
    for href, _values in audit.resources:
        if href[1:] not in ids:
            raise ReleaseError("broken_local_anchor")

    css = decoded["styles.css"]
    if (re.search(r"@import\b", css, flags=re.IGNORECASE)
            or re.search(r"url\s*\(", css, flags=re.IGNORECASE)):
        raise ReleaseError("stylesheet_external_asset_not_reviewed")
    if ("prefers-reduced-motion" not in css or ":focus-visible" not in css
            or "@media (max-width: 680px)" not in css):
        raise ReleaseError("responsive_accessibility_contract_missing")

    if not decoded["favicon.svg"].lstrip().startswith("<svg"):
        raise ReleaseError("invalid_static_icon")
    _audit_headers(decoded["_headers"])

    return assets


def prepare_release(
    destination: Path, *,
    site_root: Path = SITE_ROOT,
    target: str = "cloudflare-pages",
) -> dict[str, Any]:
    """Produce one isolated static bundle, never deploying any variant."""
    if target not in TARGETS:
        raise ReleaseError("unknown_release_target")
    audited = inspect_assets(site_root=site_root)
    names = ASSETS if target == "cloudflare-pages" else PORTABLE_ASSETS
    source = {name: audited[name] for name in names}
    dest = destination.expanduser().absolute()
    try:
        resolved = dest.resolve(strict=False)
        repo = PROJECT_ROOT.resolve()
        if resolved == repo or repo in resolved.parents:
            raise ReleaseError("release_output_inside_checkout")
        if dest.exists() or dest.is_symlink():
            raise ReleaseError("release_output_already_exists")
        if not dest.parent.is_dir() or dest.parent.is_symlink():
            raise ReleaseError("release_parent_invalid")
        # The parent must not contain a symlink component resolving into
        # the repo; resolve above rejects that as well.
        dest.mkdir(mode=0o700)
        for name, payload in source.items():
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            descriptor = os.open(dest / name, flags, 0o644)
            with os.fdopen(descriptor, "wb") as output_stream:
                output_stream.write(payload)
    except OSError as exc:
        raise ReleaseError("release_output_creation_failed") from exc

    # Manifest stays in CLI/CI output, not in deploy assets.
    return {
        "kind": "site_release_candidate",
        "status": "ready_for_human_review",
        "target": target,
        "headers_metadata_bundled": target == "cloudflare-pages",
        "http_headers_verified": False,
        "site_asset_count": len(source),
        "assets": [
            {"name": name, "bytes": len(payload),
             "sha256": hashlib.sha256(payload).hexdigest()}
            for name, payload in source.items()
        ],
        "publication_authorized": False,
        "deploy_performed": False,
        "api_exposed": False,
        "hosting_selected_by_operator": False,
        "domain_configured": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build reviewed static assets for a target; NEVER publish them."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=TARGETS, default="cloudflare-pages")
    args = parser.parse_args(argv)
    try:
        report = prepare_release(args.output, target=args.target)
    except ReleaseError as exc:
        print(f"SITE_RELEASE=FAIL reason={exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
