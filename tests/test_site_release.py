"""WP-025: static-release security checks using temporary directories only."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from site_release.prepare import (
    ASSETS,
    PROJECT_ROOT,
    SITE_ROOT,
    ReleaseError,
    inspect_assets,
    prepare_release,
)


def copy_site(tmp_path: Path) -> Path:
    """Clone only the public source fixture; never write to the repository."""
    source = tmp_path / "source"
    source.mkdir()
    for item in SITE_ROOT.iterdir():
        assert item.is_file() and not item.is_symlink()
        shutil.copy2(item, source / item.name)
    return source


def replace(source: Path, name: str, before: str, after: str) -> None:
    asset = source / name
    value = asset.read_text(encoding="utf-8")
    assert before in value
    asset.write_text(value.replace(before, after, 1), encoding="utf-8")


def test_release_is_only_four_approved_assets_with_reproducible_hashes(
    tmp_path: Path,
) -> None:
    original = inspect_assets()
    dest = tmp_path / "one"
    report = prepare_release(dest)
    assert report["kind"] == "site_release_candidate"
    assert report["status"] == "ready_for_human_review"
    assert report["site_asset_count"] == 4
    assert {entry.name for entry in dest.iterdir()} == set(ASSETS)
    assert set(original) == set(ASSETS)
    assert "README.md" not in {entry["name"] for entry in report["assets"]}
    for item in report["assets"]:
        blob = (dest / item["name"]).read_bytes()
        assert blob == original[item["name"]]
        assert item["bytes"] == len(blob)
        assert item["sha256"] == hashlib.sha256(blob).hexdigest()
    for flag in (
        "publication_authorized", "deploy_performed", "api_exposed",
        "hosting_selected_by_operator", "domain_configured",
    ):
        assert report[flag] is False

    other = prepare_release(tmp_path / "two")
    assert report == other
    assert not (dest / ".env").exists()
    assert not (dest / "README.md").exists()


def test_release_cli_explicit_output_directory_is_required(tmp_path: Path) -> None:
    run = subprocess.run(
        [sys.executable, "-m", "site_release.prepare", "--output",
         str(tmp_path / "release")],
        capture_output=True, text=True, check=True,
    )
    output = json.loads(run.stdout)
    assert output["site_asset_count"] == 4
    assert output["publication_authorized"] is False
    assert output["deploy_performed"] is False
    assert run.stderr == ""
    assert len(list((tmp_path / "release").iterdir())) == 4


@pytest.mark.parametrize("unexpected", [".env", "case.md", ".gitignore", "backup.json"])
def test_unexpected_source_files_block_all_output(
    tmp_path: Path, unexpected: str,
) -> None:
    root = copy_site(tmp_path)
    (root / unexpected).write_text("synthetic-marker")
    output = tmp_path / "output"
    with pytest.raises(ReleaseError, match="unexpected_or_missing_source_asset"):
        prepare_release(output, site_root=root)
    assert not output.exists()


def test_missing_required_asset_blocks(tmp_path: Path) -> None:
    root = copy_site(tmp_path)
    (root / "_headers").unlink()
    with pytest.raises(ReleaseError, match="unexpected_or_missing_source_asset"):
        inspect_assets(site_root=root)


@pytest.mark.parametrize("name", ["index.html", "styles.css", "favicon.svg",
                                  "_headers", "README.md"])
def test_source_symlink_is_rejected(tmp_path: Path, name: str) -> None:
    root = copy_site(tmp_path)
    path = root / name
    path.unlink()
    path.symlink_to(SITE_ROOT / name)
    with pytest.raises(ReleaseError, match="site_contains_non_regular_file"):
        inspect_assets(site_root=root)


def test_source_directory_symlink_is_rejected(tmp_path: Path) -> None:
    root = copy_site(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ReleaseError, match="site_source_not_regular_directory"):
        inspect_assets(site_root=alias)


@pytest.mark.parametrize("name,max_size", [
    ("index.html", 128_001),
    ("styles.css", 128_001),
    ("favicon.svg", 32_001),
    ("_headers", 16_001),
])
def test_large_asset_is_rejected(
    tmp_path: Path, name: str, max_size: int,
) -> None:
    root = copy_site(tmp_path)
    (root / name).write_bytes(b"a" * max_size)
    with pytest.raises(ReleaseError, match="source_asset_not_regular_or_excessive"):
        inspect_assets(site_root=root)


def test_empty_or_non_utf8_asset_is_rejected(tmp_path: Path) -> None:
    root = copy_site(tmp_path)
    (root / "_headers").write_bytes(b"")
    with pytest.raises(ReleaseError):
        inspect_assets(site_root=root)

    root = copy_site(tmp_path / "second")
    (root / "_headers").write_bytes(b"\xff\xfe\xff")
    with pytest.raises(ReleaseError, match="asset_not_utf8"):
        inspect_assets(site_root=root)


@pytest.mark.parametrize("html", [
    '<script src="https://example.org/a.js"></script>',
    '<form method="post" action="/collect"></form>',
    '<iframe src="/operator"></iframe>',
    '<style>body{color:red}</style>',
    '<a href="https://evil.invalid/x">wrong</a>',
    '<a href="javascript:alert(1)">wrong</a>',
    '<a href="https://github.com/fenatodev-evil">wrong</a>',
    '<meta http-equiv="refresh" content="1;url=https://example.org">',
    '<img src="https://example.org/pixel.gif">',
])
def test_active_content_or_nonapproved_external_asset_is_rejected(
    tmp_path: Path, html: str,
) -> None:
    root = copy_site(tmp_path)
    index = root / "index.html"
    index.write_text(
        index.read_text().replace("</body>", html + "\n</body>"),
        encoding="utf-8",
    )
    with pytest.raises(ReleaseError):
        inspect_assets(site_root=root)


def test_private_service_marker_in_html_is_rejected(tmp_path: Path) -> None:
    root = copy_site(tmp_path)
    replace(root, "index.html", "FenatoDev — Automação",
            "http://127.0.0.1:8788/operator")
    with pytest.raises(ReleaseError, match="private_endpoint_or_secret_marker"):
        inspect_assets(site_root=root)


@pytest.mark.parametrize("item", [
    "@import 'https://example.invalid/track.css';",
    "body{background:url(https://example.invalid/pixel)}",
])
def test_css_remote_or_unreviewed_asset_is_rejected(
    tmp_path: Path, item: str,
) -> None:
    root = copy_site(tmp_path)
    with (root / "styles.css").open("a", encoding="utf-8") as out:
        out.write(item + "\n")
    with pytest.raises(ReleaseError, match="stylesheet_external_asset_not_reviewed"):
        inspect_assets(site_root=root)


def test_broken_anchor_blocks_release(tmp_path: Path) -> None:
    root = copy_site(tmp_path)
    replace(root, "index.html", 'href="#contato"', 'href="#not-found"')
    with pytest.raises(ReleaseError, match="broken_local_anchor"):
        inspect_assets(site_root=root)


@pytest.mark.parametrize("missing", [
    "frame-ancestors 'none'",
    "script-src 'none'",
    "X-Content-Type-Options: nosniff",
    "Permissions-Policy:",
])
def test_missing_header_or_protection_rejects_package(
    tmp_path: Path, missing: str,
) -> None:
    root = copy_site(tmp_path)
    path = root / "_headers"
    value = path.read_text(encoding="utf-8")
    assert missing in value
    path.write_text(value.replace(missing, ""), encoding="utf-8")
    with pytest.raises(ReleaseError):
        inspect_assets(site_root=root)


def test_unsafe_output_paths_and_preexisting_contents_are_rejected(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep.txt").write_text("must-stay")
    with pytest.raises(ReleaseError, match="release_output_already_exists"):
        prepare_release(existing)
    assert (existing / "keep.txt").read_text() == "must-stay"

    symlink = tmp_path / "link"
    symlink.symlink_to(existing, target_is_directory=True)
    with pytest.raises(ReleaseError, match="release_output_already_exists"):
        prepare_release(symlink)
    assert symlink.is_symlink()
    assert (existing / "keep.txt").read_text() == "must-stay"

    # Must fail prior to creating anything in the live repository.
    candidate = PROJECT_ROOT / "wp025-never-create"
    assert not candidate.exists()
    with pytest.raises(ReleaseError, match="release_output_inside_checkout"):
        prepare_release(candidate)
    assert not candidate.exists()


def test_nonexistent_parent_cannot_be_created_implicitly(tmp_path: Path) -> None:
    dest = tmp_path / "missing-parent" / "release"
    with pytest.raises(ReleaseError, match="release_parent_invalid"):
        prepare_release(dest)
    assert not dest.parent.exists()


def test_no_deploy_code_or_credential_access_in_packager() -> None:
    text = (PROJECT_ROOT / "site_release/prepare.py").read_text()
    for token in (
        "import subprocess", "import socket", "import httpx", "import requests",
        "urllib.request", "import boto3", "import cloudflare",
        "os.environ[", "os.system(", "api_token", "deploy_pages(",
    ):
        assert token not in text
    assert "publication_authorized" in text
    assert "deploy_performed" in text
