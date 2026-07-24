"""OVS Setup - Prerequisite test for OVS regression suite.

Run this before the regression tests to ensure OVS is properly configured.
Validates app status, agent pod, bridge, IPs, and remote peer connectivity.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords


@mark.p0
@mark.lab_has_ovs
def test_ovs_app_applied():
    """Verify OVS application is in applied state."""
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_list = SystemApplicationListKeywords(ssh_connection).get_system_application_list()

    get_logger().log_test_case_step("Verify openvswitch application is applied")
    validate_equals(
        app_list.is_in_application_list("openvswitch"),
        True,
        "openvswitch application should be in application list",
    )
    app = app_list.get_application("openvswitch")
    validate_equals(app.get_status(), "applied", "openvswitch application should be in applied state")


@mark.p0
@mark.lab_has_ovs
def test_ovs_agent_running():
    """Verify OVS agent pod is running with all containers ready."""
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify ovs-agent pod is Running")
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    validate_str_contains(ovs_agent, "ovs-agent", "ovs-agent pod should be found and running")


@mark.p0
@mark.lab_has_ovs
def test_ovs_bridge_configured():
    """Verify OVS bridge exists with expected ports."""
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    bridge_name = ovs_config.get_bridge_name()

    get_logger().log_test_case_step(f"Verify bridge {bridge_name} exists")
    bridges = ovs_kw.ovs_vsctl(ovs_agent, "list-br")
    validate_str_contains(bridges, bridge_name, f"Bridge {bridge_name} should exist in OVS")

    get_logger().log_test_case_step("Verify expected ports are on the bridge")
    ports = ovs_kw.ovs_vsctl(ovs_agent, f"list-ports {bridge_name}")
    expected_ports = ovs_config.get_ports()
    for port in expected_ports:
        validate_str_contains(ports, port, f"Port {port} should be on {bridge_name}")


@mark.p0
@mark.lab_has_ovs
def test_ovs_bridge_ips_assigned():
    """Verify bridge IPs are assigned (refresh if needed).

    IPs are ephemeral (lost on pod restart) so this must run before L2 tests.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    bridge_name = ovs_config.get_bridge_name()

    get_logger().log_test_case_step("Assign untagged bridge IP")
    untagged_ip = ovs_config.get_bridge_ip("untagged")
    if untagged_ip:
        ovs_kw.exec_in_pod(ovs_agent, f"ip -6 addr add {untagged_ip}/64 dev {bridge_name} 2>/dev/null || true")
        ovs_kw.exec_in_pod(ovs_agent, f"ip link set {bridge_name} up")

    get_logger().log_test_case_step("Assign VLAN 100 bridge IP")
    vlan100_ip = ovs_config.get_bridge_ip("vlan100")
    if vlan100_ip:
        ovs_kw.ovs_vsctl(ovs_agent, f"add-port {bridge_name} vlan100 tag=100 -- set interface vlan100 type=internal 2>/dev/null || true")
        ovs_kw.exec_in_pod(ovs_agent, f"ip -6 addr add {vlan100_ip}/64 dev vlan100 2>/dev/null || true")
        ovs_kw.exec_in_pod(ovs_agent, "ip link set vlan100 up")

    get_logger().log_test_case_step("Assign VLAN 200 bridge IP")
    vlan200_ip = ovs_config.get_bridge_ip("vlan200")
    if vlan200_ip:
        ovs_kw.ovs_vsctl(ovs_agent, f"add-port {bridge_name} vlan200 tag=200 -- set interface vlan200 type=internal 2>/dev/null || true")
        ovs_kw.exec_in_pod(ovs_agent, f"ip -6 addr add {vlan200_ip}/64 dev vlan200 2>/dev/null || true")
        ovs_kw.exec_in_pod(ovs_agent, "ip link set vlan200 up")

    get_logger().log_test_case_step("Verify bridge has IPv6 address assigned")
    output = ovs_kw.exec_in_pod(ovs_agent, f"ip -6 addr show {bridge_name}")
    validate_str_contains(output, untagged_ip, f"Bridge should have IP {untagged_ip} assigned")


@mark.p0
@mark.lab_has_ovs
def test_remote_peer_pods_running():
    """Verify remote peer traffic pods are running."""
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()

    if not remote_ip:
        get_logger().log_info("No remote peer configured — skipping")
        return

    get_logger().log_test_case_step("Verify traffic pod running on remote peer")
    pod_name = ovs_kw.get_remote_pod_by_prefix(remote_ip, remote_password, ovs_config.get_traffic_pod_prefix())
    validate_not_equals(pod_name, "", "Traffic pod should be found on remote peer")
    get_logger().log_info(f"Remote peer traffic pod: {pod_name}")
