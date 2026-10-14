"""Guarded A1 bootstrap: read-only audit by default, one opt-in SDK launch.

Only --apply with OCI_A1_ENABLED=true may create a cloud resource.
No automatic retries; only the fixed Always Free-sized A1 shape, 50GB disk.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
import sys
from typing import Any

from oci_sdk_probe import (
    InspectionBlocked, read_only_inspection, REGION, SHAPE, INSTANCE_NAME,
)
from oci_sdk_tenancy_audit import check_tenancy_usage

OCPUS = 2
MEMORY_GB = 12
BOOT_GB = 50
PROJECT = "business-automation"


def make_launch_details(oci_module: Any, verified: dict[str, str], public_key: str) -> Any:
    """Construct a fixed shape/volume/network request; no caller-supplied sizing."""
    if not public_key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
        raise InspectionBlocked("SSH_PUBLIC_KEY_INVALID")
    if "PRIVATE KEY" in public_key or "\n" in public_key:
        raise InspectionBlocked("SSH_PUBLIC_KEY_INVALID")
    for name, prefix in (
        ("compartment_id", "ocid1.compartment."),
        ("subnet_id", "ocid1.subnet."),
        ("image_id", "ocid1.image."),
    ):
        if not verified.get(name, "").startswith(prefix):
            raise InspectionBlocked(f"LAUNCH_{name.upper()}_INVALID")
    if not verified.get("availability_domain"):
        raise InspectionBlocked("LAUNCH_AD_MISSING")
    models = oci_module.core.models
    return models.LaunchInstanceDetails(
        availability_domain=verified["availability_domain"],
        compartment_id=verified["compartment_id"],
        display_name=INSTANCE_NAME,
        shape=SHAPE,
        shape_config=models.LaunchInstanceShapeConfigDetails(
            ocpus=OCPUS, memory_in_gbs=MEMORY_GB,
        ),
        source_details=models.InstanceSourceViaImageDetails(
            image_id=verified["image_id"], boot_volume_size_in_gbs=BOOT_GB,
        ),
        create_vnic_details=models.CreateVnicDetails(
            subnet_id=verified["subnet_id"], assign_public_ip=True,
        ),
        metadata={"ssh_authorized_keys": public_key},
        instance_options=models.InstanceOptions(
            are_legacy_imds_endpoints_disabled=True,
        ),
        freeform_tags={"project": PROJECT, "intended_tier": "always-free"},
    )


def is_capacity_error(error: Any) -> bool:
    code = str(getattr(error, "code", "")).lower()
    message = str(getattr(error, "message", "")).lower()
    return (
        code in {"outofhostcapacity", "outofcapacity"}
        or "out of capacity" in message
        or "out of host capacity" in message
    )


def attempt(oci_module: Any, config: dict[str, str], public_key: str, *, apply: bool) -> str:
    """Do all possible READ operations before the single optional launch call."""
    if config.get("region") != REGION:
        raise InspectionBlocked("UNEXPECTED_REGION")
    verified = read_only_inspection(oci_module, config)
    audit = check_tenancy_usage(oci_module, config, verified["availability_domain"])
    print(
        f"TENANCY_AUDIT_OK: {audit.compartments_checked} compartment(s); "
        f"{audit.allocated_volume_gb}GB allocated; no A1. No VM created."
    )
    if not apply:
        return "READ_ONLY_OK"

    if os.environ.get("OCI_A1_ENABLED") != "true":
        raise InspectionBlocked("PROVISIONING_FLAG_DISABLED")
    launch = make_launch_details(oci_module, verified, public_key)
    # Oracle retry tokens are valid for ~24h; daily scoped, no SDK retries.
    token = hashlib.sha256(
        f"{config['tenancy']}|{PROJECT}|{datetime.now(timezone.utc).date().isoformat()}".encode()
    ).hexdigest()
    compute = oci_module.core.ComputeClient(config)
    result = compute.launch_instance(
        launch,
        opc_retry_token=token,
        retry_strategy=oci_module.retry.NoneRetryStrategy(),
    )
    instance_id = getattr(getattr(result, "data", None), "id", "")
    if not isinstance(instance_id, str) or not instance_id.startswith("ocid1.instance."):
        raise InspectionBlocked("UNCERTAIN_LAUNCH_RESPONSE_REVIEW_CONSOLE")
    return "CREATED: A1 2 OCPU / 12GB / 50GB in Sao Paulo; no further launch attempted."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Make exactly one allowed launch API call")
    args = parser.parse_args(argv)
    try:
        import oci

        config = oci.config.from_file()
        oci.config.validate_config(config)
        if not args.apply:
            print("READ_ONLY_AUDIT: no mutations permitted.")
        with open(os.path.expanduser("~/.oci/public_ssh.pub"), encoding="utf-8") as fp:
            public_key = fp.read().strip()
        print(attempt(oci, config, public_key, apply=args.apply))
        return 0
    except InspectionBlocked as exc:
        if args.apply and str(exc) == "TENANCY_ALREADY_HAS_A1":
            print("EXISTING_A1: stopped; nothing created.")
            return 0
        print(f"OCI_BLOCKED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        try:
            import oci
            if isinstance(exc, oci.exceptions.ServiceError):
                if args.apply and is_capacity_error(exc):
                    print("NO_CAPACITY: Oracle A1 unavailable; retry at next scheduled hour.")
                    return 0
                category = exc.code if exc.code in {
                    "NotAuthorizedOrNotFound", "NotAuthenticated",
                    "InvalidParameter", "LimitExceeded", "TooManyRequests",
                    "InternalError", "ServiceUnavailable",
                } else "OTHER"
                print(f"OCI_BLOCKED: SERVICE_{int(exc.status)}_{category}", file=sys.stderr)
            else:
                print(f"OCI_BLOCKED: SDK_{type(exc).__name__}", file=sys.stderr)
        except Exception:
            print("OCI_BLOCKED: UNCLASSIFIED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
