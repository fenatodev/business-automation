"""Read-only tenancy-wide quota inventory for OCI Always Free preflight.

Inspect in the HOME region only; any OCI read permission failure aborts.
Never changes a resource, and never prints IDs, credentials, or API responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oci_sdk_probe import InspectionBlocked, SHAPE

MAX_BOOT_AND_BLOCK_GB = 200
PLANNED_BOOT_GB = 50


@dataclass(frozen=True)
class TenancyInventory:
    compartments_checked: int
    existing_a1_count: int
    allocated_volume_gb: int


def _all(oci_module: Any, method: Any, *, stage: str, **kwargs: Any) -> list[Any]:
    """Expose only a fixed read-stage identifier; never raw API errors or IDs."""
    try:
        result = oci_module.pagination.list_call_get_all_results(method, **kwargs).data
    except Exception:
        raise InspectionBlocked(f"TENANCY_{stage}_READ_FAILED") from None
    if not isinstance(result, list):
        raise InspectionBlocked(f"TENANCY_{stage}_RESPONSE_NOT_LIST")
    return result


def check_tenancy_usage(
    oci_module: Any, config: dict[str, str], availability_domain: str
) -> TenancyInventory:
    """Fully enumerate tenanted compartments, VMs and block storage, fail closed."""
    if config.get("region") != "sa-saopaulo-1":
        raise InspectionBlocked("UNEXPECTED_REGION")
    tenancy_id = config.get("tenancy", "")
    if not tenancy_id.startswith("ocid1.tenancy."):
        raise InspectionBlocked("INVALID_TENANCY")

    identity = oci_module.identity.IdentityClient(config)
    compute = oci_module.core.ComputeClient(config)
    storage = oci_module.core.BlockstorageClient(config)

    compartments = _all(
        oci_module, identity.list_compartments, stage="COMPARTMENTS", compartment_id=tenancy_id,
        compartment_id_in_subtree=True, access_level="ANY",
    )
    ids = [tenancy_id]
    seen = {tenancy_id}
    for item in compartments:
        if getattr(item, "lifecycle_state", None) in ("DELETED", "DELETING"):
            continue
        compartment_id = getattr(item, "id", "")
        if not isinstance(compartment_id, str) or not compartment_id.startswith("ocid1.compartment."):
            raise InspectionBlocked("TENANCY_COMPARTMENT_ID_INVALID")
        if compartment_id in seen:
            raise InspectionBlocked("TENANCY_DUPLICATE_COMPARTMENT")
        seen.add(compartment_id)
        ids.append(compartment_id)

    existing_a1 = 0
    total_gb = 0
    for compartment_id in ids:
        instances = _all(
            oci_module, compute.list_instances,
            stage="ROOT_INSTANCES" if compartment_id == tenancy_id else "CHILD_INSTANCES",
            compartment_id=compartment_id,
        )
        for instance in instances:
            if getattr(instance, "lifecycle_state", None) != "TERMINATED":
                if getattr(instance, "shape", None) == SHAPE:
                    existing_a1 += 1
        for method in (storage.list_boot_volumes, storage.list_volumes):
            volumes = _all(
                oci_module, method,
                stage=("ROOT_" if compartment_id == tenancy_id else "CHILD_")
                      + ("BOOT_VOLUME" if method.__name__ == "list_boot_volumes" else "BLOCK_VOLUME"),
                compartment_id=compartment_id, availability_domain=availability_domain,
            )
            for volume in volumes:
                if getattr(volume, "lifecycle_state", None) in ("TERMINATED", "DELETED"):
                    continue
                size = getattr(volume, "size_in_gbs", None)
                if not isinstance(size, (int, float)) or isinstance(size, bool) or size < 0:
                    raise InspectionBlocked("TENANCY_VOLUME_SIZE_UNVERIFIABLE")
                total_gb += size

    if existing_a1:
        raise InspectionBlocked("TENANCY_ALREADY_HAS_A1")
    if total_gb + PLANNED_BOOT_GB > MAX_BOOT_AND_BLOCK_GB:
        raise InspectionBlocked("TENANCY_STORAGE_WOULD_EXCEED_FREE_200GB")
    if not ids:
        raise InspectionBlocked("TENANCY_INVENTORY_EMPTY")
    return TenancyInventory(
        compartments_checked=len(ids),
        existing_a1_count=existing_a1,
        allocated_volume_gb=int(total_gb),
    )
