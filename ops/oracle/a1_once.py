"""One safe OCI Always Free A1 launch attempt; suitable for an hourly scheduler.

External OCI CLI credentials and identifiers are supplied only at runtime.
No instance is ever launched unless --apply is explicit.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

REGION = "sa-saopaulo-1"
SHAPE = "VM.Standard.A1.Flex"
OCPUS = 2
MEMORY_GB = 12
BOOT_GB = 50
DISPLAY_NAME = "business-automation-01"


class PreflightError(RuntimeError):
    """A configuration or OCI API problem that must not be retried blindly."""


def required(name: str, environ: dict[str, str]) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise PreflightError(f"Missing required variable: {name}")
    return value


def parse_config(environ: dict[str, str]) -> dict[str, str]:
    config = {name: required(name, environ) for name in (
        "OCI_A1_COMPARTMENT_OCID", "OCI_A1_AVAILABILITY_DOMAIN",
        "OCI_A1_SUBNET_OCID", "OCI_A1_IMAGE_OCID", "OCI_A1_SSH_PUBLIC_KEY_PATH",
    )}
    for field in ("OCI_A1_COMPARTMENT_OCID", "OCI_A1_SUBNET_OCID", "OCI_A1_IMAGE_OCID"):
        if not config[field].startswith("ocid1."):
            raise PreflightError(f"Invalid OCID format: {field}")
    pub_path = Path(config["OCI_A1_SSH_PUBLIC_KEY_PATH"]).expanduser()
    if not pub_path.is_file():
        raise PreflightError("SSH public-key file is missing")
    pubkey = pub_path.read_text(encoding="utf-8").strip()
    if not pubkey.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")) or "PRIVATE KEY" in pubkey:
        raise PreflightError("Expected an OpenSSH PUBLIC key (never use the private key)")
    config["OCI_A1_SSH_PUBLIC_KEY_PATH"] = str(pub_path)
    return config


def cmd_base() -> list[str]:
    return ["oci", "--region", REGION]


def run_cli(args: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError(f"OCI CLI unavailable or timed out: {type(exc).__name__}") from exc
    return proc.returncode, proc.stdout, proc.stderr


def check_existing(config: dict[str, str]) -> None:
    command = cmd_base() + [
        "compute", "instance", "list", "--compartment-id",
        config["OCI_A1_COMPARTMENT_OCID"], "--all", "--output", "json", "--no-retry",
    ]
    status, out, _err = run_cli(command)
    if status:
        raise PreflightError("Cannot verify existing instances; aborting before launch")
    try:
        items = json.loads(out)["data"]
        if not isinstance(items, list):
            raise ValueError("invalid response")
    except (KeyError, ValueError, TypeError) as exc:
        raise PreflightError("Invalid instance-list JSON; aborting before launch") from exc
    for instance in items:
        state = instance.get("lifecycle-state", "")
        if state != "TERMINATED" and (
            instance.get("shape") == SHAPE or instance.get("display-name") == DISPLAY_NAME
        ):
            raise PreflightError("An A1 or matching-name instance already exists; refusing duplicate")


def build_launch(config: dict[str, str]) -> list[str]:
    return cmd_base() + [
        "compute", "instance", "launch",
        "--compartment-id", config["OCI_A1_COMPARTMENT_OCID"],
        "--availability-domain", config["OCI_A1_AVAILABILITY_DOMAIN"],
        "--subnet-id", config["OCI_A1_SUBNET_OCID"],
        "--image-id", config["OCI_A1_IMAGE_OCID"],
        "--ssh-authorized-keys-file", config["OCI_A1_SSH_PUBLIC_KEY_PATH"],
        "--display-name", DISPLAY_NAME,
        "--shape", SHAPE,
        "--shape-config", json.dumps({"ocpus": OCPUS, "memoryInGBs": MEMORY_GB}),
        "--boot-volume-size-in-gbs", str(BOOT_GB),
        "--assign-public-ip", "true",
        "--instance-options", '{"areLegacyImdsEndpointsDisabled":true}',
        "--freeform-tags", '{"project":"business-automation","tier":"always-free-intended"}',
        "--no-retry", "--connection-timeout", "30", "--read-timeout", "120",
    ]


def capacity_shortage(message: str) -> bool:
    text = message.lower()
    return "out of capacity" in text or "out of host capacity" in text


def execute(config: dict[str, str], *, apply: bool) -> str:
    if not apply:
        return f"DRY RUN: {SHAPE}, {OCPUS} OCPUs, {MEMORY_GB} GB RAM, {BOOT_GB} GB disk, {REGION}; no API call."
    check_existing(config)
    status, stdout, stderr = run_cli(build_launch(config))
    if status != 0:
        if capacity_shortage(stderr):
            return "NO_CAPACITY: OCI reports A1 shape unavailable; next scheduled attempt may retry."
        raise PreflightError("Launch rejected (not a recognized capacity shortage); review OCI logs privately")
    try:
        item = json.loads(stdout)["data"]
        ocid = item["id"]
        if not ocid.startswith("ocid1.instance."):
            raise ValueError("missing instance OCID")
    except (KeyError, ValueError, TypeError) as exc:
        raise PreflightError("Uncertain launch result; inspect OCI console before retry") from exc
    return "CREATED: one A1 instance provisioned; verify in OCI Console and disable the workflow."


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Launch at most one Always Free-sized VM")
    args = parser.parse_args(argv)
    environ = dict(os.environ if environ is None else environ)
    try:
        config = parse_config(environ)
        print(execute(config, apply=args.apply))
        return 0
    except PreflightError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
