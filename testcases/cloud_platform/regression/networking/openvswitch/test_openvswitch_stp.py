"""Test OVS STP/RSTP.

Covers TC 51 from the test plan.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p1
@mark.lab_has_ovs
def test_rstp_enabled_and_operational():
    """Verify STP/RSTP loop prevention is enabled and operational on br-sriov.

    Test Steps:
        - Verify rstp_enable is true on br-sriov
        - Query RSTP status via ovs-appctl rstp/show
        - Verify at least one port has Root role
        - Verify at least one port is in Forwarding state
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent_pod = ovs_kw.get_ovs_agent_pod()

    get_logger().log_test_case_step("Verify RSTP is enabled on br-sriov")
    rstp_output = ovs_kw.ovs_vsctl(ovs_agent_pod, "get bridge br-sriov rstp_enable")
    validate_str_contains(rstp_output, "true", "RSTP should be enabled on br-sriov")

    get_logger().log_test_case_step("Query RSTP port roles and states")
    status_output = ovs_kw.ovs_appctl(ovs_agent_pod, "rstp/show br-sriov")
    get_logger().log_test_case_step(f"RSTP status:\n{status_output}")

    validate_str_contains(status_output, "Root", "At least one port should have Root role")
    validate_str_contains(status_output, "Forwarding", "At least one port should be in Forwarding state")
