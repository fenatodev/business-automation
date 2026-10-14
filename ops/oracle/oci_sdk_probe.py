"""Fail-closed OCI read-only SDK inspection. Never creates or changes resources."""

from __future__ import annotations

import os
import re
import sys
from typing import Any

REGION = "sa-saopaulo-1"
PROJECT = "business-automation"
SUBNET = "public subnet-business-automation-vcn"
SHAPE = "VM.Standard.A1.Flex"
INSTANCE_NAME = "business-automation-01"


class InspectionBlocked(RuntimeError):
    """Public and non-sensitive failure reason."""


def exactly_one(resources: list[Any], *, attribute: str, name: str, label: str) -> Any:
    matched = [
        x for x in resources
        if getattr(x, attribute, None) == name
        and getattr(x, "lifecycle_state", "ACTIVE") not in ("DELETED", "TERMINATED")
    ]
    if len(matched) != 1:
        raise InspectionBlocked(f"{label}: expected exactly one matching resource, got {len(matched)}")
    return matched[0]


def check_instances(resources: list[Any]) -> None:
    if not isinstance(resources, list):
        raise InspectionBlocked("VM_INVENTORY_NOT_LIST")
    for item in resources:
        if getattr(item, "lifecycle_state", None) != "TERMINATED":
            if getattr(item, "shape", None) == SHAPE or getattr(item, "display_name", None) == INSTANCE_NAME:
                raise InspectionBlocked("EXISTING_A1_OR_MATCHING_INSTANCE")
    # Absence is proved only in this one compartment, not across the tenancy.


def check_public_subnet(subnet: Any) -> None:
    if getattr(subnet, "cidr_block", None) != "10.0.0.0/24":
        raise InspectionBlocked("UNEXPECTED_SUBNET_CIDR")
    if getattr(subnet, "prohibit_public_ip_on_vnic", None) is not False:
        raise InspectionBlocked("NOT_A_VERIFIED_PUBLIC_SUBNET")


def read_only_inspection(oci_module: Any, config: dict[str, str]) -> None:
    if config.get("region") != REGION:
        raise InspectionBlocked("UNEXPECTED_REGION")
    tenancy = config.get("tenancy", "")
    if not tenancy.startswith("ocid1.tenancy."):
        raise InspectionBlocked("INVALID_TENANCY")
    if tenancy != os.environ.get("OCI_A1_TENANCY_OCID"):
        raise InspectionBlocked("TENANCY_ENV_CONFIG_MISMATCH")

    identity = oci_module.identity.IdentityClient(config)
    network = oci_module.core.VirtualNetworkClient(config)
    compute = oci_module.core.ComputeClient(config)
    def all_pages(method: Any, **kwargs: Any) -> list[Any]:
        result = oci_module.pagination.list_call_get_all_results(method, **kwargs).data
        if not isinstance(result, list):
            raise InspectionBlocked("SDK_RESPONSE_NOT_LIST")
        return result

    compartments = all_pages(
        identity.list_compartments, compartment_id=tenancy,
        compartment_id_in_subtree=False, access_level="ACCESSIBLE",
    )
    project = exactly_one(compartments, attribute="name", name=PROJECT, label="PROJECT_COMPARTMENT")
    if getattr(project, "compartment_id", None) != tenancy:
        raise InspectionBlocked("PROJECT_NOT_DIRECT_CHILD")
    if not getattr(project, "id", "").startswith("ocid1.compartment."):
        raise InspectionBlocked("INVALID_PROJECT_OCID")

    ads = identity.list_availability_domains(compartment_id=tenancy).data
    if not isinstance(ads, list) or len(ads) != 1 or not getattr(ads[0], "name", None):
        raise InspectionBlocked("UNEXPECTED_AVAILABILITY_DOMAINS")

    subnets = all_pages(network.list_subnets, compartment_id=tenancy)
    subnet = exactly_one(subnets, attribute="display_name", name=SUBNET, label="PUBLIC_SUBNET")
    check_public_subnet(subnet)

    images = all_pages(
        compute.list_images, compartment_id=project.id,
        operating_system="Canonical Ubuntu", operating_system_version="24.04", shape=SHAPE,
    )
    valid_images = [
        img for img in images
        if getattr(img, "operating_system", None) == "Canonical Ubuntu"
        and getattr(img, "operating_system_version", None) == "24.04"
        and "aarch64" in (getattr(img, "display_name", "") or "").lower()
        and getattr(img, "lifecycle_state", None) == "AVAILABLE"
    ]
    if not valid_images:
        raise InspectionBlocked("NO_VERIFIED_UBUNTU_2404_ARM_IMAGE")

    instances = all_pages(compute.list_instances, compartment_id=project.id)
    check_instances(instances)
    print("SDK_INSPECT_OK: identity, compartment, AD, subnet, image and VM inventory verified. NO VM CREATED.")


def main() -> int:
    try:
        import oci
        config = oci.config.from_file()
        oci.config.validate_config(config)
        read_only_inspection(oci, config)
        return 0
    except InspectionBlocked as error:
        print(f"SDK_BLOCKED: {error}", file=sys.stderr)
    except Exception as error:
        try:
            import oci
            if isinstance(error, oci.exceptions.ServiceError):
                status = int(getattr(error, "status", 0))
                code = getattr(error, "code", "")
                safe_code = code if code in {
                    "NotAuthorizedOrNotFound", "NotAuthenticated",
                    "InvalidParameter", "InternalError", "LimitExceeded",
                    "TooManyRequests", "ServiceUnavailable",
                } else "OTHER"
                print(f"SDK_BLOCKED: SERVICE_{status}_{safe_code}", file=sys.stderr)
            else:
                # Never print exception text: it may contain OCIDs, HTTP bodies or keys.
                print(f"SDK_BLOCKED: SDK_{type(error).__name__}", file=sys.stderr)
        except Exception:
            print("SDK_BLOCKED: UNSPECIFIED", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
