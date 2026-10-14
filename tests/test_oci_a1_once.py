"""Offline-only, synthetic tests for the OCI A1 capacity retry gate."""

import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "ops" / "oracle" / "a1_once.py"
SPEC = importlib.util.spec_from_file_location("a1_once", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def cfg(tmp_path):
    pub = tmp_path / "ssh.pub"
    pub.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeDemoKeyForTestsOnly\n")
    env = {
        "OCI_A1_COMPARTMENT_OCID": "ocid1.tenancy.oc1..fake",
        "OCI_A1_AVAILABILITY_DOMAIN": "fake:SA-SAOPAULO-1-AD-1",
        "OCI_A1_SUBNET_OCID": "ocid1.subnet.oc1..fake",
        "OCI_A1_IMAGE_OCID": "ocid1.image.oc1..fake",
        "OCI_A1_SSH_PUBLIC_KEY_PATH": str(pub),
    }
    return MODULE.parse_config(env)


def test_dry_run_never_contacts_cloud(cfg, monkeypatch):
    monkeypatch.setattr(MODULE, "run_cli", lambda _: pytest.fail("unexpected OCI call"))
    assert MODULE.execute(cfg, apply=False).startswith("DRY RUN")


def test_build_launch_locked_to_free_cpu_ram_disk_region(cfg):
    command = MODULE.build_launch(cfg)
    assert "VM.Standard.A1.Flex" in command
    assert json.loads(command[command.index("--shape-config") + 1]) == {"ocpus": 2, "memoryInGBs": 12}
    assert command[command.index("--boot-volume-size-in-gbs") + 1] == "50"
    assert command[command.index("--region") + 1] == "sa-saopaulo-1"
    assert "--no-retry" in command
    assert "--ssh-authorized-keys-file" in command


def test_no_capacity_makes_one_attempt(cfg, monkeypatch):
    seen = []
    def fake(cmd):
        seen.append(cmd)
        if "list" in cmd:
            return 0, '{"data":[]}', ""
        return 1, "", "ServiceError: Out of capacity for shape VM.Standard.A1.Flex"
    monkeypatch.setattr(MODULE, "run_cli", fake)
    assert MODULE.execute(cfg, apply=True).startswith("NO_CAPACITY")
    assert len(seen) == 2


def test_duplicate_prevents_launch(cfg, monkeypatch):
    seen = []
    def fake(cmd):
        seen.append(cmd)
        return 0, json.dumps({"data": [{"shape": MODULE.SHAPE, "lifecycle-state": "PROVISIONING"}]}), ""
    monkeypatch.setattr(MODULE, "run_cli", fake)
    with pytest.raises(MODULE.PreflightError, match="already exists"):
        MODULE.execute(cfg, apply=True)
    assert len(seen) == 1


def test_success_stops_and_returns_id(cfg, monkeypatch):
    responses = iter([(0, '{"data":[]}', ""), (0, '{"data":{"id":"ocid1.instance.oc1..fake"}}', "")])
    monkeypatch.setattr(MODULE, "run_cli", lambda _: next(responses))
    assert "CREATED" in MODULE.execute(cfg, apply=True)


def test_ambiguous_success_does_not_retry(cfg, monkeypatch):
    responses = iter([(0, '{"data":[]}', ""), (0, '[]', "")])
    monkeypatch.setattr(MODULE, "run_cli", lambda _: next(responses))
    with pytest.raises(MODULE.PreflightError, match="Uncertain"):
        MODULE.execute(cfg, apply=True)


def test_permissions_and_auth_errors_fail_closed(cfg, monkeypatch):
    responses = iter([(0, '{"data":[]}', ""), (1, "", "NotAuthorizedOrNotFound")])
    monkeypatch.setattr(MODULE, "run_cli", lambda _: next(responses))
    with pytest.raises(MODULE.PreflightError, match="rejected"):
        MODULE.execute(cfg, apply=True)


def test_missing_key_or_private_key_rejected(cfg):
    env = dict(cfg)
    pub = Path(env["OCI_A1_SSH_PUBLIC_KEY_PATH"])
    pub.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nNOT_A_REAL_KEY")
    with pytest.raises(MODULE.PreflightError, match="PUBLIC"):
        MODULE.parse_config(env)
    pub.unlink()
    with pytest.raises(MODULE.PreflightError, match="missing"):
        MODULE.parse_config(env)


def test_missing_required_identifier_rejected(cfg):
    env = dict(cfg)
    del env["OCI_A1_IMAGE_OCID"]
    with pytest.raises(MODULE.PreflightError, match="Missing required"):
        MODULE.parse_config(env)
