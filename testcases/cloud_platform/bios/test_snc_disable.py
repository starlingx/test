import pytest
from pytest import mark

from keywords.cloud_platform.bios.snc_keywords import SncKeywords


@mark.p3
@mark.lab_is_simplex
@mark.lab_has_bmc_redfish
def test_snc_disable(request: pytest.FixtureRequest):
    """Disable sub-NUMA clustering and verify the BMC reports it disabled.

    Drives the vendor's NUMA BIOS attribute to its "disabled" value (HPE/
    Dell ``Disabled``, AMD/Supermicro ``NUMANodesPerSocket=NPS1``), reboots
    the host to apply it, brings the controller back online, and verifies
    the BMC reports the expected value. A teardown restores the BIOS value
    observed before the test and leaves the controller unlocked.

    WARNING: This is a DISRUPTIVE test. It stages a BIOS change and reboots
    the host, taking the StarlingX system down for a reboot cycle. Only run
    it against a lab that is free for a reboot.
    """
    SncKeywords().set_snc(request, SncKeywords.SNC_DISABLED)
