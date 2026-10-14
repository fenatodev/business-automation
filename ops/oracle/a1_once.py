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


def classify_oci_failure(stdout: str, stderr: str) -> str:
    """Log only a bounded public error category, never request bodies or OCIDs."""
    raw = (stderr or stdout).lower()
    if "no such option" in raw or "no such command" in raw or "usage: oci " in raw:
        return "CLI_USAGE"
    if "invalidconfig" in raw or "could not find config" in raw or "config file" in raw:
        return "CLI_CONFIG"
    if "securitytokenexpired" in raw or "notauthenticated" in raw or "unauthorized" in raw:
        return "AUTHENTICATION"
    if "notauthorizedornotfound" in raw or "not authorized" in raw:
        return "IAM_NOT_AUTHORIZED"
    if "invalidparameter" in raw or "invalid parameter" in raw:
        return "INVALID_REQUEST"
    if "limitexceeded" in raw or "too many requests" in raw:
        return "RATE_LIMIT"
    if "serviceunavailable" in raw or "internalerror" in raw:
        return "SERVICE_UNAVAILABLE"
    if "certificate verify failed" in raw or "ssLError" in raw.lower():
        return "TLS_FAILURE"
    return "UNCLASSIFIED"


def _list_data(command: list[str], label: str) -> list[dict]:
    """Read OCI metadata, without leaking identities, credentials or API responses."""
    status, stdout, stderr = run_cli(command + ["--output", "json", "--no-retry"])
    if status != 0:
        error_class = classify_oci_failure(stdout, stderr)
        raise PreflightError(f"Cannot discover {label}: {error_class}; inspect OCI credentials, policy and CLI invocation")
    try:
        items = json.loads(stdout)["data"]
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise ValueError("expected list of objects")
    except (KeyError, ValueError, TypeError) as exc:
        raise PreflightError(f"Invalid response discovering {label}") from exc
    return items


def _unique(items: list[dict], key: str, value: str, label: str) -> dict:
    matches = [item for item in items if item.get(key) == value
               and item.get("lifecycle-state", "ACTIVE") not in ("DELETED", "TERMINATED")]
    if len(matches) != 1:
        raise PreflightError(f"Expected exactly one {label}; found {len(matches)}")
    return matches[0]


def discover_config(environ: dict[str, str]) -> dict[str, str]:
    """Resolve OCIDs by exact resource names, read-only; fail on ambiguity."""
    tenancy = required("OCI_A1_TENANCY_OCID", environ)
    if not tenancy.startswith("ocid1.tenancy."):
        raise PreflightError("Invalid tenancy OCID")

    compartments = _list_data(cmd_base() + [
        "iam", "compartment", "list", "--compartment-id", tenancy,
        "--access-level", "ACCESSIBLE", "--all",
    ], "project compartment")
    compartment = _unique(compartments, "name", "business-automation", "project compartment")
    compartment_id = compartment.get("id", "")
    if not compartment_id.startswith("ocid1.compartment."):
        raise PreflightError("Invalid discovered project compartment")
    if compartment.get("compartment-id") != tenancy:
        raise PreflightError("Project compartment is not a direct child of tenancy")

    ads = _list_data(cmd_base() + [
        "iam", "availability-domain", "list", "--compartment-id", tenancy,
    ], "availability domain")
    if len(ads) != 1 or not ads[0].get("name"):
        raise PreflightError("Expected exactly one availability domain in Sao Paulo")
    ad = ads[0]["name"]

    subnets = _list_data(cmd_base() + [
        "network", "subnet", "list", "--compartment-id", tenancy, "--all",
    ], "public subnet")
    subnet = _unique(subnets, "display-name", "public subnet-business-automation-vcn", "public subnet")
    subnet_id = subnet.get("id", "")
    if not subnet_id.startswith("ocid1.subnet.") or subnet.get("prohibit-public-ip-on-vnic") is not False:
        raise PreflightError("Expected a verified public subnet; refusing private subnet")
    if subnet.get("cidr-block") != "10.0.0.0/24":
        raise PreflightError("Unexpected public subnet CIDR")

    images = _list_data(cmd_base() + [
        "compute", "image", "list", "--compartment-id", compartment_id,
        "--operating-system", "Canonical Ubuntu", "--operating-system-version", "24.04",
        "--shape", SHAPE, "--lifecycle-state", "AVAILABLE", "--all",
    ], "Ubuntu 24.04 ARM image")
    candidates = [i for i in images if i.get("id", "").startswith("ocid1.image.")
                  and i.get("operating-system") == "Canonical Ubuntu"
                  and i.get("operating-system-version") == "24.04"
                  and "aarch64" in (i.get("display-name") or "").lower()]
    if not candidates:
        raise PreflightError("No verified Ubuntu 24.04 AArch64 platform image")
    image_id = max(candidates, key=lambda i: i.get("time-created", ""))["id"]

    resolved = dict(environ)
    resolved.update({
        "OCI_A1_COMPARTMENT_OCID": compartment_id,
        "OCI_A1_AVAILABILITY_DOMAIN": ad,
        "OCI_A1_SUBNET_OCID": subnet_id,
        "OCI_A1_IMAGE_OCID": image_id,
    })
    return parse_config(resolved)


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true", help="Discover resources, then launch at most one VM")
    modes.add_argument("--inspect", action="store_true", help="Read-only discovery and duplicate check")
    args = parser.parse_args(argv)
    environ = dict(os.environ if environ is None else environ)
    try:
        if not args.apply and not args.inspect:
            print(f"DRY RUN: {SHAPE}, {OCPUS} OCPUs, {MEMORY_GB} GB RAM, "
                  f"{BOOT_GB} GB disk in {REGION}; no API call.")
            return 0
        config = discover_config(environ)
        if args.inspect:
            check_existing(config)
            print("INSPECT_OK: exact project compartment, public subnet and Ubuntu ARM64 image; "
                  "no existing A1 in project compartment. No VM created.")
        else:
            print(execute(config, apply=True))
        return 0
    except PreflightError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
