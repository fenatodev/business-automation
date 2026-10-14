"""Synthetic OCI tenancy audit and guarded launch tests. Never contact Oracle."""

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

OPS_DIR = Path(__file__).resolve().parents[1] / "ops" / "oracle"
if str(OPS_DIR) not in sys.path:
    sys.path.insert(0, str(OPS_DIR))
AUDIT = importlib.import_module("oci_sdk_tenancy_audit")
LAUNCH = importlib.import_module("oci_sdk_launch")
PROBE = importlib.import_module("oci_sdk_probe")

TENANCY = "ocid1.tenancy.oc1..synthetic"
VERIFIED = {
    "compartment_id": "ocid1.compartment.oc1..synthetic",
    "availability_domain": "fake:SA-SAOPAULO-1-AD-1",
    "subnet_id": "ocid1.subnet.oc1..synthetic",
    "image_id": "ocid1.image.oc1..synthetic",
}
PUB = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISyntheticFakePublicOnly"


def synthetic_sdk(*, a1_in_root=False, occupied_gb=0, deny_root=False):
    calls = []
    launched = []
    project = NS(id=VERIFIED["compartment_id"], lifecycle_state="ACTIVE")
    sample_volume = NS(size_in_gbs=occupied_gb, lifecycle_state="AVAILABLE")

    class Identity:
        def list_compartments(self, **kwargs):
            calls.append(("list_compartments", kwargs))
            assert kwargs["access_level"] == "ANY"
            assert kwargs["compartment_id_in_subtree"] is True
            return NS(data=[project])

    class Compute:
        def list_instances(self, **kwargs):
            calls.append(("list_instances", kwargs))
            if deny_root and kwargs["compartment_id"] == TENANCY:
                raise ValueError("IAM_DENIAL_NO_DETAILS")
            result = (
                [NS(lifecycle_state="RUNNING", shape="VM.Standard.A1.Flex")]
                if a1_in_root and kwargs["compartment_id"] == TENANCY
                else []
            )
            return NS(data=result)

        def launch_instance(self, details, **kwargs):
            launched.append((details, kwargs))
            return NS(data=NS(id="ocid1.instance.oc1..synthetic"))

    class Storage:
        def list_boot_volumes(self, **kwargs):
            calls.append(("list_boot_volumes", kwargs))
            return NS(data=[sample_volume] if kwargs["compartment_id"] == TENANCY and occupied_gb else [])
        def list_volumes(self, **kwargs):
            calls.append(("list_volumes", kwargs))
            return NS(data=[])

    class Models:
        @staticmethod
        def LaunchInstanceDetails(**kwargs):
            return NS(**kwargs)
        @staticmethod
        def LaunchInstanceShapeConfigDetails(**kwargs):
            return NS(**kwargs)
        @staticmethod
        def InstanceSourceViaImageDetails(**kwargs):
            return NS(**kwargs)
        @staticmethod
        def CreateVnicDetails(**kwargs):
            return NS(**kwargs)

    sdk = NS(
        identity=NS(IdentityClient=lambda config: Identity()),
        core=NS(
            ComputeClient=lambda config: Compute(),
            BlockstorageClient=lambda config: Storage(),
            models=Models(),
        ),
        retry=NS(NoneRetryStrategy=lambda: NS()),
        pagination=NS(list_call_get_all_results=lambda method, **kwargs: method(**kwargs)),
    )
    return sdk, calls, launched


def test_audit_proves_root_and_child_storage_and_instances():
    sdk, calls, _ = synthetic_sdk(occupied_gb=150)
    stats = AUDIT.check_tenancy_usage(
        sdk, {"region": "sa-saopaulo-1", "tenancy": TENANCY}, VERIFIED["availability_domain"]
    )
    assert stats.compartments_checked == 2
    assert stats.allocated_volume_gb == 150
    assert stats.existing_a1_count == 0
    assert [kind for kind, kw in calls if kw.get("compartment_id") == TENANCY].count("list_instances") == 1


def test_audit_blocks_preexisting_root_a1():
    sdk, _, _ = synthetic_sdk(a1_in_root=True)
    with pytest.raises(PROBE.InspectionBlocked, match="TENANCY_ALREADY_HAS_A1"):
        AUDIT.check_tenancy_usage(
            sdk, {"region": "sa-saopaulo-1", "tenancy": TENANCY}, VERIFIED["availability_domain"]
        )


def test_audit_blocks_storage_over_free_limit():
    sdk, _, _ = synthetic_sdk(occupied_gb=151)
    with pytest.raises(PROBE.InspectionBlocked, match="STORAGE_WOULD_EXCEED"):
        AUDIT.check_tenancy_usage(
            sdk, {"region": "sa-saopaulo-1", "tenancy": TENANCY}, VERIFIED["availability_domain"]
        )


def test_audit_fails_closed_when_root_cannot_be_read():
    sdk, _, _ = synthetic_sdk(deny_root=True)
    with pytest.raises(PROBE.InspectionBlocked, match="ROOT_INSTANCES_READ_FAILED"):
        AUDIT.check_tenancy_usage(
            sdk, {"region": "sa-saopaulo-1", "tenancy": TENANCY}, VERIFIED["availability_domain"]
        )


def test_launch_details_exact_fixed_free_tier_shape():
    sdk, _, _ = synthetic_sdk()
    details = LAUNCH.make_launch_details(sdk, VERIFIED, PUB)
    assert details.shape == "VM.Standard.A1.Flex"
    assert details.shape_config.ocpus == 2
    assert details.shape_config.memory_in_gbs == 12
    assert details.source_details.boot_volume_size_in_gbs == 50
    assert details.source_details.image_id == VERIFIED["image_id"]
    assert details.create_vnic_details.subnet_id == VERIFIED["subnet_id"]
    assert details.create_vnic_details.assign_public_ip is True
    assert details.metadata == {"ssh_authorized_keys": PUB}
    assert details.compartment_id == VERIFIED["compartment_id"]


def test_launch_rejects_any_private_key():
    sdk, _, _ = synthetic_sdk()
    with pytest.raises(PROBE.InspectionBlocked, match="SSH_PUBLIC_KEY_INVALID"):
        LAUNCH.make_launch_details(sdk, VERIFIED, "-----BEGIN PRIVATE KEY-----")


def test_audit_mode_never_launches(monkeypatch):
    sdk, _, launches = synthetic_sdk()
    monkeypatch.setattr(LAUNCH, "read_only_inspection", lambda *a: VERIFIED)
    result = LAUNCH.attempt(
        sdk, {"region": "sa-saopaulo-1", "tenancy": TENANCY}, PUB, apply=False
    )
    assert result == "READ_ONLY_OK"
    assert launches == []


def test_apply_requires_flag_even_after_full_audit(monkeypatch):
    sdk, _, launches = synthetic_sdk()
    monkeypatch.setattr(LAUNCH, "read_only_inspection", lambda *a: VERIFIED)
    monkeypatch.delenv("OCI_A1_ENABLED", raising=False)
    with pytest.raises(PROBE.InspectionBlocked, match="PROVISIONING_FLAG_DISABLED"):
        LAUNCH.attempt(
            sdk, {"region": "sa-saopaulo-1", "tenancy": TENANCY}, PUB, apply=True
        )
    assert launches == []


def test_apply_makes_exactly_one_nonretrying_sdk_launch(monkeypatch):
    sdk, _, launches = synthetic_sdk()
    monkeypatch.setattr(LAUNCH, "read_only_inspection", lambda *a: VERIFIED)
    monkeypatch.setenv("OCI_A1_ENABLED", "true")
    result = LAUNCH.attempt(
        sdk, {"region": "sa-saopaulo-1", "tenancy": TENANCY}, PUB, apply=True
    )
    assert result.startswith("CREATED:")
    assert len(launches) == 1
    details, options = launches[0]
    assert details.shape == "VM.Standard.A1.Flex"
    assert len(options["opc_retry_token"]) == 64
    assert options["retry_strategy"] is not None


def test_apply_never_launches_if_root_has_a1(monkeypatch):
    sdk, _, launches = synthetic_sdk(a1_in_root=True)
    monkeypatch.setattr(LAUNCH, "read_only_inspection", lambda *a: VERIFIED)
    monkeypatch.setenv("OCI_A1_ENABLED", "true")
    with pytest.raises(PROBE.InspectionBlocked, match="TENANCY_ALREADY_HAS_A1"):
        LAUNCH.attempt(
            sdk, {"region": "sa-saopaulo-1", "tenancy": TENANCY}, PUB, apply=True
        )
    assert launches == []


@pytest.mark.parametrize("code,message,expect", [
    ("OutOfHostCapacity", "", True),
    ("UNKNOWN", "Out of capacity for shape", True),
    ("NotAuthorizedOrNotFound", "Cannot access", False),
])
def test_capacity_error_only_known_capacity_errors(code, message, expect):
    assert LAUNCH.is_capacity_error(NS(code=code, message=message)) is expect
