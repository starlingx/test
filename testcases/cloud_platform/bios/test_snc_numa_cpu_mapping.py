import pytest
from pytest import mark

from keywords.cloud_platform.bios.snc_keywords import SncKeywords


@mark.p3
@mark.lab_is_simplex
@mark.lab_has_bmc_redfish
def test_snc_numa_cpu_mapping(request: pytest.FixtureRequest):
    """Verify sysinv derives NUMA CPU mapping from sysfs and matches the OS.

    Enables sub-NUMA clustering (vendor-adaptive), then verifies that sysinv
    discovers NUMA nodes from ``/sys/devices/system/node`` rather than the
    old ``physical_id`` socket assumption from ``/proc/cpuinfo``, and that
    the sysinv DB's CPU-to-NUMA-node mapping matches the OS sysfs topology.

    Three checks are evaluated and individually logged PASS/FAIL:
      1. the sysinv agent source references ``/sys/devices/system/node``;
      2. the sysinv DB reports more than one NUMA node (SNC enabled); and
      3. the DB per-node CPU sets match the OS ``node*/cpulist``.


    This is a DISRUPTIVE test. It stages a BIOS change and reboots
    the host, taking the StarlingX system down for a reboot cycle. Only run
    it against a lab that is free for a reboot.
    """
    SncKeywords().verify_numa_cpu_mapping(request)
