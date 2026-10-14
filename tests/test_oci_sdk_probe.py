"""Synthetic tests for read-only OCI SDK discovery; no network and no credentials."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "ops" / "oracle" / "oci_sdk_probe.py"
SPEC = importlib.util.spec_from_file_location("oci_sdk_probe", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def obj(**kwargs):
    return SimpleNamespace(**kwargs)


def make_fake():
    tenancy = "ocid1.tenancy.oc1..synthetic"
    project = obj(
        name="business-automation", id="ocid1.compartment.oc1..synthetic",
        compartment_id=tenancy, lifecycle_state="ACTIVE",
    )
    subnet = obj(
        display_name="public subnet-business-automation-vcn",
        cidr_block="10.0.0.0/24", prohibit_public_ip_on_vnic=False,
        lifecycle_state="AVAILABLE",
    )
    image = obj(
        display_name="Canonical-Ubuntu-24.04-aarch64-2026.10.01",
        operating_system="Canonical Ubuntu", operating_system_version="24.04",
        lifecycle_state="AVAILABLE",
    )
    instances = []
    calls = []

    class Identity:
        def list_compartments(self, **kwargs):
            calls.append("list_compartments")
            return obj(data=[project])
        def list_availability_domains(self, **kwargs):
            calls.append("list_availability_domains")
            return obj(data=[obj(name="fake:SA-SAOPAULO-1-AD-1")])

    class Network:
        def list_subnets(self, **kwargs):
            calls.append("list_subnets")
            return obj(data=[subnet])

    class Compute:
        def list_images(self, **kwargs):
            calls.append("list_images")
            return obj(data=[image])
        def list_instances(self, **kwargs):
            calls.append("list_instances")
            return obj(data=instances)

    fake = obj(
        identity=obj(IdentityClient=lambda config: Identity()),
        core=obj(
            VirtualNetworkClient=lambda config: Network(),
            ComputeClient=lambda config: Compute(),
        ),
        pagination=obj(
            list_call_get_all_results=lambda method, **kwargs: method(**kwargs),
        ),
    )
    return fake, tenancy, calls, instances, subnet


def test_sdk_inspection_never_mutates(monkeypatch, capsys):
    fake, tenancy, calls, _instances, _subnet = make_fake()
    monkeypatch.setenv("OCI_A1_TENANCY_OCID", tenancy)
    MODULE.read_only_inspection(fake, {"region": "sa-saopaulo-1", "tenancy": tenancy})
    assert calls == [
        "list_compartments", "list_availability_domains", "list_subnets",
        "list_images", "list_instances",
    ]
    assert "NO VM CREATED" in capsys.readouterr().out


def test_sdk_rejects_existing_a1(monkeypatch):
    fake, tenancy, _calls, instances, _subnet = make_fake()
    instances.append(obj(
        lifecycle_state="RUNNING", shape="VM.Standard.A1.Flex",
        display_name="other-vm",
    ))
    monkeypatch.setenv("OCI_A1_TENANCY_OCID", tenancy)
    with pytest.raises(MODULE.InspectionBlocked, match="EXISTING_A1"):
        MODULE.read_only_inspection(fake, {"region": "sa-saopaulo-1", "tenancy": tenancy})


def test_sdk_rejects_wrong_subnet(monkeypatch):
    fake, tenancy, _calls, _instances, subnet = make_fake()
    subnet.prohibit_public_ip_on_vnic = True
    monkeypatch.setenv("OCI_A1_TENANCY_OCID", tenancy)
    with pytest.raises(MODULE.InspectionBlocked, match="PUBLIC_SUBNET"):
        MODULE.read_only_inspection(fake, {"region": "sa-saopaulo-1", "tenancy": tenancy})


def test_sdk_rejects_tenancy_mismatch(monkeypatch):
    fake, tenancy, calls, _instances, _subnet = make_fake()
    monkeypatch.setenv("OCI_A1_TENANCY_OCID", "ocid1.tenancy.oc1..other")
    with pytest.raises(MODULE.InspectionBlocked, match="MISMATCH"):
        MODULE.read_only_inspection(fake, {"region": "sa-saopaulo-1", "tenancy": tenancy})
    assert not calls
