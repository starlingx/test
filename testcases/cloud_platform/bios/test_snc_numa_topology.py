import pytest
from pytest import mark

from keywords.cloud_platform.bios.snc_keywords import SncKeywords


@mark.p3
@mark.lab_is_simplex
@mark.lab_has_bmc_redfish
def test_snc_numa_topology(request: pytest.FixtureRequest):
    """Verify the NUMA topology is detected correctly with SNC enabled.

    Enables sub-NUMA clustering (vendor-adaptive: HPE SNC, Dell
    SubNumaCluster, AMD/Supermicro NPS), reboots to apply it, then verifies
    the resulting NUMA topology is reported consistently across layers. The
    expected total NUMA node count is sockets x nodes-per-socket, so a
    dual-socket system with 2 nodes per socket is expected to show 4 NUMA
    nodes total.

    All checks (OS /sys node count and sysinv host-cpu-list processor
    count) are evaluated and individually logged PASS/FAIL, so a failure
    makes clear which layer disagreed.

    WARNING: This is a DISRUPTIVE test. It stages a BIOS change and reboots
    the host, taking the StarlingX system down for a reboot cycle. Only run
    it against a lab that is free for a reboot.
    """
    SncKeywords().verify_numa_topology(request)
