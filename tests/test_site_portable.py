"""WP-026: generic static bundle never includes Cloudflare _headers.

All operations are offline and use temporary directories. No TV box, router,
DNS, publishing account or client data is accessed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from site_release.prepare import ASSETS, PORTABLE_ASSETS, ReleaseError, prepare_release


def test_portable_bundle_contains_exactly_three_public_site_files(tmp_path: Path) -> None:
    output = tmp_path / "portable"
    record = prepare_release(output, target="portable-static")
    assert record["target"] == "portable-static"
    assert record["kind"] == "site_release_candidate"
    assert record["status"] == "ready_for_human_review"
    assert record["site_asset_count"] == 3
    assert record["headers_metadata_bundled"] is False
    assert record["http_headers_verified"] is False
    assert set(PORTABLE_ASSETS) == {"index.html", "styles.css", "favicon.svg"}
    assert {p.name for p in output.iterdir()} == set(PORTABLE_ASSETS)
    for denied in ("_headers", ".env", "README.md", ".git", "Caddyfile"):
        assert not (output / denied).exists()
    for item in record["assets"]:
        assert item["name"] in PORTABLE_ASSETS
        blob = (output / item["name"]).read_bytes()
        assert len(blob) == item["bytes"]
        assert hashlib.sha256(blob).hexdigest() == item["sha256"]
    for flag in ("publication_authorized", "deploy_performed", "api_exposed",
                 "hosting_selected_by_operator", "domain_configured"):
        assert record[flag] is False


def test_existing_cloudflare_target_remains_default_and_isolated(tmp_path: Path) -> None:
    old = prepare_release(tmp_path / "cloudflare-default")
    explicit = prepare_release(tmp_path / "cloudflare-explicit", target="cloudflare-pages")
    assert old == explicit
    assert old["site_asset_count"] == 4
    assert old["target"] == "cloudflare-pages"
    assert old["headers_metadata_bundled"] is True
    assert old["http_headers_verified"] is False
    assert set(ASSETS) == {entry["name"] for entry in old["assets"]}
    assert (tmp_path / "cloudflare-default/_headers").is_file()


def test_same_public_bytes_for_both_variants(tmp_path: Path) -> None:
    portable = prepare_release(tmp_path / "p", target="portable-static")
    cloud = prepare_release(tmp_path / "c", target="cloudflare-pages")
    cloud_items = {x["name"]: x for x in cloud["assets"]}
    for asset in portable["assets"]:
        assert asset == cloud_items[asset["name"]]
    assert not (tmp_path / "p/_headers").exists()


def test_portable_output_is_stable_and_source_is_not_modified(tmp_path: Path) -> None:
    first = prepare_release(tmp_path / "one", target="portable-static")
    second = prepare_release(tmp_path / "two", target="portable-static")
    assert first == second
    assert (tmp_path / "one/index.html").read_bytes() == (tmp_path / "two/index.html").read_bytes()


def test_unknown_target_is_rejected_before_any_file_creation(tmp_path: Path) -> None:
    destination = tmp_path / "never-created"
    with pytest.raises(ReleaseError, match="unknown_release_target"):
        prepare_release(destination, target="mxq-auto")
    assert not destination.exists()


def test_portable_rejects_existing_destination_and_preserves_contents(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    marker = target / "operator-notes.txt"
    marker.write_text("preserve")
    with pytest.raises(ReleaseError, match="release_output_already_exists"):
        prepare_release(target, target="portable-static")
    assert marker.read_text() == "preserve"


def test_portable_cli_returns_manifest_without_deployment(tmp_path: Path) -> None:
    output = tmp_path / "release"
    result = subprocess.run(
        [sys.executable, "-m", "site_release.prepare", "--target",
         "portable-static", "--output", str(output)],
        check=True, capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["site_asset_count"] == 3
    assert payload["target"] == "portable-static"
    assert payload["publication_authorized"] is False
    assert payload["deploy_performed"] is False
    assert payload["http_headers_verified"] is False
    assert result.stderr == ""
    assert not (output / "_headers").exists()


def test_portable_cli_does_not_accept_arbitrary_target(tmp_path: Path) -> None:
    output = tmp_path / "reject"
    run = subprocess.run(
        [sys.executable, "-m", "site_release.prepare", "--target", "mxq",
         "--output", str(output)],
        capture_output=True, text=True,
    )
    assert run.returncode != 0
    assert not output.exists()
